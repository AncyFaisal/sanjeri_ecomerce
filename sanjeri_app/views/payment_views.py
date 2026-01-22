# sanjeri_app/views/payment_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
import json
import logging

from ..models import Order, PaymentTransaction
from ..services.razorpay_service import RazorpayService
from django.conf import settings

logger = logging.getLogger(__name__)
razorpay_service = RazorpayService()

@login_required
def initiate_payment(request, order_id):
    """Initiate payment for an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order can be paid
    if not order.can_pay_online:
        messages.error(request, "This order cannot be paid online.")
        return redirect('order_detail', order_id=order.id)
    
    # Calculate amount to pay (after wallet deduction)
    amount_to_pay = order.amount_to_pay
    
    # Create Razorpay order
    result = razorpay_service.create_order(
        amount_in_rupees=float(amount_to_pay),
        notes={
            'order_id': str(order.id),
            'order_number': order.order_number,
            'user_id': str(request.user.id)
        }
    )
    
    if not result['success']:
        messages.error(request, f"Payment initiation failed: {result['error']}")
        return redirect('order_detail', order_id=order.id)
    
    # Create payment transaction record
    payment_transaction = PaymentTransaction.objects.create(
        order=order,
        user=request.user,
        razorpay_order_id=result['order_id'],
        amount=amount_to_pay,
        status='created'
    )
    
    # Return Razorpay data to frontend
    return JsonResponse({
        'success': True,
        'razorpay_order_id': result['order_id'],
        'amount': result['amount'],
        'currency': result['currency'],
        'key': settings.RAZORPAY_KEY_ID,
        'customer_name': request.user.get_full_name() or request.user.username,
        'customer_email': request.user.email,
        'customer_phone': getattr(request.user, 'phone', ''),
        'order_id': order.id,
    })

@csrf_exempt
@login_required
def verify_payment(request):
    """Verify payment callback from Razorpay"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')
            order_id = data.get('order_id')
            
            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, order_id]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing payment data'
                })
            
            # Get payment transaction
            payment_transaction = PaymentTransaction.objects.get(
                razorpay_order_id=razorpay_order_id,
                order_id=order_id,
                user=request.user
            )
            
            # Verify signature
            is_valid = razorpay_service.verify_payment_signature(
                razorpay_order_id,
                razorpay_payment_id,
                razorpay_signature
            )
            
            if not is_valid:
                payment_transaction.mark_as_failed("Invalid payment signature")
                return JsonResponse({
                    'success': False,
                    'message': 'Payment verification failed'
                })
            
            # Update payment transaction
            payment_transaction.mark_as_captured(
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature
            )
            
            # Update order
            order = payment_transaction.order
            order.payment_status = 'completed'
            order.razorpay_payment_id = razorpay_payment_id
            order.status = 'confirmed'
            order.save()
            
            messages.success(request, "Payment successful! Order confirmed.")
            
            return JsonResponse({
                'success': True,
                'message': 'Payment verified successfully',
                'redirect_url': reverse('order_success', args=[order.id])
            })
            
        except PaymentTransaction.DoesNotExist:
            logger.error(f"Payment transaction not found for order: {order_id}")
            return JsonResponse({
                'success': False,
                'message': 'Payment record not found'
            })
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Payment verification failed: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

@login_required
def payment_retry(request, order_id):
    """Retry failed payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if there's a failed payment transaction
    failed_payment = order.payment_transactions.filter(status='failed').last()
    
    if failed_payment and failed_payment.can_retry():
        # Initiate new payment
        return initiate_payment(request, order_id)
    
    messages.error(request, "Cannot retry payment for this order.")
    return redirect('order_detail', order_id=order.id)

@login_required
def payment_details(request, order_id):
    """View payment details for an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'payment_transactions': order.payment_transactions.all(),
    }
    return render(request, 'payments/payment_details.html', context)