from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import razorpay
import json
from django.conf import settings
from datetime import timedelta
import hashlib
from decimal import Decimal, ROUND_DOWN
from ..models import Cart, Address, Order, OrderItem, Coupon, Wallet
from ..models.offer_models import ProductOffer, CategoryOffer, OfferApplication
from ..utils.offer_utils import apply_offers_to_cart, get_best_offer_for_product, calculate_seasonal_discount
from django.utils import timezone

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def cleanup_old_tokens(request):
    """Clean up tokens older than 1 hour"""
    one_hour_ago = timezone.now() - timedelta(hours=1)
    tokens_to_delete = []
    
    for key in list(request.session.keys()):
        if key.startswith(f'order_token_{request.user.id}_'):
            try:
                token_time = timezone.datetime.fromisoformat(request.session[key])
                if token_time < one_hour_ago:
                    tokens_to_delete.append(key)
            except:
                tokens_to_delete.append(key)
    
    for key in tokens_to_delete:
        del request.session[key]


@login_required
def checkout_view(request):
    """Checkout page view - WITH PROPER OFFER CALCULATIONS"""

    if 'checkout_calculations' in request.session:
        del request.session['checkout_calculations']

    cart = Cart.objects.filter(user=request.user).first()
    
    if not cart or cart.items.count() == 0:
        messages.error(request, "Your cart is empty!")
        return redirect('cart')
    
    addresses = Address.objects.filter(user=request.user)
    
    # ==========  GET WALLET PROPERLY ==========
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        # Create wallet if it doesn't exist
        wallet = Wallet.objects.create(user=request.user, balance=Decimal('0.00'))
    
    # Ensure wallet balance is a Decimal
    wallet_balance = wallet.balance if wallet.balance is not None else Decimal('0.00')
    
    # ========== 1. CALCULATE OFFER DISCOUNTS ==========
    offer_info = apply_offers_to_cart(cart)
    offer_discount = offer_info['total_discount']
    price_after_offers = offer_info['subtotal_after_discount']
    
    # ========== 2. CREATE ENHANCED CART ITEMS WITH OFFER INFO ==========
    enhanced_cart_items = []
    for item in cart.items.all():
        if item.id in offer_info['item_offers']:
            # Item has an offer
            offer_data = offer_info['item_offers'][item.id]
            enhanced_cart_items.append({
                'item': item,
                'product': item.variant.product,
                'variant': item.variant,
                'quantity': item.quantity,
                'original_price': float(item.variant.display_price),
                'offer_applied': True,
                'offer_name': offer_data['offer_name'],
                'offer_type': offer_data['offer_type'],
                'discount_per_item': float(offer_data['discount_per_unit']),
                'final_price_per_item': float(offer_data['final_price_per_unit']),
                'total_original': float(offer_data['total_original']),
                'total_discount': float(offer_data['total_discount']),
                'total_final': float(offer_data['total_final']),
            })
        else:
            # No offer applied
            enhanced_cart_items.append({
                'item': item,
                'product': item.variant.product,
                'variant': item.variant,
                'quantity': item.quantity,
                'original_price': float(item.variant.display_price),
                'offer_applied': False,
                'offer_name': None,
                'discount_per_item': 0,
                'final_price_per_item': float(item.variant.display_price),
                'total_original': float(item.total_price),
                'total_discount': 0,
                'total_final': float(item.total_price),
            })
    
    # ========== 3. CALCULATE SEASONAL DISCOUNT ==========
    seasonal_discount = calculate_seasonal_discount(price_after_offers)
    price_after_seasonal = price_after_offers - seasonal_discount
    
    # ========== 4. APPLY COUPON DISCOUNT ==========
    coupon_discount = Decimal('0')
    applied_coupon = None
    applied_coupon_data = None
    
    if 'applied_coupon' in request.session:
        coupon_data = request.session['applied_coupon']
        try:
            coupon = Coupon.objects.get(id=coupon_data['coupon_id'], active=True)
            # Check validity
            is_valid, message = coupon.is_valid(request.user, price_after_seasonal)
            if is_valid:
                coupon_discount = coupon.calculate_discount(price_after_seasonal)
                applied_coupon = coupon
                applied_coupon_data = {
                    'code': coupon.code,
                    'discount_type': coupon.discount_type,
                    'discount_value': float(coupon.discount_value),
                    'discount_amount': float(coupon_discount),
                }
            else:
                # Invalid coupon - remove from session
                del request.session['applied_coupon']
                messages.warning(request, message)
        except (Coupon.DoesNotExist, KeyError):
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']
    
    # ========== 5. FINAL PRICE AFTER ALL DISCOUNTS ==========
    price_after_coupon = price_after_seasonal - coupon_discount
    
    # ========== 6. CALCULATE SHIPPING ==========
    shipping_charge = Decimal('50.00')  # Default shipping
    if price_after_coupon >= Decimal('500.00'):
        shipping_charge = Decimal('0.00')  # Free shipping
    
    # ========== 7. CALCULATE TAX ==========
    tax_amount = price_after_coupon * Decimal('0.18')  # 18% GST
    
    # ========== 8. CALCULATE TOTAL BEFORE WALLET ==========
    total_before_wallet = price_after_coupon + shipping_charge + tax_amount
    
    # ========== 9. HANDLE WALLET PAYMENT ==========
    wallet_discount = Decimal('0')
    if request.method == 'POST' and request.POST.get('use_wallet') == 'true':
        wallet_amount = Decimal(request.POST.get('wallet_amount', '0'))
        wallet_discount = min(wallet_amount, wallet.balance, total_before_wallet)
    
    # ========== 10. CALCULATE FINAL TOTAL ==========
    total_amount = total_before_wallet - wallet_discount
    
    # ========== ADD THIS: Check COD eligibility ==========
    cod_disabled = total_amount > Decimal('1000.00')
    cod_disabled_message = 'Cash on Delivery is not available for orders above ₹1000'

    # ========== 11. STORE ALL CALCULATIONS IN SESSION (CONVERT DECIMALS TO FLOAT) ==========
    request.session['checkout_calculations'] = {
    'offer_discount': float(offer_discount),
    'seasonal_discount': float(seasonal_discount),
    'coupon_discount': float(coupon_discount),
    'total_discount': float(offer_discount + seasonal_discount + coupon_discount),
    'price_after_offers': float(price_after_offers),
    'price_after_seasonal': float(price_after_seasonal),
    'price_after_coupon': float(price_after_coupon),
    'shipping_charge': float(shipping_charge),
    'tax_amount': float(tax_amount),
    'total_before_wallet': float(total_before_wallet),
    'wallet_discount': float(wallet_discount),
    'total_amount': float(total_amount),
    'item_offers': {
        str(k): {
            'offer_id': v.get('offer_id'),
            'offer_name': v.get('offer_name'),
            'offer_type': v.get('offer_type'),
            'discount_per_unit': float(v.get('discount_per_unit', 0)),
            'final_price_per_unit': float(v.get('final_price_per_unit', 0)),
            'total_original': float(v.get('total_original', 0)),
            'total_discount': float(v.get('total_discount', 0)),
            'total_final': float(v.get('total_final', 0)),
        } for k, v in offer_info['item_offers'].items()
    },
}
    
    # ========== 12. PREPARE CONTEXT FOR TEMPLATE ==========
    context = {
        'cart': cart,
        'cart_items': enhanced_cart_items,
        'addresses': addresses,
        'wallet_balance': float(wallet_balance),  # Convert to float
        
        # Price breakdown - all converted to float for template
        'subtotal': float(cart.subtotal),
        'offer_discount': float(offer_discount),
        'seasonal_discount': float(seasonal_discount),
        'coupon_discount': float(coupon_discount),
        'total_discount': float(offer_discount + seasonal_discount + coupon_discount),
        'shipping_charge': float(shipping_charge),
        'tax_amount': float(tax_amount),
        'wallet_discount': float(wallet_discount),
        'total_amount': float(total_amount),
        
        # Applied items
        'applied_coupon': applied_coupon,
        'applied_coupon_data': applied_coupon_data,
        'available_coupons': Coupon.objects.filter(
            active=True, 
            valid_from__lte=timezone.now(), 
            valid_to__gte=timezone.now()
        )[:5],
        
        # Wallet
        'max_wallet_amount': float(min(wallet_balance, total_before_wallet)),
        'payment_required': total_amount > 0,

        'cod_disabled': cod_disabled,
        'cod_disabled_message': cod_disabled_message,
        
        # For debugging
        'price_after_offers': float(price_after_offers),
        'price_after_coupon': float(price_after_coupon),
        
        'title': 'Checkout - Sanjeri'
    }
    
    return render(request, 'checkout/checkout.html', context)

