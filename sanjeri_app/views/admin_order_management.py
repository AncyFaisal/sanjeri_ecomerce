# views/admin_order_management.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from ..models import Order, OrderItem, ProductVariant, CustomUser

def admin_required(view_func):
    """Decorator to ensure user is admin/staff"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def admin_order_list(request):
    """Admin order listing with search, filter, and pagination"""
    # Base queryset - latest orders first
    orders = Order.objects.all().select_related(
        'user', 'shipping_address'
    ).prefetch_related('items').order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(shipping_address__phone__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Date filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Sort functionality
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['created_at', '-created_at', 'total_amount', '-total_amount']:
        orders = orders.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(orders, 20)  # 20 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Order statistics for dashboard
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    delivered_orders = orders.filter(status='delivered').count()
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'title': 'Order Management - Admin'
    }
    return render(request, 'admin/orders/order_list.html', context)

@login_required
@admin_required
def admin_order_detail(request, order_id):
    """Admin order detail view"""
    print("\n" + "="*50)
    print(f"🔍 VIEW CALLED with order_id={order_id}")
    print(f"🔍 URL: {request.build_absolute_uri()}")
    print(f"🔍 Method: {request.method}")

    try:
        order = Order.objects.get(id=order_id)
        print(f"✅ Found order: #{order.order_number}")
        print(f"✅ Redirecting to template...")
    except Order.DoesNotExist:
        print(f"❌ Order with id={order_id} does NOT exist!")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("="*50)
    
    try:
        # Get order without user restriction (admin can see all orders)
        order = get_object_or_404(Order.objects.select_related(
            'user', 'shipping_address'
        ).prefetch_related('items'), id=order_id)
        
        context = {
            'order': order,
            'order_items': order.items.all(),
            'title': f'Order #{order.order_number} - Admin'
        }
        return render(request, 'admin/orders/order_detail.html', context)
        
    except Exception as e:
        print(f"Error in admin_order_detail: {e}")
        messages.error(request, "Order not found.")
        return redirect('admin_order_list')



@login_required
@admin_required
@user_passes_test(lambda u: u.is_staff)
def update_order_status(request, order_id):
    """Update order status (AJAX or form submission)"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            old_status = order.status
            
            # ========== SPECIAL HANDLING FOR REFUNDED ==========
            if new_status == 'refunded' and old_status != 'refunded':
                # If order has return_requested status, use approve_return method
                if order.return_status == 'requested':
                    # This will process wallet refund
                    if order.approve_return(approved_by=request.user):
                        messages.success(request, f"Return approved and ₹{order.total_amount} refunded to wallet.")
                    else:
                        messages.error(request, "Failed to process refund.")
                    return redirect('admin_order_detail', order_id=order_id)
                else:
                    # For direct refunds (not from return request)
                    order.status = new_status
                    order.returned_at = timezone.now()
                    order.payment_status = 'refunded'
                    order.save()
            
            elif new_status == 'delivered' and old_status != 'delivered':
                order.delivered_at = timezone.now()
                order.status = new_status
                
                # COD payment completes upon delivery
                if order.payment_method == 'cod' and order.payment_status == 'pending':
                    order.payment_status = 'completed'
                order.save()
            
            elif new_status == 'cancelled' and old_status != 'cancelled':
                order.cancelled_at = timezone.now()
                order.status = new_status
                if order.payment_status in ['completed', 'success']:
                    order.payment_status = 'refunded'
                elif order.payment_status in ['pending', 'partially_paid']:
                    order.payment_status = 'failed'
                order.save()
            
            else:
                # For other statuses
                order.status = new_status
                order.save()
            
            # ========== END FIX ==========
            
            # If AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Order status updated to {order.get_status_display()}',
                    'new_status': order.status,
                    'new_status_display': order.get_status_display(),
                    'new_payment_status': order.payment_status,
                    'new_payment_status_display': order.get_payment_status_display()
                })
            else:
                messages.success(request, f'Order status updated to {order.get_status_display()}')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status'
                }, status=400)
            else:
                messages.error(request, 'Invalid status')
    
    return redirect('admin_order_detail', order_id=order_id)


