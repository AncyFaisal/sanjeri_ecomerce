# views/checkout.py
# views/checkout.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from ..models import Cart, CartItem, Address, Order, OrderItem, Coupon

# Add these helper functions at the top of the file
def get_coupon_display_data(cart, coupon_data):
    """Helper function to get coupon display data"""
    if not coupon_data:
        return None
    
    try:
        coupon = Coupon.objects.get(id=coupon_data['coupon_id'])
        discount_amount = coupon.calculate_discount(cart.subtotal)
        
        return {
            'code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value,
            'discount_amount': discount_amount,
            'display_text': f'{coupon.discount_value}{"%" if coupon.discount_type == "percentage" else "₹"} OFF',
            'description': get_coupon_description(coupon)
        }
    except Coupon.DoesNotExist:
        return None

def get_coupon_description(coupon):
    """Generate coupon description"""
    description = []
    
    if coupon.discount_type == 'percentage':
        description.append(f'{coupon.discount_value}% discount')
    else:
        description.append(f'₹{coupon.discount_value} off')
    
    if coupon.min_order_amount > 0:
        description.append(f'on orders above ₹{coupon.min_order_amount}')
    
    if coupon.max_discount_amount:
        description.append(f'(max ₹{coupon.max_discount_amount})')
    
    return ' '.join(description)

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
        
        # Get user wallet balance
        wallet_balance = Decimal('0')
        try:
            wallet_balance = request.user.wallet.balance
        except:
            pass
        
         # Get applied coupon from session
        applied_coupon_data = request.session.get('applied_coupon')
        coupon_display = None
        coupon_discount = Decimal('0')
        
        if applied_coupon_data:
            try:
                coupon = Coupon.objects.get(id=applied_coupon_data['coupon_id'], active=True)
                
                
                # Check if user has already used this coupon
                if coupon.single_use_per_user:
                    # Check if user has already placed orders with this coupon
                    from ..models import Order
                    used_count = Order.objects.filter(
                        user=request.user,
                        coupon=coupon,
                        status__in=['confirmed', 'shipped', 'delivered', 'out_for_delivery']
                    ).count()
                    
                    if used_count > 0:
                        # User already used this coupon, remove from session
                        del request.session['applied_coupon']
                        messages.warning(request, f'Coupon "{coupon.code}" has already been used.')
                        return redirect('checkout')
                
                
                is_valid, message = coupon.is_valid(
                    user=request.user,
                    order_amount=cart.subtotal
                )
                
                if is_valid:
                    coupon_discount = coupon.calculate_discount(cart.subtotal)
                    coupon_display = get_coupon_display_data(cart, applied_coupon_data)
                else:
                    # Remove invalid coupon from session
                    del request.session['applied_coupon']
                    messages.warning(request, f'Coupon "{coupon.code}" is no longer valid: {message}')
            except Coupon.DoesNotExist:
                # Remove invalid coupon from session
                if 'applied_coupon' in request.session:
                    del request.session['applied_coupon']
        
        # Calculate order totals
        subtotal = cart.subtotal
        
        # Apply coupon discount
        coupon_discount_amount = coupon_discount
        
        # Apply existing 10% discount on orders above 1000
        additional_discount = Decimal('0')
        if subtotal > Decimal('1000'):
            additional_discount = subtotal * Decimal('0.10')
        
        # Total discount
        total_discount = coupon_discount_amount + additional_discount
        
        # Calculate shipping and tax
        shipping_charge = Decimal('0') if subtotal > Decimal('500') else Decimal('40')
        tax_amount = (subtotal - coupon_discount_amount) * Decimal('0.18')
        # total_amount_before_wallet = subtotal + shipping_charge + tax_amount - total_discount

        # Calculate FINAL TOTAL (corrected calculation)
        total_amount = subtotal + shipping_charge + tax_amount - total_discount 
        
        # Calculate max wallet amount that can be used
        max_wallet_amount = min(wallet_balance, total_amount)
        

        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'addresses': addresses,
            'default_address': default_address,
            'applied_coupon': coupon_display,
            'wallet_balance': wallet_balance,
            'max_wallet_amount': max_wallet_amount,
            'subtotal': subtotal,
            'discount_amount': total_discount,
            'coupon_discount': coupon_discount_amount,
            'additional_discount': additional_discount,
            'shipping_charge': shipping_charge,
            'tax_amount': tax_amount,
            'total_amount': total_amount,
            'show_online_payment': True,
            'wallet_balance_formatted': f"{wallet_balance:,.2f}",
        }
        return render(request, 'checkout/checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty. Add some products to checkout.")
        return redirect('cart')

@login_required
@require_POST
def place_order(request):
    """Place order with wallet payment option"""
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
            
            # Get wallet payment details
            use_wallet = request.POST.get('use_wallet') == 'true'
            wallet_amount = Decimal(request.POST.get('wallet_amount', '0'))
            
            address = get_object_or_404(Address, id=address_id, user=request.user)
            
            # Get applied coupon
            coupon = None
            coupon_discount = Decimal('0')
            applied_coupon_data = request.session.get('applied_coupon')
            
            if applied_coupon_data:
                try:
                    coupon = Coupon.objects.get(id=applied_coupon_data['coupon_id'], active=True)
                    
                    # ========== ADD VALIDATION HERE TOO ==========
                    if coupon.single_use_per_user:
                        # Double-check user hasn't used coupon
                        used_count = Order.objects.filter(
                            user=request.user,
                            coupon=coupon,
                            status__in=['confirmed', 'shipped', 'delivered', 'out_for_delivery']
                        ).count()
                        
                        if used_count > 0:
                            # Remove invalid coupon
                            if 'applied_coupon' in request.session:
                                del request.session['applied_coupon']
                            return JsonResponse({
                                'success': False,
                                'message': f'Coupon "{coupon.code}" has already been used.'
                            })
                    # ========== END VALIDATION ==========
                    
                    is_valid, message = coupon.is_valid(
                        user=request.user,
                        order_amount=cart.subtotal
                    )
                    
                    if is_valid:
                        coupon_discount = coupon.calculate_discount(cart.subtotal)
                    else:
                        coupon = None
                        coupon_discount = Decimal('0')
                        
                except Coupon.DoesNotExist:
                    coupon = None
                    coupon_discount = Decimal('0')
            
            # Calculate subtotal
            subtotal = cart.subtotal
            
            # Apply coupon discount
            if coupon_discount > subtotal:
                coupon_discount = subtotal
            
            # ========== FIXED DISCOUNT CALCULATION ==========
            # Apply existing 10% discount on ORIGINAL subtotal
            other_discount = Decimal('0')
            if subtotal > Decimal('1000'):
                other_discount = subtotal * Decimal('0.10')  # 10% of ORIGINAL subtotal
            
            # Calculate total discount
            total_discount = coupon_discount + other_discount
            
            # Calculate shipping and tax
            shipping_charge = Decimal('0') if subtotal > Decimal('500') else Decimal('40')
            tax_amount = (subtotal - coupon_discount) * Decimal('0.18')
            
            # Calculate total amount before wallet
            total_before_wallet = subtotal + shipping_charge + tax_amount - total_discount
            # ========== END FIXED CALCULATION ==========
            
            # Validate wallet payment
            wallet_amount_to_use = Decimal('0')
            if use_wallet and wallet_amount > 0:
                # Check wallet balance
                try:
                    if request.user.wallet.balance >= wallet_amount:
                        wallet_amount_to_use = min(wallet_amount, total_before_wallet)
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': 'Insufficient wallet balance.'
                        })
                except:
                    return JsonResponse({
                        'success': False,
                        'message': 'Wallet not found.'
                    })
            
            # Calculate final amount to pay
            final_amount = total_before_wallet - wallet_amount_to_use
            
            # Determine payment method based on wallet usage
            if wallet_amount_to_use >= total_before_wallet:
                payment_method = 'wallet'  # Full wallet payment
                payment_status = 'completed'
            elif wallet_amount_to_use > 0:
                payment_method = 'mixed'  # Mixed payment
                payment_status = 'pending' if final_amount > 0 else 'completed'
            else:
                payment_status = 'pending' if payment_method == 'online' else 'pending'
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                shipping_address=address,
                payment_method=payment_method,
                payment_status=payment_status,
                coupon=coupon,
                coupon_discount=coupon_discount,
                wallet_amount=wallet_amount_to_use,
                wallet_used=(wallet_amount_to_use > 0),
                subtotal=subtotal,
                discount_amount=total_discount,
                shipping_charge=shipping_charge,
                tax_amount=tax_amount,
                total_amount=final_amount,
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
            
            # Process wallet payment if any
            if wallet_amount_to_use > 0:
                # Deduct from wallet
                request.user.wallet.withdraw(
                    wallet_amount_to_use,
                    reason=f"Payment for order #{order.order_number}",
                    order=order
                )
            
            # Increment coupon usage if coupon was applied
            if coupon:
                coupon.increment_usage()
            
            # Clear cart after successful order
            cart.clear_cart()
            
            # Clear coupon from session
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']
            
            # Handle different payment scenarios
            if final_amount > 0:
                if payment_method in ['online', 'mixed'] and final_amount > 0:
                    # Need online payment for remaining amount
                    request.session['last_order_id'] = order.id
                    
                    return JsonResponse({
                        'success': True,
                        'payment_required': True,
                        'redirect_url': f'/payment/initiate/{order.id}/'
                    })
                else:
                    # COD for remaining amount
                    return JsonResponse({
                        'success': True,
                        'payment_required': False,
                        'redirect_url': f'/order-success/{order.id}/'
                    })
            else:
                # Fully paid with wallet
                order.payment_status = 'completed'
                order.save()
                
                return JsonResponse({
                    'success': True,
                    'payment_required': False,
                    'redirect_url': f'/order-success/{order.id}/'
                })
            
    except Exception as e:
        import traceback
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

