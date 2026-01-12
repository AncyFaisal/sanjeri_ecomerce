# Add these imports at the top of views.py
import razorpay
import json
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Order

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def checkout_payment(request, order_id):
    """Select payment method"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'online':
            return redirect('initiate_payment', order_id=order.id)
        elif payment_method == 'cod':
            order.payment_method = 'cod'
            order.status = 'confirmed'
            order.save()
            messages.success(request, "Order placed with Cash on Delivery!")
            return redirect('order_detail', order_id=order.id)
    
    return render(request, 'payment/checkout.html', {'order': order})

@login_required
def initiate_payment(request, order_id):
    """Create Razorpay order and show payment page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order can be paid
    if order.payment_status == 'completed':
        messages.info(request, "Payment already completed for this order.")
        return redirect('order_detail', order_id=order.id)
    
    if order.status == 'cancelled':
        messages.error(request, "This order has been cancelled.")
        return redirect('order_detail', order_id=order.id)
    
    # Convert amount to paise (Razorpay requires amount in smallest currency unit)
    amount_paise = int(order.total_amount * 100)
    
    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'payment_capture': '1',  # Auto capture payment
        'notes': {
            'order_id': str(order.id),
            'user_id': str(request.user.id)
        }
    })
    
    # Save Razorpay order ID to your order
    order.razorpay_order_id = razorpay_order['id']
    order.save()
    
    # Prepare context for payment template
    context = {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount': amount_paise,
        'currency': 'INR',
        'user_name': request.user.get_full_name() or request.user.email,
        'user_email': request.user.email,
        'user_phone': request.user.phone if hasattr(request.user, 'phone') else '',
    }
    
    return render(request, 'payment/razorpay_payment.html', context)

@csrf_exempt
def payment_webhook(request):
    """Handle Razorpay webhook for payment verification"""
    if request.method == 'POST':
        try:
            # Get webhook data
            webhook_body = request.body.decode('utf-8')
            webhook_data = json.loads(webhook_body)
            
            # Verify webhook signature (optional for now)
            event = webhook_data.get('event', '')
            
            if event == 'payment.captured':
                payment = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
                razorpay_payment_id = payment.get('id', '')
                razorpay_order_id = payment.get('order_id', '')
                amount = payment.get('amount', 0) / 100  # Convert from paise
                
                # Update order
                try:
                    order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                    order.payment_status = 'completed'
                    order.razorpay_payment_id = razorpay_payment_id
                    order.status = 'confirmed'
                    order.save()
                    
                    print(f"✅ Webhook: Order {order.order_number} payment captured")
                except Order.DoesNotExist:
                    print(f"❌ Webhook: Order not found for {razorpay_order_id}")
            
        except Exception as e:
            print(f"Webhook error: {e}")
    
    return HttpResponse(status=200)

@login_required
def payment_success(request):
    """Handle successful payment return"""
    razorpay_payment_id = request.GET.get('razorpay_payment_id', '')
    razorpay_order_id = request.GET.get('razorpay_order_id', '')
    razorpay_signature = request.GET.get('razorpay_signature', '')
    
    if razorpay_order_id:
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
            
            # Verify payment (optional for now - webhook handles it)
            order.payment_status = 'completed'
            order.razorpay_payment_id = razorpay_payment_id
            order.status = 'confirmed'
            order.save()
            
            messages.success(request, "Payment successful! Order confirmed.")
            return render(request, 'payment/success.html', {'order': order})
            
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
    
    return redirect('homepage')

@login_required
def payment_failure(request, order_id):
    """Payment failure page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.payment_status = 'failed'
    order.save()
    
    return render(request, 'payment/failure.html', {'order': order})

@login_required
def retry_payment(request, order_id):
    """Retry failed payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.payment_status == 'failed':
        return redirect('initiate_payment', order_id=order.id)
    
    return redirect('order_detail', order_id=order.id)