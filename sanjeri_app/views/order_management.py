# views/order_management.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.template.loader import render_to_string
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from decimal import Decimal
from django.utils import timezone
from ..models import Order, OrderItem
from ..models import Wallet, WalletTransaction

@login_required
def order_list(request):
    """Order listing page with search and filters"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(shipping_address__full_name__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Get user's wallet balance for the template
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    context = {
        'orders': orders,
        'search_query': search_query,
        'status_filter': status_filter,
        'wallet_balance': wallet.balance,
        'title': 'My Orders - Sanjeri'
    }
    return render(request, 'orders/order_list.html', context)
@login_required
@require_POST
def cancel_order_item(request, item_id):
    """Cancel specific order item - only refund if payment was made"""
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if order_item.is_cancelled:
        messages.warning(request, "This item is already cancelled.")
        return redirect('order_detail', order_id=order_item.order.id)
    
    reason = request.POST.get('reason', '').strip()
    
    # Get or create user's wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Calculate refund amount for this item
    refund_amount = order_item.total_price
    
    # Get the order for payment status check
    order = order_item.order
    
    # Check if user paid for this order
    user_paid = order.payment_status in ['completed', 'partially_paid']
    print(f"Order #{order.order_number} payment status: {order.payment_status}")
    print(f"User paid: {user_paid}")
    print(f"Refund amount: ₹{refund_amount}")
    
    if order_item.cancel_item(reason):
        if user_paid and refund_amount > 0:
            try:
                # Create wallet transaction
                transaction = WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type='REFUND',
                    status='COMPLETED',
                    reason=f"Refund for cancelled item: {order_item.product_name} (Order #{order.order_number})",
                    order=order
                )
                
                print(f"Created refund transaction: {transaction.id}")
                
                # Manually update wallet balance
                wallet.refresh_from_db()
                wallet.balance += Decimal(refund_amount)
                wallet.save(update_fields=['balance'])
                
                # Update user's wallet_balance field
                user = request.user
                if hasattr(user, 'wallet_balance'):
                    user.wallet_balance = wallet.balance
                    user.save(update_fields=['wallet_balance'])
                
                messages.success(request, f"{order_item.product_name} has been cancelled. ₹{refund_amount} refunded to your wallet.")
                
            except Exception as e:
                print(f"❌ Error in wallet refund: {e}")
                messages.error(request, f"Item cancelled but refund failed: {str(e)}")
                return redirect('order_detail', order_id=order_item.order.id)
        else:
            # No refund needed - payment was pending or free
            messages.success(request, f"{order_item.product_name} has been cancelled. No refund needed.")
        
        # Check if all items in order are cancelled
        remaining_items = order.items.filter(is_cancelled=False)
        if not remaining_items.exists():
            order.status = 'cancelled'
            order.cancellation_reason = "All items cancelled individually"
            
            # Update payment status based on whether it was paid
            if user_paid:
                order.payment_status = 'refunded'
            else:
                order.payment_status = 'cancelled'
            
            order.save()
            
            messages.info(request, "All items in the order have been cancelled. Order marked as cancelled.")
    
    return redirect('order_detail', order_id=order_item.order.id)



@login_required
def return_order(request, order_id):
    """Request return for an order - requires admin approval"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, "Please provide a reason for return.")
            return redirect('order_detail', order_id=order_id)
        
        if order.request_return(reason):        
            messages.success(request, "Return request submitted successfully. Please wait for admin approval. Refund will be processed to your wallet after approval.")
        else:
            messages.error(request, "Cannot return this order. It may be outside the return period.")
        
        return redirect('order_detail', order_id=order_id)
    
    context = {
        'order': order,
    }
    return render(request, 'orders/return_request.html', context)

@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancel entire order - only refund if payment was made"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get reason if provided (from form), but since we removed the form,
    # reason will always be empty - that's fine
    reason = request.POST.get('reason', '').strip()

    # Get or create user's wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Check if order was paid
    user_paid = order.payment_status in ['completed', 'success', 'partially_paid']
    
    if order.cancel_order(reason):
        # Only show refund message if user actually paid
        if user_paid:
            messages.success(request, f"Order cancelled successfully. ₹{order.refund_amount} refunded to your wallet.")
        else:
            messages.success(request, "Order cancelled successfully. No refund needed (payment was pending).")
    else:
        messages.error(request, "Cannot cancel this order. It may have already been shipped.")
    
    return redirect('order_detail', order_id=order_id)

