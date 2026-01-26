from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import razorpay
import json
from ..models import Order

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def initiate_payment(request, order_id):
    """Initiate Razorpay payment for an existing order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not order.can_pay_online:
        return JsonResponse({
            'success': False,
            'message': 'This order cannot be paid online.'
        })
    
    try:
        # Convert amount to paise
        amount_paise = int(order.amount_to_pay * 100)
        
        # Create Razorpay order
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
        
        # Update order with Razorpay order ID
        order.razorpay_order_id = razorpay_order['id']
        order.save()
        
        return JsonResponse({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'amount': amount_paise,
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID,
            'order_number': order.order_number,
            'customer_name': request.user.get_full_name() or request.user.username,
            'customer_email': request.user.email,
            'customer_phone': getattr(request.user.profile, 'phone', ''),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Payment initiation failed: {str(e)}'
        })

@login_required
def payment_retry(request, order_id):
    """Retry failed payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Reset payment status to allow retry
    if order.payment_status == 'failed':
        order.payment_status = 'pending'
        order.save()
    
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
    return render(request, 'payment/details.html', context)



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