@login_required
@transaction.atomic
def place_order(request):
    """Place order view - WITH COMPREHENSIVE DEBUGGING"""

    # Add this right after getting calculations (around line 170-180)
    calculations = request.session.get('checkout_calculations')
    print("="*50)
    print("SESSION DATA VERIFICATION:")
    print(f"Type of calculations: {type(calculations)}")
    if calculations:
        for key, value in calculations.items():
            if key != 'item_offers':
                print(f"  {key}: {type(value)} - {value}")
            else:
                print(f"  {key}: {type(value)}")
                if isinstance(value, dict):
                    for item_id, offer_data in value.items():
                        print(f"    Item {item_id}:")
                        for offer_key, offer_val in offer_data.items():
                            print(f"      {offer_key}: {type(offer_val)}")


    print("\n" + "="*50)
    print("PLACE ORDER CALLED - DEBUG MODE")
    print("="*50)
    
    try:
        # Step 1: Check authentication
        print(f"Step 1 - User authenticated: {request.user.is_authenticated}")
        if not request.user.is_authenticated:
            print("ERROR: User not authenticated")
            return JsonResponse({
                'success': False,
                'message': 'Please login to continue',
                'login_required': True
            }, status=401)

        # Step 2: Check request method
        print(f"Step 2 - Request method: {request.method}")
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': 'Invalid request method'})

        # Step 3: Check AJAX header
        print(f"Step 3 - X-Requested-With: {request.headers.get('X-Requested-With')}")
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Invalid request type'
            }, status=400)

        # Step 4: Check POST data
        print(f"Step 4 - POST data keys: {list(request.POST.keys())}")
        print(f"Step 4 - POST data: {dict(request.POST)}")

        # Step 5: Check checkout token
        checkout_token = request.POST.get('checkout_token', '')
        print(f"Step 5 - checkout_token: {checkout_token}")

        # Step 6: Clean up old tokens
        print("Step 6 - Cleaning up old tokens")
        cleanup_old_tokens(request)

        # Step 7: Check for duplicate token
        if checkout_token:
            token_key = f'order_token_{request.user.id}_{checkout_token}'
            print(f"Step 7 - token_key: {token_key}")
            if request.session.get(token_key):
                print(f"⚠️ Duplicate submission detected with token: {checkout_token}")
                return JsonResponse({
                    'success': False,
                    'message': 'Duplicate order submission detected. Please check your orders.'
                })
            request.session[token_key] = timezone.now().isoformat()

        # Step 8: Check for recent order
        print("Step 8 - Checking for recent order")
        recent_order = Order.objects.filter(
            user=request.user,
            created_at__gte=timezone.now() - timedelta(seconds=30)
        ).first()
        
        if recent_order:
            print(f"Recent order detected: {recent_order.order_number}")
            cart = Cart.objects.filter(user=request.user).first()
            if cart and cart.subtotal == recent_order.subtotal:
                return JsonResponse({
                    'success': True,
                    'payment_required': False,
                    'redirect_url': reverse('order_success', args=[recent_order.id]),
                    'order_id': recent_order.id,
                    'order_number': recent_order.order_number,
                    'message': 'Order already placed'
                })

        # Step 9: Get user's cart
        print("Step 9 - Getting user's cart")
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            print("ERROR: Cart not found")
            return JsonResponse({'success': False, 'message': 'Cart not found!'})
        
        if cart.items.count() == 0:
            print("ERROR: Cart is empty")
            return JsonResponse({'success': False, 'message': 'Your cart is empty!'})
        
        print(f"Cart found with {cart.items.count()} items")

        # Step 10: Get calculations from session
        print("Step 10 - Getting checkout calculations from session")
        print(f"Session keys: {list(request.session.keys())}")
        
        calculations = request.session.get('checkout_calculations')
        if not calculations:
            print("ERROR: checkout_calculations not in session")
            return JsonResponse({
                'success': False, 
                'message': 'Checkout session expired. Please go back to checkout.'
            })
        
        print(f"Calculations keys: {list(calculations.keys())}")

        print("Step 11 - Creating Decimal versions for calculations")
        decimal_calculations = {}

        for key in list(calculations.keys()):
            if key != 'item_offers':
                print(f"  Key: {key}, Type: {type(calculations[key])}, Value: {calculations[key]}")
                if isinstance(calculations[key], (int, float)):
                    decimal_calculations[key] = Decimal(str(calculations[key]))
                else:
                    decimal_calculations[key] = calculations[key]
            else:
                # Handle item_offers separately
                decimal_calculations[key] = {}
                if isinstance(calculations[key], dict):
                    for item_id, offer_data in calculations[key].items():
                        decimal_calculations[key][item_id] = {}
                        for offer_key, offer_value in offer_data.items():
                            if isinstance(offer_value, (int, float)):
                                decimal_calculations[key][item_id][offer_key] = Decimal(str(offer_value))
                            else:
                                decimal_calculations[key][item_id][offer_key] = offer_value
                
        # Step 12: Get form data
        print("Step 12 - Getting form data")
        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method', 'cod')
        print(f"address_id: {address_id}, payment_method: {payment_method}")
        
        # Step 13: Validate address
        print("Step 13 - Validating address")
        if not address_id:
            return JsonResponse({'success': False, 'message': 'Please select an address!'})
            
        address = Address.objects.filter(id=address_id, user=request.user).first()
        if not address:
            print(f"ERROR: Address {address_id} not found for user {request.user.id}")
            return JsonResponse({'success': False, 'message': 'Please select a valid address!'})
        
        print(f"Address found: {address}")

        # Step 14: Get coupon from session
        print("Step 14 - Getting coupon from session")
        coupon = None
        if 'applied_coupon' in request.session:
            try:
                coupon_data = request.session['applied_coupon']
                print(f"Coupon data: {coupon_data}")
                coupon = Coupon.objects.get(id=coupon_data['coupon_id'])
                print(f"Coupon found: {coupon.code}")
            except (Coupon.DoesNotExist, KeyError) as e:
                print(f"Coupon error: {e}")
                pass
        
        # Step 15: Get wallet
        print("Step 15 - Getting wallet")
        wallet = None
        wallet_amount_used = Decimal('0')
        wallet_payment_only = False
        actual_payment_method = payment_method
        
        # Handle wallet payment
        if payment_method == 'wallet':
            print("Processing wallet-only payment")
            try:
                wallet = Wallet.objects.get(user=request.user)
                print(f"Wallet found with balance: {wallet.balance}")
                total_before_wallet = Decimal(calculations['total_before_wallet'])
                
                if wallet.balance < total_before_wallet:
                    return JsonResponse({
                        'success': False,
                        'message': f'Insufficient wallet balance. Need ₹{total_before_wallet - wallet.balance} more.'
                    })
                
                wallet_amount_used = total_before_wallet
                wallet_payment_only = True
                actual_payment_method = 'wallet'
                
            except Wallet.DoesNotExist:
                print("Wallet not found")
                return JsonResponse({
                    'success': False,
                    'message': 'Wallet not found. Please add money to your wallet first.'
                })
        else:
            print("Processing non-wallet payment")
            use_wallet = request.POST.get('use_wallet') == 'true'
            print(f"use_wallet: {use_wallet}")
            if use_wallet:
                wallet_amount = Decimal(request.POST.get('wallet_amount', '0'))
                print(f"wallet_amount: {wallet_amount}")
                if wallet_amount > 0:
                    try:
                        wallet = Wallet.objects.get(user=request.user)
                        print(f"Wallet found with balance: {wallet.balance}")
                        wallet_amount_used = min(wallet_amount, wallet.balance, Decimal(calculations['total_before_wallet']))
                        
                        if wallet_amount_used >= Decimal(calculations['total_before_wallet']):
                            wallet_payment_only = True
                            actual_payment_method = 'wallet'
                        else:
                            actual_payment_method = 'mixed'
                            
                    except Wallet.DoesNotExist:
                        print("Wallet not found")
                        wallet_amount_used = Decimal('0')
                        actual_payment_method = payment_method
                else:
                    actual_payment_method = payment_method
            else:
                actual_payment_method = payment_method

        print(f"wallet_amount_used: {wallet_amount_used}")
        print(f"wallet_payment_only: {wallet_payment_only}")
        print(f"actual_payment_method: {actual_payment_method}")

        # Step 16: Calculate final total
        print("Step 16 - Calculating final total")
        total_before_wallet = decimal_calculations['total_before_wallet'].quantize(Decimal('0.01'))
        wallet_amount_used = wallet_amount_used.quantize(Decimal('0.01'))
        total_amount = (total_before_wallet - wallet_amount_used).quantize(Decimal('0.01'))
        print(f"total_before_wallet: {total_before_wallet}")
        print(f"total_amount: {total_amount}")
        
        # Step 17: CREATE ORDER
        print("Step 17 - Creating order")
        print(f"Creating order with:")
        print(f"  subtotal: {cart.subtotal}")
        print(f"  offer_discount: {calculations['offer_discount']}")
        print(f"  coupon_discount: {calculations['coupon_discount']}")
        print(f"  discount_amount: {calculations['total_discount']}")
        print(f"  shipping_charge: {calculations['shipping_charge']}")
        print(f"  tax_amount: {calculations['tax_amount']}")
        print(f"  total_amount: {total_amount}")
        
        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            
            # Order totals
            subtotal=cart.subtotal,
            offer_discount=decimal_calculations['offer_discount'].quantize(Decimal('0.01')),
            coupon=coupon,
            coupon_discount=Decimal(calculations['coupon_discount']).quantize(Decimal('0.01')),
            discount_amount=Decimal(calculations['total_discount']).quantize(Decimal('0.01')),
            shipping_charge=Decimal(calculations['shipping_charge']).quantize(Decimal('0.01')),
            tax_amount=Decimal(calculations['tax_amount']).quantize(Decimal('0.01')),
            total_amount=total_amount,
            
            # Payment info
            payment_method=actual_payment_method,
            payment_status='completed' if wallet_payment_only else 'pending',
            status='confirmed' if wallet_payment_only else 'pending_payment',
            wallet_amount_used=wallet_amount_used,
        )
        print(f"Order created with ID: {order.id}")

        # Step 18: CREATE ORDER ITEMS
        print("Step 18 - Creating order items")
        item_offers = calculations.get('item_offers', {})
        print(f"item_offers keys: {list(item_offers.keys())}")
        
        for cart_item in cart.items.select_related('variant__product').all():
            print(f"Processing cart item: {cart_item.id}")
            product = cart_item.variant.product
            variant_display = f"{cart_item.variant.volume_ml}ml ({cart_item.variant.gender})"
            unit_price = cart_item.variant.display_price
            
            cart_item_id_str = str(cart_item.id)
            if cart_item_id_str in item_offers:
                print(f"  Item has offer: {cart_item_id_str}")
                offer_data = item_offers[cart_item_id_str]
                print(f"  offer_data: {offer_data}")
                final_price_per_unit = Decimal(offer_data['final_price_per_unit'])
                item_total = final_price_per_unit * cart_item.quantity
                
                order_item = OrderItem.objects.create(
                    order=order,
                    variant=cart_item.variant,
                    product_name=product.name,
                    variant_details=variant_display,
                    quantity=cart_item.quantity,
                    unit_price=unit_price,
                    total_price=item_total,
                    product_image=product.main_image if product.main_image else None
                )
                print(f"  Order item created with offer: {order_item.id}")
                
                if offer_data.get('offer_id'):
                    OfferApplication.objects.create(
                        offer_type=offer_data['offer_type'],
                        product_offer=ProductOffer.objects.get(id=offer_data['offer_id']) 
                                    if offer_data['offer_type'] == 'product' else None,
                        category_offer=CategoryOffer.objects.get(id=offer_data['offer_id'])
                                      if offer_data['offer_type'] == 'category' else None,
                        order=order,
                        order_item=order_item,
                        product=product,
                        original_price=unit_price * cart_item.quantity,
                        discount_amount=offer_data['total_discount'],
                        final_price=item_total,
                        offer_name=offer_data['offer_name'],
                        applied_at=timezone.now()
                    )
                    
                    if offer_data['offer_type'] == 'product':
                        offer = ProductOffer.objects.get(id=offer_data['offer_id'])
                        offer.increment_usage()
                    elif offer_data['offer_type'] == 'category':
                        offer = CategoryOffer.objects.get(id=offer_data['offer_id'])
                        offer.increment_usage()
            else:
                print(f"  Item has no offer")
                order_item = OrderItem.objects.create(
                    order=order,
                    variant=cart_item.variant,
                    product_name=product.name,
                    variant_details=variant_display,
                    quantity=cart_item.quantity,
                    unit_price=unit_price,
                    total_price=unit_price * cart_item.quantity,
                    product_image=product.main_image if product.main_image else None
                )

        # Step 19: HANDLE WALLET WITHDRAWAL
        print("Step 19 - Handling wallet withdrawal")
        if wallet_amount_used > 0 and wallet:
            try:
                print(f"Processing wallet withdrawal: {wallet_amount_used}")
                wallet.withdraw(
                    amount=wallet_amount_used,
                    reason=f"Payment for order #{order.order_number}",
                    order=order
                )
                print("Wallet withdrawal successful")
            except Exception as e:
                print(f"Wallet withdrawal failed: {str(e)}")
                order.delete()
                return JsonResponse({
                    'success': False, 
                    'message': f'Wallet payment failed: {str(e)}'
                })

        # Step 20: INCREMENT COUPON USAGE
        print("Step 20 - Incrementing coupon usage")
        if coupon:
            coupon.increment_usage()

        # Step 21: HANDLE DIFFERENT PAYMENT SCENARIOS
        print("Step 21 - Handling payment scenarios")
        
        # Case 1: Wallet only (full payment)
        if wallet_payment_only:
            print("Case 1: Wallet only payment")
            order.payment_status = 'completed'
            order.status = 'confirmed'
            order.save()
            
            # Clear cart
            cart.items.all().delete()
            
            # Clear session data
            if 'checkout_calculations' in request.session:
                del request.session['checkout_calculations']
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']
                
            return JsonResponse({
                'success': True,
                'payment_required': False,
                'redirect_url': reverse('order_success', args=[order.id]),
                'order_id': order.id,
                'order_number': order.order_number
            })
        
        # Case 2: Mixed payment or online payment
        elif actual_payment_method in ['mixed', 'online'] and total_amount > 0:
            print("Case 2: Mixed or online payment")
            order.payment_status = 'partially_paid' if actual_payment_method == 'mixed' else 'pending'
            order.status = 'pending_payment'
            order.save()
            
            # Create Razorpay order
            amount_in_paise = int(total_amount * 100)
            print(f"Creating Razorpay order for amount: {amount_in_paise}")
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1',
                'receipt': order.order_number,
                'notes': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'user_id': str(request.user.id)
                }
            })
            
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            return JsonResponse({
                'success': True,
                'payment_required': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'key': settings.RAZORPAY_KEY_ID,
                'amount': amount_in_paise,
                'currency': 'INR',
                'razorpay_order_id': razorpay_order['id'],
                'customer_name': request.user.get_full_name() or request.user.username,
                'customer_email': request.user.email,
                'customer_phone': address.phone,
            })
        
        # Case 3: Cash on Delivery
        elif actual_payment_method == 'cod':
            if decimal_calculations['total_amount'] <Decimal('1000.00'):            
                print("Case 3: Cash on Delivery")
                order.payment_status = 'pending'
                order.status = 'confirmed'
                order.save()
                
                # Clear cart
                cart.items.all().delete()
                
                # Clear session data
                if 'checkout_calculations' in request.session:
                    del request.session['checkout_calculations']
                if 'applied_coupon' in request.session:
                    del request.session['applied_coupon']

                return JsonResponse({
                    'success': True,
                    'payment_required': False,
                    'redirect_url': reverse('order_success', args=[order.id]),
                    'order_id': order.id,
                    'order_number': order.order_number
                })
            else:
                # Reject COD for orders above ₹1000
                print(f"COD not allowed for orders above ₹1000. Amount: {decimal_calculations['total_amount']}")
                order.delete()  # Delete the order since we can't proceed
                return JsonResponse({
                    'success': False,
                    'message': 'Cash on Delivery is not available for orders above ₹1000. Please choose another payment method.'
                })
                # In your checkout_view, add this to context:
                context['cod_disabled'] = total_amount > 1000
                context['cod_disabled_message'] = 'Cash on Delivery not available for orders above ₹1000'

        else:
            print("Case 4: Default case")
            order.payment_status = 'pending'
            order.status = 'pending_payment'
            order.save()
            
            return JsonResponse({
                'success': True,
                'payment_required': False,
                'redirect_url': reverse('order_success', args=[order.id]),
                'order_id': order.id,
                'order_number': order.order_number
            })
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'message': f'Error: {str(e)}'
        })
        

