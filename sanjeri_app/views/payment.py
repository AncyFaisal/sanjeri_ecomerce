# # payment.py
# import razorpay
# import json
# from django.conf import settings
# from django.shortcuts import render, redirect, get_object_or_404
# from django.views.decorators.csrf import csrf_exempt
# from django.http import HttpResponse, JsonResponse
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from ..models import Order, Cart
# from django.urls import reverse
# import logging

# # Initialize logger
# logger = logging.getLogger(__name__)

# # Initialize Razorpay client
# razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# @csrf_exempt
# def payment_webhook(request):
#     """Handle Razorpay webhook for payment verification"""
#     if request.method == 'POST':
#         try:
#             # Get webhook data
#             webhook_body = request.body.decode('utf-8')
#             webhook_data = json.loads(webhook_body)
            
#             # Verify webhook signature (optional for now)
#             event = webhook_data.get('event', '')
#             logger.info(f"Webhook received: {event}")
            
#             if event == 'payment.captured':
#                 payment = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
#                 razorpay_payment_id = payment.get('id', '')
#                 razorpay_order_id = payment.get('order_id', '')
#                 amount = payment.get('amount', 0) / 100  # Convert from paise
                
#                 # Update order
#                 try:
#                     order = Order.objects.get(razorpay_order_id=razorpay_order_id)
#                     if order.payment_status != 'completed':
#                         order.payment_status = 'completed'
#                         order.razorpay_payment_id = razorpay_payment_id
#                         order.status = 'confirmed'
#                         order.save()
                        
#                         logger.info(f"Webhook: Order {order.order_number} payment captured")
#                     else:
#                         logger.info(f"Webhook: Order {order.order_number} already completed")
                        
#                 except Order.DoesNotExist:
#                     logger.error(f"Webhook: Order not found for {razorpay_order_id}")
            
#             elif event == 'payment.failed':
#                 payment = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
#                 razorpay_order_id = payment.get('order_id', '')
#                 error_reason = payment.get('error_description', 'Unknown error')
                
#                 try:
#                     order = Order.objects.get(razorpay_order_id=razorpay_order_id)
#                     order.payment_status = 'failed'
#                     order.save()
#                     logger.error(f"Webhook: Order {order.order_number} payment failed: {error_reason}")
#                 except Order.DoesNotExist:
#                     logger.error(f"Webhook: Order with razorpay_id {razorpay_order_id} not found")
            
#         except Exception as e:
#             logger.error(f"Webhook error: {e}")
    
#     return HttpResponse(status=200)

# @csrf_exempt
# @login_required
# def verify_payment(request):
#     """Verify Razorpay payment and update order"""
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             print("🎯 Verification data:", data)
            
#             # Get payment details
#             razorpay_payment_id = data.get('razorpay_payment_id')
#             razorpay_order_id = data.get('razorpay_order_id')
#             razorpay_signature = data.get('razorpay_signature')
#             order_id = data.get('order_id')
            
#             print(f"🔍 Payment ID: {razorpay_payment_id}")
#             print(f"🔍 Order ID: {razorpay_order_id}")
#             print(f"🔍 Signature: {razorpay_signature[:20]}...")
#             print(f"🔍 Order ID from frontend: {order_id}")
            
#             if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, order_id]):
#                 return JsonResponse({
#                     'success': False,
#                     'message': 'Missing payment data'
#                 })
            
#             # Get the order
#             order = Order.objects.get(id=order_id, user=request.user)
#             print(f"✅ Found order: {order.order_number}")
            
#             # IMPORTANT: Verify payment signature
#             try:
#                 # Create parameters dictionary for verification
#                 params_dict = {
#                     'razorpay_order_id': razorpay_order_id,
#                     'razorpay_payment_id': razorpay_payment_id,
#                     'razorpay_signature': razorpay_signature
#                 }
                
#                 print("🔐 Verifying signature...")
                
#                 # Verify with Razorpay
#                 razorpay_client.utility.verify_payment_signature(params_dict)
#                 print("✅ Signature verification successful!")
                
#             except razorpay.errors.SignatureVerificationError as e:
#                 print(f"❌ Signature verification failed: {str(e)}")
#                 # For testing, you might want to skip this, but in production keep it
#                 return JsonResponse({
#                     'success': False,
#                     'message': f'Payment verification failed: {str(e)}'
#                 })
            
#             # Payment verified successfully
#             order.payment_status = 'completed'
#             order.razorpay_payment_id = razorpay_payment_id
#             order.razorpay_order_id = razorpay_order_id
#             order.status = 'confirmed'
#             order.save()
            
#             print(f"✅ Order {order.order_number} marked as paid!")
            
#             return JsonResponse({
#                 'success': True,
#                 'message': 'Payment verified successfully',
#                 'redirect_url': reverse('order_success', args=[order.id])
#             })
            
#         except Order.DoesNotExist:
#             print(f"❌ Order {order_id} not found")
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Order not found'
#             })
#         except Exception as e:
#             print(f"❌ Error in verify_payment: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return JsonResponse({
#                 'success': False,
#                 'message': f'Payment verification failed: {str(e)}'
#             })
    
#     return JsonResponse({
#         'success': False,
#         'message': 'Invalid request method'
#     })

# @login_required
# def payment_success(request):
#     """Payment success page (fallback if JavaScript verification fails)"""
#     razorpay_payment_id = request.GET.get('razorpay_payment_id', '')
#     razorpay_order_id = request.GET.get('razorpay_order_id', '')
#     razorpay_signature = request.GET.get('razorpay_signature', '')
    
#     if razorpay_order_id:
#         try:
#             order = Order.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
            
#             # Verify payment (optional for now - webhook handles it)
#             if order.payment_status != 'completed':
#                 order.payment_status = 'completed'
#                 order.razorpay_payment_id = razorpay_payment_id
#                 order.status = 'confirmed'
#                 order.save()
            
#             messages.success(request, "Payment successful! Order confirmed.")
#             return render(request, 'payment/success.html', {'order': order})
            
#         except Order.DoesNotExist:
#             messages.error(request, "Order not found.")
    
#     return redirect('order_list')

# @login_required
# def payment_failure(request, order_id):
#     """Payment failure page"""
#     order = get_object_or_404(Order, id=order_id, user=request.user)
#     order.payment_status = 'failed'
#     order.save()
    
#     return render(request, 'payment/failure.html', {'order': order})

# @login_required
# def retry_payment(request, order_id):
#     """Retry failed payment"""
#     order = get_object_or_404(Order, id=order_id, user=request.user)
    
#     if order.payment_status == 'failed':
#         try:
#             # Create new Razorpay order
#             amount_paise = int(order.total_amount * 100)
            
#             razorpay_order = razorpay_client.order.create({
#                 'amount': amount_paise,
#                 'currency': 'INR',
#                 'payment_capture': '1',
#                 'notes': {
#                     'order_id': str(order.id),
#                     'user_id': str(request.user.id)
#                 }
#             })
            
#             order.razorpay_order_id = razorpay_order['id']
#             order.save()
            
#             context = {
#                 'order': order,
#                 'razorpay_order_id': razorpay_order['id'],
#                 'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#                 'amount': amount_paise,
#                 'currency': 'INR',
#                 'user_name': request.user.get_full_name() or request.user.email,
#                 'user_email': request.user.email,
#             }
            
#             return render(request, 'payment/razorpay_payment.html', context)
            
#         except Exception as e:
#             messages.error(request, f"Error creating payment: {str(e)}")
#             return redirect('order_detail', order_id=order.id)
    
#     return redirect('order_detail', order_id=order.id)