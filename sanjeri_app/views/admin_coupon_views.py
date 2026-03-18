from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from ..models import Coupon
from django.db import transaction
import json
from datetime import timedelta
from django.utils.dateparse import parse_datetime
import pytz
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# Get user's timezone (assuming IST)
user_timezone = pytz.timezone('Asia/Kolkata')


def is_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_coupon_list(request):
    """Display all coupons in admin panel"""
    # Get filter parameters
    status = request.GET.get('status', '')
    discount_type = request.GET.get('discount_type', '')
    search = request.GET.get('search', '')
    show_deleted = request.GET.get('show_deleted', 'false') == 'true'
    
    # Pagination parameter
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10) 

    if show_deleted:
        coupons = Coupon.objects.deleted().order_by('-deleted_at')
    else:
        coupons = Coupon.objects.all().order_by('-created_at')
    
    # Apply filters
    if status and not show_deleted:  # Don't filter status for deleted items
        coupons = coupons.filter(active=(status == 'active'))
    if discount_type:
        coupons = coupons.filter(discount_type=discount_type)
    if search:
        coupons = coupons.filter(code__icontains=search)
    
     # Calculate counts for tabs
    active_count = Coupon.objects.filter(is_deleted=False).count()
    deleted_count = Coupon.objects.filter(is_deleted=True).count()
    
     # Apply pagination
    paginator = Paginator(coupons, page_size)
    
    try:
        paginated_coupons = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        paginated_coupons = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        paginated_coupons = paginator.page(paginator.num_pages)
    
    # Build query string for pagination links (preserve filters)
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if discount_type:
        query_params.append(f'discount_type={discount_type}')
    if search:
        query_params.append(f'search={search}')
    if show_deleted:
        query_params.append('show_deleted=true')
    if page_size != 10:
        query_params.append(f'page_size={page_size}')
    
    query_string = '&'.join(query_params)
    if query_string:
        query_string = '&' + query_string
        
    context = {
        'coupons': paginated_coupons,
        'status_filter': status,
        'discount_type_filter': discount_type,
        'search_query': search,
        'show_deleted': show_deleted,
        'active_count': active_count,
        'deleted_count': deleted_count, 
        'page_size': page_size,
        'query_string': query_string,
        'paginator': paginator, 
    }
    return render(request, 'admin/coupon/list.html', context)

@login_required
@user_passes_test(is_admin)
def create_coupon(request):
    """Create new coupon"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                code = request.POST.get('code', '').strip().upper()
                discount_type = request.POST.get('discount_type')
                discount_value = request.POST.get('discount_value')
                min_order_amount = request.POST.get('min_order_amount') or 0
                max_discount_amount = request.POST.get('max_discount_amount') or None
                usage_limit = request.POST.get('usage_limit') or 1
                valid_from = request.POST.get('valid_from')
                valid_to = request.POST.get('valid_to')
                active = request.POST.get('active') == 'on'
                single_use_per_user = request.POST.get('single_use_per_user') == 'on'
                
                # Validation
                if not code:
                    raise ValidationError("Coupon code is required")
                
                if Coupon.objects.filter(code=code).exists():
                    raise ValidationError(f"Coupon code '{code}' already exists")
                
                if discount_type == 'percentage' and Decimal(discount_value) > 100:
                    raise ValidationError("Percentage discount cannot exceed 100%")
                
                # Convert to datetime
                
                valid_from_dt = parse_datetime(valid_from)
                valid_to_dt = parse_datetime(valid_to)
                
                if not valid_from_dt or not valid_to_dt:
                    raise ValidationError("Invalid date format")
                
                # Assume the input dates are in user's local time (IST)
                # First, make them naive if they have timezone
                if timezone.is_aware(valid_from_dt):
                    valid_from_dt = valid_from_dt.replace(tzinfo=None)
                if timezone.is_aware(valid_to_dt):
                    valid_to_dt = valid_to_dt.replace(tzinfo=None)

                # Localize to user's timezone (IST)
                valid_from_dt = user_timezone.localize(valid_from_dt)
                valid_to_dt = user_timezone.localize(valid_to_dt)

                # Convert to UTC for storage - FIXED
                valid_from_dt = valid_from_dt.astimezone(pytz.UTC)
                valid_to_dt = valid_to_dt.astimezone(pytz.UTC)
                 
                # NOW validate the dates (after conversion)
                if valid_from_dt >= valid_to_dt:
                    raise ValidationError("Valid 'From' date must be before 'To' date")
                
                # Create coupon
                coupon = Coupon(
                    code=code,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    min_order_amount=min_order_amount,
                    max_discount_amount=max_discount_amount,
                    usage_limit=usage_limit,
                    valid_from=valid_from_dt,  # Start from now if past date provided
                    valid_to=valid_to_dt,
                    active=active,
                    single_use_per_user=single_use_per_user,
                )
                coupon.save()
                
                messages.success(request, f'Coupon "{code}" created successfully!')
                return redirect('admin_coupon_list')
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error creating coupon: {str(e)}')
    
    return render(request, 'admin/coupon/create.html')

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_coupon(request, coupon_id):
    """Soft delete a coupon"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id)
            
            # Check if already deleted
            if coupon.is_deleted:
                return JsonResponse({
                    'success': False,
                    'message': f'Coupon "{coupon.code}" is already deleted'
                })
            
            # Check if coupon has been used
            if coupon.times_used > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot delete coupon "{coupon.code}" as it has been used {coupon.times_used} times'
                })
            
            # Soft delete
            coupon.soft_delete(user=request.user)
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon "{coupon.code}" deleted successfully',
                'is_soft_delete': True
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error deleting coupon: {str(e)}'
            })
    
    # Non-AJAX request
    try:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        
        if coupon.times_used > 0:
            messages.warning(request, f'Cannot delete coupon "{coupon.code}" as it has been used {coupon.times_used} times')
        else:
            coupon.soft_delete(user=request.user)
            messages.success(request, f'Coupon "{coupon.code}" deleted successfully')
            
    except Exception as e:
        messages.error(request, f'Error deleting coupon: {str(e)}')
    
    return redirect('admin_coupon_list')

