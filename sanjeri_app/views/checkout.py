# views/checkout.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from ..models import Cart, CartItem, Address, Order, OrderItem

# Update the checkout_view to include payment options
@login_required
def checkout_view(request):
    """Checkout page with address selection and order summary"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('variant', 'variant__product', 'variant__product__category').all()
        
        # Check if cart can proceed to checkout
        if not cart.can_checkout:
            messages.error(request, "Some items in your cart are unavailable. Please remove them to proceed.")
            return redirect('cart')
        
        if cart.total_items == 0:
            messages.warning(request, "Your cart is empty. Add some products to checkout.")
            return redirect('cart')
        
        # Get user addresses
        addresses = Address.objects.filter(user=request.user)
        default_address = addresses.filter(is_default=True).first()
        
        # Calculate order totals - Use Decimal consistently
        subtotal = cart.subtotal
        discount_amount = Decimal('0') 
        if subtotal > Decimal('1000'):
            discount_amount = subtotal * Decimal('0.10')
        shipping_charge = Decimal('0') if subtotal > Decimal('500') else Decimal('40')
        tax_amount = subtotal * Decimal('0.18')
        total_amount = subtotal + shipping_charge + tax_amount - discount_amount
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'addresses': addresses,
            'default_address': default_address,
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'shipping_charge': shipping_charge,
            'tax_amount': tax_amount,
            'total_amount': total_amount,
            'show_online_payment': True,  # Enable online payment option
        }
        return render(request, 'checkout/checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty. Add some products to checkout.")
        return redirect('cart')
    

@login_required
@require_POST
def place_order(request):
    """Place order with payment method selection"""
    try:
        with transaction.atomic():
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.select_related('variant', 'variant__product').all()
            
            # Validate cart before placing order
            if not cart.can_checkout:
                return JsonResponse({
                    'success': False,
                    'message': 'Some items in your cart are unavailable. Please remove them to proceed.'
                })
            
            if cart.total_items == 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Your cart is empty.'
                })
            
            # Get selected address
            address_id = request.POST.get('address_id')
            if not address_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select a delivery address.'
                })
            
            # Get payment method
            payment_method = request.POST.get('payment_method', 'cod')
            
            address = get_object_or_404(Address, id=address_id, user=request.user)
            
            # Calculate discount (same logic as checkout view)
            subtotal = cart.subtotal
            discount_amount = Decimal('0')
            if subtotal > Decimal('1000'):
                discount_amount = subtotal * Decimal('0.10')
                
            # Create order
            order = Order.objects.create(
                user=request.user,
                shipping_address=address,
                payment_method=payment_method,
                payment_status='pending' if payment_method == 'online' else 'pending',
                subtotal=subtotal,
                discount_amount=discount_amount,
            )
            
            # Create order items
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=cart_item.variant,
                    product_name=cart_item.variant.product.name,
                    variant_details=f"{cart_item.variant.volume_ml}ml - {cart_item.variant.gender}",
                    quantity=cart_item.quantity,
                    unit_price=cart_item.variant.display_price,
                    total_price=cart_item.total_price,
                    product_image=cart_item.variant.product.main_image
                )
                
                # Update product stock
                cart_item.variant.stock -= cart_item.quantity
                cart_item.variant.save()
            
            # Calculate order totals
            order.calculate_totals()
            
            # Clear cart after successful order
            cart.clear_cart()
            
            # Handle different payment methods
            if payment_method == 'online':
                # Store order ID in session for failed payments
                request.session['last_order_id'] = order.id
                
                return JsonResponse({
                    'success': True,
                    'payment_required': True,
                    'redirect_url': f'/payment/initiate/{order.id}/'
                })
            else:
                # COD - redirect directly to success
                order.payment_status = 'pending'  # COD is pending until delivered
                order.save()
                
                return JsonResponse({
                    'success': True,
                    'payment_required': False,
                    'redirect_url': f'/order-success/{order.id}/'
                })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error placing order: {str(e)}'
        })
    
    
@login_required
def order_success(request, order_id):
    """Order success page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    return render(request, 'checkout/order_success.html', context)

@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    return render(request, 'checkout/order_detail.html', context)