@login_required
def _clear_checkout_session(request):
    """Helper to clear checkout session data"""
    if 'checkout_calculations' in request.session:
        del request.session['checkout_calculations']
    if 'applied_coupon' in request.session:
        del request.session['applied_coupon']


@csrf_exempt
def verify_payment(request):
    """Verify Razorpay payment and clear cart"""
    print("\n=== PAYMENT VERIFICATION ===")
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    
    try:
        # Parse request data
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        order_id = data.get('order_id')
        
        # Get the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'})
        
        # Check if order is already paid
        if order.payment_status == 'completed':
            return JsonResponse({
                'success': True,
                'message': 'Payment already verified',
                'redirect_url': reverse('order_success', args=[order.id])
            })
        
        # Verify signature
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
            client.utility.verify_payment_signature(params_dict)
            
            # Update order
            order.payment_status = 'completed'
            order.status = 'confirmed'
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save()
            
            # Clear cart
            cart = Cart.objects.filter(user=order.user).first()
            if cart:
                cart.items.all().delete()
            
            # Clear session
            if request.user.is_authenticated:
                if 'checkout_calculations' in request.session:
                    del request.session['checkout_calculations']
                if 'applied_coupon' in request.session:
                    del request.session['applied_coupon']
            
            return JsonResponse({
                'success': True,
                'message': 'Payment verified successfully',
                'redirect_url': reverse('order_success', args=[order.id])
            })
            
        except razorpay.errors.SignatureVerificationError:
            order.payment_status = 'failed'
            order.save()
            return JsonResponse({
                'success': False,
                'message': 'Payment signature verification failed'
            })
            
    except Exception as e:
        print(f"Error in verify_payment: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def order_success(request, order_id):
    """Order success page"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if this is a page refresh
        if request.session.get('last_viewed_order') == order_id:
            messages.info(request, "This order has already been confirmed.")
        else:
            request.session['last_viewed_order'] = order_id

        # Get offer applications for display
        offer_applications = OfferApplication.objects.filter(order=order).select_related(
            'product_offer', 'category_offer', 'order_item'
        )
        
        # Group offers by order item
        item_offers = {}
        for app in offer_applications:
            item_offers[app.order_item.id] = {
                'offer_name': app.offer_name,
                'offer_type': app.offer_type,
                'discount_amount': app.discount_amount,
            }
        
        # Enhance order items with offer info
        enhanced_items = []
        for item in order.items.all():
            item_data = {
                'item': item,
                'has_offer': item.id in item_offers,
                'offer_info': item_offers.get(item.id),
            }
            enhanced_items.append(item_data)
        
        context = {
            'order': order,
            'order_items': enhanced_items,
            'offer_applications': offer_applications,
            'title': f'Order Confirmed - #{order.order_number}',
        }
        
        return render(request, 'checkout/order_success.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, "Order not found!")
        return redirect('order_list')
    

@login_required
def payment_failed(request, order_id):
    """Payment failed page - restores cart from failed order"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Ensure the order is in a failed state
        if order.payment_status != 'failed':
            order.payment_status = 'failed'
            order.save()
            
        # Restore cart items from failed order
        cart, created = Cart.objects.get_or_create(user=request.user)
        restored_items = 0
        
        for order_item in order.items.all():
            if order_item.variant and order_item.variant.stock_quantity > 0:
                from ..models import CartItem
                cart_item, item_created = CartItem.objects.get_or_create(
                    cart=cart,
                    variant=order_item.variant,
                    defaults={'quantity': order_item.quantity}
                )
                
                if not item_created:
                    cart_item.quantity += order_item.quantity
                    cart_item.save()
                
                restored_items += 1
        
        if restored_items > 0:
            messages.info(request, f"{restored_items} item(s) have been restored to your cart.")
        
    except Order.DoesNotExist:
        order = None
        messages.error(request, "Order not found")
    except Exception as e:
        messages.error(request, f"Error restoring cart: {str(e)}")
    
    context = {
        'order': order,
        'title': 'Payment Failed - Sanjeri'
    }
    
    return render(request, 'payment/payment_failed.html', context)