@login_required
@admin_required
def admin_inventory_management(request):
    """Inventory/Stock management view"""
    # Get all product variants with stock information
    variants = ProductVariant.objects.select_related('product').order_by('product__name', 'volume_ml')
    
    # Search and filter
    search_query = request.GET.get('search', '')
    if search_query:
        variants = variants.filter(
            Q(product__name__icontains=search_query) |
            Q(product__brand__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Low stock filter
    low_stock_filter = request.GET.get('low_stock', '')
    if low_stock_filter:
        variants = variants.filter(stock__lte=10)  # Less than or equal to 10 items
    
    # Out of stock filter
    out_of_stock_filter = request.GET.get('out_of_stock', '')
    if out_of_stock_filter:
        variants = variants.filter(stock=0)
    
    # Pagination
    paginator = Paginator(variants, 25)  # 25 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Inventory statistics
    total_variants = variants.count()
    low_stock_count = variants.filter(stock__lte=10, stock__gt=0).count()
    out_of_stock_count = variants.filter(stock=0).count()
    
    context = {
        'page_obj': page_obj,
        'variants': page_obj.object_list,
        'search_query': search_query,
        'low_stock_filter': low_stock_filter,
        'out_of_stock_filter': out_of_stock_filter,
        'total_variants': total_variants,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'title': 'Inventory Management - Admin'
    }
    return render(request, 'admin/inventory/inventory_management.html', context)

@login_required
@admin_required
def update_stock(request, variant_id):
    """Update product variant stock (AJAX)"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        try:
            new_stock = int(request.POST.get('stock', 0))
            if new_stock >= 0:
                variant.stock = new_stock
                variant.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Stock updated to {new_stock}',
                    'new_stock': variant.stock,
                    'variant_name': str(variant)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Stock cannot be negative'
                }, status=400)
                
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid stock value'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from ..models import Order


@staff_member_required
def approve_return(request, order_id):
    """Admin approves return and processes wallet refund (VIEW)"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check if already approved
    if order.return_status == 'approved':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Return for order #{order.order_number} is already approved.'
            })
        else:
            messages.warning(request, f"Return for order #{order.order_number} is already approved.")
            return redirect('admin_order_detail', order_id=order_id)
    
    # Call the model method (this will call the correct one in models/order.py)
    if order.approve_return(request.user):
        message = f"Return approved for order #{order.order_number}. Amount refunded to customer's wallet."
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'new_status': order.status,
                'new_status_display': order.get_status_display(),
                'new_payment_status': order.payment_status,
                'new_payment_status_display': order.get_payment_status_display(),
                'return_status': order.return_status
            })
        else:
            messages.success(request, message)
    else:
        message = "Cannot approve return. Order may not be in requested state."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': message})
        else:
            messages.error(request, message)
    
    return redirect('admin_order_detail', order_id=order_id)
        
    
