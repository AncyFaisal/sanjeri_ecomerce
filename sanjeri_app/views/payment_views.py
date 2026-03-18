from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import razorpay
import json
from ..models import Order
from decimal import Decimal
import traceback
import logging

logger = logging.getLogger(__name__)


# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# payment_views.py
import traceback
import logging

logger = logging.getLogger(__name__)

@login_required
def initiate_payment(request, order_id):
    """Initiate Razorpay payment for an existing order"""
    print(f"🔵 INITIATE PAYMENT CALLED for order {order_id}")
    print(f"🔵 User: {request.user.id} - {request.user.email}")
    print(f"🔵 Request method: {request.method}")
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        print(f"🔵 Order found: #{order.order_number}")
        print(f"🔵 Order status: {order.status}")
        print(f"🔵 Payment status: {order.payment_status}")
        print(f"🔵 Payment method: {order.payment_method}")
        print(f"🔵 Amount to pay: {order.amount_to_pay}")
        print(f"🔵 Can pay online: {order.can_pay_online}")
        
        # Check if order can be paid online
        if not order.can_pay_online:
            error_msg = f'This order cannot be paid online. Status: {order.status}, Payment: {order.payment_status}'
            print(f"🔴 {error_msg}")
            return JsonResponse({
                'success': False,
                'message': error_msg
            })
        
        # Convert amount to paise
        amount_paise = int(order.amount_to_pay * 100)
        print(f"🔵 Amount in paise: {amount_paise}")
        
        # Create Razorpay order
        try:
            import razorpay
            from django.conf import settings
            
            print(f"🔵 Razorpay Key ID: {settings.RAZORPAY_KEY_ID[:10]}...")
            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            razorpay_order = client.order.create({
                'amount': amount_paise,
                'currency': 'INR',
                'payment_capture': 1,
                'notes': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'user_id': str(request.user.id)
                }
            })
            
            print(f"🔵 Razorpay order created: {razorpay_order['id']}")
            
            # Update order with Razorpay order ID
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            # Get user phone (handle case where profile doesn't exist)
            user_phone = ''
            if hasattr(request.user, 'profile') and request.user.profile:
                user_phone = getattr(request.user.profile, 'phone', '')
            
            response_data = {
                'success': True,
                'razorpay_order_id': razorpay_order['id'],
                'amount': amount_paise,
                'currency': 'INR',
                'key': settings.RAZORPAY_KEY_ID,
                'order_number': order.order_number,
                'customer_name': request.user.get_full_name() or request.user.username,
                'customer_email': request.user.email,
                'customer_phone': user_phone,
            }
            print(f"✅ Payment initiated successfully for order #{order.order_number}")
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"🔴 Razorpay order creation failed: {str(e)}")
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Razorpay order creation failed: {str(e)}'
            })
        
    except Order.DoesNotExist:
        print(f"🔴 Order {order_id} not found for user {request.user.id}")
        return JsonResponse({
            'success': False,
            'message': 'Order not found'
        })
    except Exception as e:
        print(f"🔴 Unexpected error: {str(e)}")
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Payment initiation failed: {str(e)}'
        })

@login_required
def payment_retry(request, order_id):
    """Retry failed payment"""
    print(f"🟡 PAYMENT RETRY CALLED for order {order_id}")
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        print(f"🟡 Order found: #{order.order_number}")
        print(f"🟡 Current payment status: {order.payment_status}")
        
        # Reset payment status to allow retry
        if order.payment_status == 'failed':
            order.payment_status = 'pending'
            order.status = 'pending_payment'
            order.razorpay_order_id = None
            order.razorpay_payment_id = None
            order.razorpay_signature = None
            order.save()
            print(f"✅ Order status reset for retry")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Order status reset for retry'
                })
        else:
            print(f"🟡 Order payment status is {order.payment_status}, not resetting")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Order already in retryable state'
                })
        
        return redirect('order_detail', order_id=order_id)
        
    except Exception as e:
        print(f"🔴 Error in payment_retry: {str(e)}")
        traceback.print_exc()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
        return redirect('order_detail', order_id=order_id)

@login_required
def payment_details(request, order_id):
    """Show payment details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'payment_details': {
            'razorpay_order_id': order.razorpay_order_id,
            'razorpay_payment_id': order.razorpay_payment_id,
            'amount': order.total_amount,
        }
    }
    return render(request, 'payment/payment_details.html', context)



# @login_required
# def payment_failed(request, order_id):
#     """Payment failure page"""
#     order = get_object_or_404(Order, id=order_id, user=request.user)
    
#     context = {
#         'order': order,
#         'order_items': order.items.all(),
#     }
#     return render(request, 'payment/failure.html', context)



# Note: verify_payment is now in checkout.py since it needs to update order status