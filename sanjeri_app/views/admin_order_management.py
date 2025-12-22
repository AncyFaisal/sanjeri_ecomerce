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
            order.status = new_status
            
            # Update timestamps for specific status changes
            if new_status == 'delivered' and old_status != 'delivered':
                # You could set delivered_at here if you have the field
                pass
            elif new_status == 'cancelled' and old_status != 'cancelled':
                order.cancelled_at = timezone.now()
            
            order.save()
            
            # If AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Order status updated to {order.get_status_display()}',
                    'new_status': order.status,
                    'new_status_display': order.get_status_display()
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