@staff_member_required
def reject_return(request, order_id):
    """Admin rejects return request with reason"""
    # Check if it's AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Only allow POST requests
    if request.method != 'POST':
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Invalid request method.'})
        messages.error(request, "Invalid request method.")
        return redirect('admin_order_detail', order_id=order_id)
    
    # Get the order
    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Order not found.'})
        messages.error(request, "Order not found.")
        return redirect('admin_order_list')
    
    # Get and validate rejection reason
    rejection_reason = request.POST.get('rejection_reason', '').strip()
    
    if not rejection_reason:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Please provide a reason for rejection.'})
        messages.error(request, "Please provide a reason for rejection.")
        return redirect('admin_order_detail', order_id=order_id)
    
    if len(rejection_reason) < 10:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Please provide a more detailed reason (at least 10 characters).'})
        messages.error(request, "Please provide a more detailed reason (at least 10 characters).")
        return redirect('admin_order_detail', order_id=order_id)
    
    # Validate order state
    if order.return_status != 'requested':
        if is_ajax:
            return JsonResponse({'success': False, 'message': f"Cannot reject return. Order status is '{order.get_return_status_display()}', not 'Requested'."})
        messages.error(request, f"Cannot reject return. Order status is '{order.get_return_status_display()}', not 'Requested'.")
        return redirect('admin_order_detail', order_id=order_id)
    
    # Call the model method to reject the return
    try:
        if order.reject_return(rejection_reason):
            message = f"Return rejected for order #{order.order_number}. Reason: {rejection_reason}"
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'new_status': order.status,
                    'new_status_display': order.get_status_display(),
                    'new_payment_status': order.payment_status,
                    'new_payment_status_display': order.get_payment_status_display(),
                    'return_status': order.return_status,
                    'redirect_url': reverse('admin_order_detail', args=[order.id])
                })
            else:
                messages.warning(request, message)
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Failed to reject return. Please check if order is in correct state.'})
            messages.error(request, "Failed to reject return. Please check if order is in correct state.")
            
    except Exception as e:
        if is_ajax:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})
        messages.error(request, f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return redirect('admin_order_detail', order_id=order_id)

@login_required
@admin_required
def admin_edit_order_items(request, order_id):
    """Admin view to add/remove order items"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_item':
            # Get variant and quantity
            variant_id = request.POST.get('variant_id')
            quantity = int(request.POST.get('quantity', 1))
            
            variant = get_object_or_404(ProductVariant, id=variant_id)
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                variant_details=f"{variant.volume_ml}ml - {variant.gender}",
                quantity=quantity,
                unit_price=variant.display_price,
                total_price=quantity * variant.display_price,
            )
            
            # IMPORTANT: Recalculate totals after adding item
            order.calculate_totals()
            
            messages.success(request, f"Added {quantity} x {variant.product.name} to order")
            
        elif action == 'remove_item':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            item.delete()
            
            # IMPORTANT: Recalculate totals after removing item
            order.calculate_totals()
            
            messages.success(request, "Item removed from order")
        
        elif action == 'update_quantity':
            item_id = request.POST.get('item_id')
            new_quantity = int(request.POST.get('quantity', 1))
            
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            item.quantity = new_quantity
            item.total_price = new_quantity * item.unit_price
            item.save()
            
            # IMPORTANT: Recalculate totals after updating quantity
            order.calculate_totals()
            
            messages.success(request, f"Quantity updated to {new_quantity}")
    
    return redirect('admin_order_detail', order_id=order_id)

@staff_member_required
def approve_item_return(request, item_id):
    """Admin approves individual item return"""
    order_item = get_object_or_404(OrderItem, id=item_id)
    
    # Check if already approved
    if order_item.return_status == 'approved':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Return for {order_item.product_name} is already approved.'
            })
        else:
            messages.warning(request, f"Return for {order_item.product_name} is already approved.")
            return redirect('admin_order_detail', order_id=order_item.order.id)
    
    if order_item.approve_item_return(request.user):
        message = f"Return approved for {order_item.product_name}. ₹{order_item.total_price} refunded to wallet."
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'item_id': item_id,
                'new_status': order_item.return_status,
                'new_status_display': order_item.get_return_status_display()
            })
        else:
            messages.success(request, message)
    else:
        message = "Cannot approve return for this item."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': message})
        else:
            messages.error(request, message)
    
    return redirect('admin_order_detail', order_id=order_item.order.id)


@staff_member_required
def reject_item_return(request, item_id):
    """Admin rejects individual item return"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method != 'POST':
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Invalid request method.'})
        messages.error(request, "Invalid request method.")
        return redirect('admin_order_detail', order_id=order_item.order.id)
    
    order_item = get_object_or_404(OrderItem, id=item_id)
    rejection_reason = request.POST.get('rejection_reason', '').strip()
    
    if not rejection_reason:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Please provide a reason for rejection.'})
        messages.error(request, "Please provide a reason for rejection.")
        return redirect('admin_order_detail', order_id=order_item.order.id)
    
    if order_item.reject_item_return(rejection_reason, request.user):
        message = f"Return rejected for {order_item.product_name}. Reason: {rejection_reason}"
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'item_id': item_id,
                'new_status': order_item.return_status,
                'new_status_display': order_item.get_return_status_display()
            })
        else:
            messages.warning(request, message)
    else:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Failed to reject return.'})
        messages.error(request, "Failed to reject return.")
    
    return redirect('admin_order_detail', order_id=order_item.order.id)