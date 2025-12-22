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
from ..models import Order, OrderItem

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
    
    context = {
        'orders': orders,
        'search_query': search_query,
        'status_filter': status_filter,
        'title': 'My Orders - Sanjeri'
    }
    return render(request, 'orders/order_list.html', context)

@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancel entire order with optional reason"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not order.can_be_cancelled:
        messages.error(request, "This order cannot be cancelled.")
        return redirect('order_list')
    
    reason = request.POST.get('reason', '').strip()
    
    if order.cancel_order(reason):
        messages.success(request, f"Order #{order.order_number} has been cancelled successfully.")
        
        # If all items are cancelled, refund payment (for online payments)
        if order.payment_method == 'online' and order.payment_status == 'completed':
            # Add refund logic here
            order.payment_status = 'refunded'
            order.save()
    else:
        messages.error(request, "Failed to cancel order.")
    
    return redirect('order_list')

@login_required
@require_POST
def cancel_order_item(request, item_id):
    """Cancel specific order item"""
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if order_item.is_cancelled:
        messages.warning(request, "This item is already cancelled.")
        return redirect('order_detail', order_id=order_item.order.id)
    
    reason = request.POST.get('reason', '').strip()
    
    if order_item.cancel_item(reason):
        messages.success(request, f"{order_item.product_name} has been cancelled.")
        
        # Check if all items in order are cancelled
        order = order_item.order
        remaining_items = order.items.filter(is_cancelled=False)
        if not remaining_items.exists():
            order.status = 'cancelled'
            order.cancellation_reason = "All items cancelled individually"
            order.save()
            messages.info(request, "All items in the order have been cancelled. Order marked as cancelled.")
    
    return redirect('order_detail', order_id=order_item.order.id)

@login_required
@require_POST
def return_order(request, order_id):
    """Return delivered order with mandatory reason"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not order.can_be_returned:
        messages.error(request, "This order cannot be returned.")
        return redirect('order_list')
    
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, "Please provide a reason for return.")
        return redirect('order_detail', order_id=order_id)
    
    if order.return_order(reason):
        messages.success(request, f"Order #{order.order_number} return request submitted successfully.")
        
        # Refund logic for paid orders
        if order.payment_status == 'completed':
            order.payment_status = 'refunded'
            order.save()
    else:
        messages.error(request, "Failed to process return request.")
    
    return redirect('order_list')

@login_required
def download_invoice(request, order_id):
    """Generate and download PDF invoice using ReportLab"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
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
            f"₹{item.unit_price}",
            f"₹{item.total_price}"
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
        ['Subtotal:', f"₹{order.subtotal}"],
        ['Shipping:', f"₹{order.shipping_charge}" if order.shipping_charge > 0 else 'FREE'],
        ['Tax (18%):', f"₹{order.tax_amount:.2f}"],
    ]
    
    if order.discount_amount > 0:
        summary_data.append(['Discount:', f"-₹{order.discount_amount}"])
    
    summary_data.append(['TOTAL:', f"₹{order.total_amount:.2f}"])
    
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
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'title': f'Order #{order.order_number} - Sanjeri'
    }
    return render(request, 'orders/order_detail.html', context)