# @login_required
# @user_passes_test(is_admin)
# @require_POST
# def restore_coupon(request, coupon_id):
#     """Restore a soft-deleted coupon"""
#     try:
#         coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id, is_deleted=True)
#         coupon.restore()
        
#         messages.success(request, f'Coupon "{coupon.code}" restored successfully')
        
#     except Exception as e:
#         messages.error(request, f'Error restoring coupon: {str(e)}')
    
#     return redirect('admin_coupon_list')

# @login_required
# @user_passes_test(is_admin)
# @require_POST
# def permanent_delete_coupon(request, coupon_id):
#     """Permanently delete a coupon (only if already soft-deleted)"""
#     try:
#         coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id, is_deleted=True)
        
#         # Double check - only delete if soft-deleted for at least 30 days
#         from django.utils import timezone
#         from datetime import timedelta
        
#         if coupon.deleted_at and coupon.deleted_at < timezone.now() - timedelta(days=30):
#             coupon.delete()
#             messages.success(request, f'Coupon "{coupon.code}" permanently deleted')
#         else:
#             messages.warning(request, f'Coupon can only be permanently deleted 30 days after soft deletion')
            
#     except Exception as e:
#         messages.error(request, f'Error permanently deleting coupon: {str(e)}')
    
#     return redirect('admin_coupon_list')

@login_required
@user_passes_test(is_admin)
def toggle_coupon_status(request, coupon_id):
    """Toggle coupon active status"""
    try:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.active = not coupon.active
        coupon.save()
        
        status = "activated" if coupon.active else "deactivated"
        messages.success(request, f'Coupon "{coupon.code}" {status} successfully')
        
    except Exception as e:
        messages.error(request, f'Error updating coupon: {str(e)}')
    
    return redirect('admin_coupon_list')


@login_required
@user_passes_test(is_admin)
def coupon_trash(request):
    """Display all soft-deleted coupons (recycle bin)"""
    # Get soft-deleted coupons
    deleted_coupons = Coupon.objects.deleted().order_by('-deleted_at')
    
    # Get filter parameters
    search = request.GET.get('search', '')
    days_deleted = request.GET.get('days_deleted', '')
    
    if search:
        deleted_coupons = deleted_coupons.filter(code__icontains=search)
    
    if days_deleted:
        try:
            days = int(days_deleted)
            cutoff_date = timezone.now() - timedelta(days=days)
            deleted_coupons = deleted_coupons.filter(deleted_at__gte=cutoff_date)
        except ValueError:
            pass
    
    # Create a list of coupon data with calculated values
    coupon_data_list = []
    can_permanent_delete_count = 0
    
    for coupon in deleted_coupons:
        # Calculate days since deleted
        days_since = 0
        if coupon.deleted_at:
            delta = timezone.now() - coupon.deleted_at
            days_since = delta.days
        
        # Calculate days left
        days_left = max(30 - days_since, 0)
        
        # Check if can be permanently deleted
        can_delete = days_since >= 30
        if can_delete:
            can_permanent_delete_count += 1
        
        # Create a dictionary with all data
        data = {
            'object': coupon,
            'days_since_deleted': days_since,
            'days_left': days_left,
            'can_be_permanently_deleted': can_delete,
        }
        coupon_data_list.append(data)
    
    context = {
        'coupon_data_list': coupon_data_list,  # Changed variable name
        'search_query': search,
        'days_deleted': days_deleted,
        'total_deleted': len(coupon_data_list),
        'can_permanent_delete': can_permanent_delete_count,
        'deleted_count': len(coupon_data_list),
        'is_trash_page': True,
    }
    return render(request, 'admin/coupon/trash.html', context)