@login_required
def wallet_balance(request):
    """View wallet balance and transaction history"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Get transaction history
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'title': 'My Wallet - Sanjeri'
    }
    return render(request, 'orders/wallet.html', context)

@login_required
def process_return_refund(request, order_id):
    """Admin view to process return refund to wallet"""
    # Check if user is admin or staff
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('order_detail', order_id=order_id)
    
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        # Approve return and process wallet refund
        if order.status == 'return_requested':
            # Find pending refund transaction
            transaction = WalletTransaction.objects.filter(
                order=order,
                transaction_type='REFUND',
                status='PENDING'
            ).first()
            
            if transaction:
                # Approve the refund
                if transaction.mark_as_completed(approved_by=request.user):
                    # Update order status
                    order.status = 'returned'
                    order.refund_amount = transaction.amount
                    order.refunded_at = timezone.now()
                    order.save()
                    
                    # Also update user's wallet_balance
                    user = order.user
                    user.wallet_balance += Decimal(transaction.amount)
                    user.save()
                    
                    messages.success(request, f"Return approved. ₹{transaction.amount} refunded to customer's wallet.")
                else:
                    messages.error(request, "Failed to process refund.")
            else:
                messages.error(request, "No pending refund transaction found.")
            
            return redirect('admin:orders_order_change', object_id=order_id)
    
    context = {
        'order': order,
    }
    return render(request, 'orders/admin/process_return.html', context)

@login_required
def use_wallet_payment(request):
    """Apply wallet balance to cart/order during checkout"""
    if request.method == 'POST':
        # Get user's cart (assuming you have a Cart model)
        cart = getattr(request.user, 'cart', None)
        
        if not cart or (hasattr(cart, 'items') and cart.items.count() == 0):
            return JsonResponse({'success': False, 'message': 'Cart is empty'})
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Calculate cart total (adjust based on your cart structure)
        cart_total = Decimal('0.00')
        if hasattr(cart, 'get_total_price'):
            cart_total = cart.subtotal
        
        # Check if user wants to use wallet
        use_wallet = request.POST.get('use_wallet', 'false') == 'true'
        
        if use_wallet and wallet.balance > 0:
            # Determine how much to use from wallet
            wallet_to_use = min(wallet.balance, cart_total)
            
            # Store in session for checkout
            request.session['wallet_amount_used'] = float(wallet_to_use)
            request.session['remaining_amount'] = float(cart_total - Decimal(wallet_to_use))
            
            return JsonResponse({
                'success': True,
                'wallet_used': float(wallet_to_use),
                'remaining_amount': float(cart_total - Decimal(wallet_to_use)),
                'wallet_balance': float(wallet.balance - Decimal(wallet_to_use))
            })
        
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def download_invoice(request, order_id):
    """Generate and download PDF invoice using ReportLab"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if wallet was used for this order
    wallet_payment = WalletTransaction.objects.filter(
        order=order,
        transaction_type='WITHDRAWAL'
    ).first()
    
    # Check if refund was made to wallet
    wallet_refund = WalletTransaction.objects.filter(
        order=order,
        transaction_type='REFUND',
        status='COMPLETED'
    ).first()
    
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Add title
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center alignment
    title = Paragraph("SANJERI PERFUMES", title_style)
    elements.append(title)
    
    elements.append(Spacer(1, 12))
    
    # Add invoice title
    invoice_title = Paragraph(f"INVOICE - #{order.order_number}", styles['Heading2'])
    elements.append(invoice_title)
    elements.append(Spacer(1, 12))
    
    # Order details
    order_details = [
        [f"Order Date: {order.created_at.strftime('%B %d, %Y')}", f"Status: {order.get_status_display()}"],
        [f"Payment Method: {order.get_payment_method_display()}", f"Payment Status: {order.get_payment_status_display()}"],
    ]
    
    order_table = Table(order_details, colWidths=[250, 250])
    order_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(order_table)
    elements.append(Spacer(1, 20))
    
    # Billing information
    billing_info = [
        ['BILL TO:', 'SHIP TO:'],
        [order.shipping_address.full_name, order.shipping_address.full_name],
        [order.shipping_address.phone, order.shipping_address.phone],
        [order.shipping_address.address_line1, order.shipping_address.address_line1],
        [order.shipping_address.city, order.shipping_address.city],
        [f"{order.shipping_address.state} - {order.shipping_address.postal_code}", 
         f"{order.shipping_address.state} - {order.shipping_address.postal_code}"],
    ]
    
    billing_table = Table(billing_info, colWidths=[250, 250])
    billing_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    elements.append(billing_table)
    elements.append(Spacer(1, 20))
    
    # Order items header
    items_header = [['Product', 'Variant', 'Quantity', 'Unit Price', 'Total']]
    
    # Order items data
    items_data = []
    for item in order.items.all():
        items_data.append([
            item.product_name,
            item.variant_details,
            str(item.quantity),
            f"Rs.{item.unit_price}",  # Changed from ₹ to Rs.
            f"Rs.{item.total_price}"   # Changed from ₹ to Rs.
        ])
    
    # Combine header and data
    items_table_data = items_header + items_data
    
    items_table = Table(items_table_data, colWidths=[180, 120, 60, 80, 80])
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # Order summary
    summary_data = [
        ['Subtotal:', f"Rs.{order.subtotal}"],  # Changed from ₹ to Rs.
        ['Shipping:', f"Rs.{order.shipping_charge}" if order.shipping_charge > 0 else 'FREE'],
        ['Tax (18%):', f"Rs.{order.tax_amount:.2f}"],  # Changed from ₹ to Rs.
    ]
    
    if order.discount_amount > 0:
        summary_data.append(['Discount:', f"-Rs.{order.discount_amount}"])  # Changed from ₹ to Rs.
    
    # Add wallet payment if used
    if hasattr(order, 'wallet_amount_used') and order.wallet_amount_used > 0:
        summary_data.append(['Wallet Payment:', f"-Rs.{order.wallet_amount_used:.2f}"])  # Changed from ₹ to Rs.
    
    summary_data.append(['TOTAL:', f"Rs.{order.total_amount:.2f}"])  # Changed from ₹ to Rs.
    
    summary_table = Table(summary_data, colWidths=[400, 120])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Add refund information if applicable
    if order.status in ['cancelled', 'returned'] and wallet_refund:
        refund_info = Paragraph(
            f"<b>REFUND INFORMATION:</b><br/>"
            f"Refund Amount: Rs.{wallet_refund.amount}<br/>"  # Changed from ₹ to Rs.
            f"Refund Method: Wallet<br/>"
            f"Refund Date: {wallet_refund.created_at.strftime('%B %d, %Y')}<br/>"
            f"Status: Refunded to customer's wallet",
            styles['Normal']
        )
        elements.append(refund_info)
        elements.append(Spacer(1, 20))
    
    # Footer
    footer = Paragraph(
        "Thank you for your business!<br/>"
        "Sanjeri Perfumes - A Scent Beyond the Soul<br/>"
        "For any queries, please contact our customer support",
        styles['Normal']
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # File response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_number}.pdf"'
    
    return response

@login_required
def order_detail(request, order_id):
    """Order detail page with wallet information"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get wallet transactions related to this order
    wallet_transactions = WalletTransaction.objects.filter(order=order)
    
    # Check if wallet was used for payment
    wallet_payment = wallet_transactions.filter(transaction_type='WITHDRAWAL').first()
    
    # Check if refund was made to wallet
    wallet_refund = wallet_transactions.filter(transaction_type='REFUND', status='COMPLETED').first()
    
    additional_discount = order.discount_amount - order.coupon_discount

    context = {
        'order': order,
        'order_items': order.items.all(),
        'wallet_payment': wallet_payment,
        'wallet_refund': wallet_refund,
        'additional_discount': additional_discount,
        'title': f'Order #{order.order_number} - Sanjeri'
    }
    return render(request, 'orders/order_detail.html', context)





@login_required
@require_POST
def request_return(request, order_id):
    """Request return for an order - requires admin approval"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    return_reason = request.POST.get('return_reason', '').strip()
    
    if not return_reason:
        messages.error(request, "Please provide a reason for return.")
        return redirect('order_detail', order_id=order_id)
    
    if order.request_return(return_reason):
        messages.success(request, "Return request submitted. Refund will be processed after admin approval.")
    else:
        messages.error(request, "Cannot return this order.")
    
    return redirect('order_detail', order_id=order_id)

# Add this function to your views/order_management.py
@login_required
def refund_status(request, order_id):
    """View refund status for an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get refund transaction for this order
    transaction = WalletTransaction.objects.filter(
        order=order,
        transaction_type='REFUND'
    ).order_by('-created_at').first()
    
    if not transaction:
        messages.error(request, "No refund transaction found for this order.")
        return redirect('order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'transaction': transaction,
        'title': f'Refund Status - Order #{order.order_number}'
    }
    
    return render(request, 'orders/refund_status.html', context)


@login_required
def check_refund_status(request, order_id):
    """Check refund status (AJAX)"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get latest refund transaction
    transaction = WalletTransaction.objects.filter(
        order=order,
        transaction_type='REFUND'
    ).order_by('-created_at').first()
    
    if transaction:
        return JsonResponse({
            'success': True,
            'status': transaction.status,
            'status_display': transaction.get_status_display(),
            'amount': float(transaction.amount),
            'created_at': transaction.created_at.strftime("%d %b %Y, %H:%M"),
            'reason': transaction.reason,
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'No refund transaction found'
        })



@login_required
def request_item_return(request, item_id):
    """Request return for individual item"""
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('return_reason', '').strip()
        
        if not reason:
            messages.error(request, "Please provide a reason for return.")
            return redirect('order_detail', order_id=order_item.order.id)
        
        success, message = order_item.request_item_return(reason)
        
        if success:
            messages.success(request, "Return request submitted for this item. Awaiting admin approval.")
        else:
            messages.error(request, message)
        
        return redirect('order_detail', order_id=order_item.order.id)
    
    context = {
        'item': order_item,
        'order': order_item.order,
    }
    return render(request, 'orders/request_item_return.html', context)