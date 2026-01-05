import razorpay
import json
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from ..models import Order, Cart
from decimal import Decimal

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@login_required
def initiate_payment(request, order_id):
    """Initiate Razorpay payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not order.can_pay_online:
        messages.error(request, "This order cannot be paid online.")
        return redirect('order_detail', order_id=order.id)
    
    # Create Razorpay order
    amount_in_paise = int(order.total_amount * 100)  # Razorpay expects amount in paise
    
    razorpay_order = razorpay_client.order.create({
        'amount': amount_in_paise,
        'currency': 'INR',
        'payment_capture': 1,  # Auto capture payment
        'notes': {
            'order_id': order.id,
            'order_number': order.order_number,
            'user_id': request.user.id
        }
    })
    
    # Update order with Razorpay order ID
    order.razorpay_order_id = razorpay_order['id']
    order.save()
    
    context = {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount': amount_in_paise,
        'currency': 'INR',
        'user_name': request.user.get_full_name(),
        'user_email': request.user.email,
        'user_phone': request.user.phone if hasattr(request.user, 'phone') else '',
    }
    
    return render(request, 'payment/payment_gateway.html', context)

@login_required
@csrf_exempt
def payment_success(request):
    """Handle successful payment"""
    if request.method == 'POST':
        try:
            # Get payment details from request
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify the payment signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Get order
            order = Order.objects.get(
                razorpay_order_id=razorpay_order_id,
                user=request.user
            )
            
            # Update order payment status
            order.payment_status = 'completed'
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.payment_method = 'online'
            order.save()
            
            # Redirect to success page
            return redirect('order_success', order_id=order.id)
            
        except razorpay.errors.SignatureVerificationError:
            messages.error(request, "Payment verification failed. Please contact support.")
            return redirect('payment_failed')
        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
            return redirect('payment_failed')
    return redirect('homepage')

@login_required
def payment_failed(request):
    """Payment failed page"""
    order_id = request.session.get('last_order_id')
    order = None
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            pass
    
    context = {
        'order': order,
        'title': 'Payment Failed - Sanjeri'
    }
    return render(request, 'payment/payment_failed.html', context)

@login_required
def retry_payment(request, order_id):
    """Retry payment for failed order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not order.can_pay_online:
        messages.error(request, "This order cannot be retried for payment.")
        return redirect('order_detail', order_id=order.id)
    
    return redirect('initiate_payment', order_id=order.id)

# PayPal Integration (Optional - Add if needed)
@login_required
def initiate_paypal_payment(request, order_id):
    """Initiate PayPal payment"""
    # This requires PayPal SDK setup
    # You'll need to implement this based on PayPal's documentation
    pass

@login_required
def paypal_callback(request):
    """Handle PayPal callback"""
    pass