@login_required
@user_passes_test(is_admin)
@require_POST
def restore_coupon(request, coupon_id):
    """Restore a soft-deleted coupon"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id)
            
            if not coupon.is_deleted:
                return JsonResponse({
                    'success': False,
                    'message': f'Coupon "{coupon.code}" is not deleted'
                })
            
            coupon.restore()
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon "{coupon.code}" restored successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error restoring coupon: {str(e)}'
            })
    
    # Non-AJAX request
    try:
        coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id)
        coupon.restore()
        messages.success(request, f'Coupon "{coupon.code}" restored successfully')
        
    except Exception as e:
        messages.error(request, f'Error restoring coupon: {str(e)}')
    
    return redirect('coupon_trash')

@login_required
@user_passes_test(is_admin)
@require_POST
def permanent_delete_coupon(request, coupon_id):
    """Permanently delete a soft-deleted coupon"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id)
            
            if not coupon.is_deleted:
                return JsonResponse({
                    'success': False,
                    'message': f'Coupon "{coupon.code}" is not in trash'
                })
            
            # Check if can be permanently deleted
            if coupon.days_since_deleted < 30:
                return JsonResponse({
                    'success': False,
                    'message': f'Coupon can only be permanently deleted 30 days after deletion. ({coupon.days_since_deleted}/30 days passed)'
                })
            
            coupon_code = coupon.code
            coupon.permanent_delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon "{coupon_code}" permanently deleted'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error permanently deleting coupon: {str(e)}'
            })
    
    # Non-AJAX request
    try:
        coupon = get_object_or_404(Coupon.objects.with_deleted(), id=coupon_id)
        
        if coupon.days_since_deleted < 30:
            messages.warning(request, f'Coupon can only be permanently deleted 30 days after deletion. ({coupon.days_since_deleted}/30 days passed)')
        else:
            coupon_code = coupon.code
            coupon.permanent_delete()
            messages.success(request, f'Coupon "{coupon_code}" permanently deleted')
            
    except Exception as e:
        messages.error(request, f'Error permanently deleting coupon: {str(e)}')
    
    return redirect('coupon_trash')

@login_required
@user_passes_test(is_admin)
@require_POST
def empty_coupon_trash(request):
    """Empty the coupon trash (permanently delete all eligible coupons)"""
    try:
        # Get coupons deleted more than 30 days ago
        cutoff_date = timezone.now() - timedelta(days=30)
        old_deleted_coupons = Coupon.objects.deleted().filter(deleted_at__lt=cutoff_date)
        
        count = old_deleted_coupons.count()
        
        if count == 0:
            messages.info(request, "No coupons eligible for permanent deletion (must be deleted for 30+ days)")
            return redirect('coupon_trash')
        
        # Delete them permanently
        old_deleted_coupons.delete()
        
        messages.success(request, f"Permanently deleted {count} coupon(s) from trash")
        
    except Exception as e:
        messages.error(request, f'Error emptying trash: {str(e)}')
    
    return redirect('coupon_trash')

@login_required
@user_passes_test(is_admin)
@require_POST
def restore_all_coupons(request):
    """Restore all coupons from trash"""
    try:
        deleted_coupons = Coupon.objects.deleted()
        count = deleted_coupons.count()
        
        if count == 0:
            messages.info(request, "No coupons in trash to restore")
            return redirect('coupon_trash')
        
        # Restore all
        for coupon in deleted_coupons:
            coupon.restore()
        
        messages.success(request, f"Restored {count} coupon(s) from trash")
        
    except Exception as e:
        messages.error(request, f'Error restoring all coupons: {str(e)}')
    
    return redirect('admin_coupon_list')