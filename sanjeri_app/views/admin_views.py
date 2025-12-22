# your_app/views/admin_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Case, When, Value, Max
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.db import models
from ..models import CustomUser  # Import your CustomUser model
from ..forms import UserSearchForm, UserFilterForm

def admin_required(function):
    """
    Decorator to ensure user is admin/staff
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access admin panel.")
            return redirect('user_login')  # Redirect to your custom login
        if not request.user.is_staff:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('homepage')  # Redirect to home page
        return function(request, *args, **kwargs)
    return wrapper
@login_required
@admin_required
def toggle_user_status(request, user_id):
    """
    Toggle user status between active and blocked
    """
    print(f"=== TOGGLE USER STATUS CALLED ===")
    print(f"User ID: {user_id}")
    print(f"Method: {request.method}")
    print(f"User: {request.user}")
    print(f"Headers: {dict(request.headers)}")
    
    if request.method == 'POST':
        try:
            user = get_object_or_404(CustomUser, id=user_id, is_staff=False)
            print(f"Found user: {user.username}, Current status: {user.status}")
            
            # Toggle status
            if user.status == 'active':
                user.status = 'blocked'
                user.is_active = False
                action = 'blocked'
                message = f'User {user.get_full_name()} has been blocked.'
            else:
                user.status = 'active'
                user.is_active = True
                action = 'unblocked'
                message = f'User {user.get_full_name()} has been unblocked.'
            
            user.save()
            print(f"User status changed to: {user.status}")
            
            # Return JSON for AJAX, redirect for forms
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'action': action,
                    'new_status': user.status,
                    'message': message
                })
            else:
                messages.success(request, message)
                return redirect('user_list')
                
        except Exception as e:
            error_msg = f'Error toggling user status: {str(e)}'
            print(f"ERROR: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            else:
                messages.error(request, error_msg)
                return redirect('user_list')
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@admin_required
def user_list(request):
    """
    User List Page with search, filter and pagination
    """
    # Get all non-staff users with calculated fields
    # users = CustomUser.objects.filter(is_staff=False).annotate(  # Use CustomUser
    #     total_orders=Count('order', distinct=True),
    #     total_amount_spent=Coalesce(Sum(
    #         Case(
    #             When(order__payment_status='paid', then='order__total_amount'),
    #             default=Value(0),
    #             output_field=models.DecimalField()
    #         )
    #     ), 0),
    #     last_order_date=Max('order__created_at')
    # ).order_by('-date_joined')  # Latest users first

    # Get all non-staff users
    # users = CustomUser.objects.filter(is_staff=False).annotate(
    #     total_orders=Value(0, output_field=IntegerField()),  # Specify output_field
    #     total_amount_spent=Value(0, output_field=DecimalField()),  # Specify output_field
    #     last_order_date=Value(None, output_field=DateTimeField())  # Specify output_field
    # ).order_by('-date_joined')
      # Get all non-staff users without annotations
    users = CustomUser.objects.filter(is_staff=False).order_by('-date_joined')

   # Initialize forms
    search_form = UserSearchForm(request.GET or None)
    filter_form = UserFilterForm(request.GET or None)
    
    # Initialize search_query with empty string
    search_query = ""

   # Search functionality
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query','')
        if search_query:
            users = users.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(username__icontains=search_query)
            )

    # Filter functionality
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        registration_date_from = filter_form.cleaned_data.get('registration_date_from')
        registration_date_to = filter_form.cleaned_data.get('registration_date_to')
        total_orders = filter_form.cleaned_data.get('total_orders')
        total_spent = filter_form.cleaned_data.get('total_spent')
        
    # Apply filters
        if status:
            users = users.filter(status=status)
    
        if registration_date_from:
            users = users.filter(date_joined__gte=registration_date_from)
        
        if registration_date_to:
            users = users.filter(date_joined__lte=registration_date_to)
    
    # if total_orders:
    #     if total_orders == '10+':
    #         users = users.filter(total_orders__gte=10)
    #     elif total_orders == '5-10':
    #         users = users.filter(total_orders__range=(5, 10))
    #     elif total_orders == '1-5':
    #         users = users.filter(total_orders__range=(1, 5))
    #     elif total_orders == '0':
    #         users = users.filter(total_orders=0)
    
    # if total_spent:
    #     if total_spent == '5000+':
    #         users = users.filter(total_amount_spent__gte=5000)
    #     elif total_spent == '1000-5000':
    #         users = users.filter(total_amount_spent__range=(1000, 5000))
    #     elif total_spent == '0-1000':
    #         users = users.filter(total_amount_spent__range=(0, 1000))

# Get total count before pagination
    total_users_count = users.count()

    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'User Management',
        'users': page_obj,
        'search_query': search_query,
        'total_users': users.count(),
    }
    
    return render(request, 'user_list.html', context)

@login_required
@admin_required
def user_detail(request, user_id):
    """
    User Detail Page
    """
    user = get_object_or_404(CustomUser, id=user_id, is_staff=False)  # Use CustomUser
    
    # Calculate user statistics
    # user_orders = Order.objects.filter(user=user)
    # total_orders = user_orders.count()
    # total_amount_spent = user_orders.filter(payment_status='paid').aggregate(
    #     total=Sum('total_amount')
    # )['total'] or 0
    
    total_orders = 0
    total_amount_spent = 0
    last_order = None

     # Get last order
    # last_order = user_orders.first()
 # Calculate average order amount
    if total_orders > 0:
        avg_order_amount = total_amount_spent / total_orders
    else:
        avg_order_amount = 0
    context = {
        'page_title': f'User Details - {user.get_full_name()}',
        'user': user,
        'total_orders': total_orders,
        'total_amount_spent': total_amount_spent,
        'avg_order_amount': avg_order_amount,  # Add this
        'last_order': None,  # Add this to fix the template reference
    }
    
    return render(request, 'user_detail.html', context)
@login_required
@admin_required
def delete_user(request, user_id):
    """
    Delete user account (soft delete)
    """
    if request.method == 'POST':
        try:
            user = get_object_or_404(CustomUser, id=user_id, is_staff=False)
            user_email = user.email
            
            # Soft delete
            user.is_active = False
            user.status = 'blocked'  # Also block the user
            
            # Handle email - ensure uniqueness
            user.email = f"deleted_{user_id}_{user.email}"
            
            # Handle phone - keep within 15 character limit
            if user.phone:
                # Use shorter prefix to fit within 15 chars
                user.phone = f"del{user_id}"[:15]
            else:
                user.phone = f"del{user_id}"[:15]
            
            user.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'User {user_email} deleted successfully'
                })
            
            messages.success(request, f'User {user_email} deleted successfully')
            return redirect('user_list')
            
        except Exception as e:
            error_msg = f'Error deleting user: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            
            messages.error(request, error_msg)
            return redirect('user_list')
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@admin_required
def admin_dashboard(request):
    """
    Admin Dashboard
    """
    total_users = CustomUser.objects.filter(is_staff=False).count()
    # Add counts for products, categories, orders etc.
    
    context = {
        'page_title': 'Admin Dashboard',
        'total_users': total_users,
        'total_products': 0,  # Replace with actual count
        'total_categories': 0,  # Replace with actual count
    }
    
    return render(request, 'admin_dashboard.html', context)