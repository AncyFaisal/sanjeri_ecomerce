# sales_report_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta, datetime
import json
from decimal import Decimal
import csv
import xlwt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

from ..models import Order, OrderItem, Coupon, ProductVariant

def is_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def sales_report(request):
    """Main sales report view"""
    
    # Get filter parameters
    report_type = request.GET.get('report_type', 'daily')
    custom_start = request.GET.get('custom_start')
    custom_end = request.GET.get('custom_end')
    
    # Export format if specified
    export_format = request.GET.get('export')
    
    # Set date range based on report type
    today = timezone.now().date()
    
    if report_type == 'daily':
        start_date = today
        end_date = today
        date_label = f"Daily Report - {today.strftime('%d %b %Y')}"
    elif report_type == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        date_label = f"Weekly Report - {start_date.strftime('%d %b')} to {end_date.strftime('%d %b %Y')}"
    elif report_type == 'monthly':
        start_date = today.replace(day=1)
        # Calculate last day of month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
        date_label = f"Monthly Report - {start_date.strftime('%B %Y')}"
    elif report_type == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        date_label = f"Yearly Report - {start_date.year}"
    elif report_type == 'custom' and custom_start and custom_end:
        try:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
            date_label = f"Custom Report - {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
        except ValueError:
            # If date parsing fails, default to today
            start_date = today
            end_date = today
            date_label = f"Daily Report - {today.strftime('%d %b %Y')}"
    else:
        # Default to today
        start_date = today
        end_date = today
        date_label = f"Daily Report - {today.strftime('%d %b %Y')}"
    
    # Filter orders (only completed/delivered orders)
    orders = Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered', 'out_for_delivery']
    ).order_by('-created_at')
    
    # Calculate totals
    total_sales_count = orders.count()
    total_order_amount = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_discount = orders.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0')
    total_coupon_discount = orders.aggregate(total=Sum('coupon_discount'))['total'] or Decimal('0')
    total_tax = orders.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
    total_shipping = orders.aggregate(total=Sum('shipping_charge'))['total'] or Decimal('0')
    
    # Net revenue (after discounts)
    net_revenue = total_order_amount - total_discount - total_coupon_discount
    
    # Calculate average order value
    if total_sales_count > 0:
        avg_order_value = total_order_amount / total_sales_count
    else:
        avg_order_value = Decimal('0')
    
    # Get top selling products
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'variant__product__name',
        'variant__volume_ml',
        'variant__gender'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:10]
    
    # Get coupon usage statistics
    coupon_stats = orders.filter(coupon__isnull=False).values(
        'coupon__code'
    ).annotate(
        usage_count=Count('id'),
        total_discount=Sum('coupon_discount')
    ).order_by('-usage_count')[:10]
    
    # Get daily sales for chart (last 7 days)
    last_7_days = []
    daily_sales_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_orders = Order.objects.filter(
            created_at__date=date,
            status__in=['confirmed', 'shipped', 'delivered', 'out_for_delivery']
        )
        daily_total = daily_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        last_7_days.append(date.strftime('%b %d'))
        daily_sales_data.append(float(daily_total))
    
    # Payment method breakdown
    payment_methods = orders.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Handle export if requested
    if export_format in ['csv', 'excel', 'pdf']:
        return export_report(request, {
            'orders': orders,
            'start_date': start_date,
            'end_date': end_date,
            'date_label': date_label,
            'total_sales_count': total_sales_count,
            'total_order_amount': total_order_amount,
            'total_discount': total_discount,
            'total_coupon_discount': total_coupon_discount,
            'total_tax': total_tax,
            'total_shipping': total_shipping,
            'net_revenue': net_revenue,
            'avg_order_value': avg_order_value,
            'top_products': list(top_products),
            'coupon_stats': list(coupon_stats),
            'payment_methods': list(payment_methods),
        }, export_format)
    
    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'custom_start': custom_start or '',
        'custom_end': custom_end or '',
        'date_label': date_label,
        'today': today,
        
        # Summary stats
        'total_sales_count': total_sales_count,
        'total_order_amount': total_order_amount,
        'total_discount': total_discount,
        'total_coupon_discount': total_coupon_discount,
        'total_tax': total_tax,
        'total_shipping': total_shipping,
        'net_revenue': net_revenue,
        'avg_order_value': avg_order_value,
        
        # Detailed data
        'top_products': top_products,
        'coupon_stats': coupon_stats,
        'payment_methods': payment_methods,
        
        # Chart data
        'last_7_days': json.dumps(last_7_days),
        'daily_sales_data': json.dumps(daily_sales_data),
        
        # For template
        'orders': orders[:50],  # Recent 50 orders
    }
    
    return render(request, 'admin/sales_report/report.html', context)

def export_report(request, data, export_format):
    """Export report in various formats"""
    
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{data["start_date"]}_to_{data["end_date"]}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([data['date_label']])
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Sales Count', data['total_sales_count']])
        writer.writerow(['Total Order Amount', f"₹{data['total_order_amount']}"])
        writer.writerow(['Total Discount', f"₹{data['total_discount']}"])
        writer.writerow(['Total Coupon Discount', f"₹{data['total_coupon_discount']}"])
        writer.writerow(['Total Tax', f"₹{data['total_tax']}"])
        writer.writerow(['Total Shipping', f"₹{data['total_shipping']}"])
        writer.writerow(['Net Revenue', f"₹{data['net_revenue']}"])
        writer.writerow(['Average Order Value', f"₹{data['avg_order_value']:.2f}"])
        writer.writerow([])
        writer.writerow([])
        
        # Write order details
        writer.writerow(['ORDER DETAILS'])
        writer.writerow(['Order ID', 'Date', 'Customer', 'Amount', 'Discount', 'Coupon', 'Status', 'Payment'])
        
        for order in data['orders']:
            writer.writerow([
                order.id,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.user.email if order.user else 'Guest',
                f"₹{order.total_amount}",
                f"₹{order.discount_amount}",
                order.coupon.code if order.coupon else '-',
                order.get_status_display(),
                order.get_payment_method_display()
            ])
        
        return response
    
    elif export_format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{data["start_date"]}_to_{data["end_date"]}.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Sales Report')
        
        row_num = 0
        
        # Title
        title_style = xlwt.easyxf('font: bold 1, height 280; align: horiz center')
        ws.write_merge(row_num, row_num, 0, 7, data['date_label'], title_style)
        row_num += 2
        
        # Summary header
        header_style = xlwt.easyxf('font: bold 1; pattern: pattern solid, fore_colour light_green;')
        ws.write(row_num, 0, 'SUMMARY', header_style)
        ws.write(row_num, 1, '', header_style)
        row_num += 1
        
        # Summary data
        summary_data = [
            ['Total Sales Count', data['total_sales_count']],
            ['Total Order Amount', f"₹{data['total_order_amount']}"],
            ['Total Discount', f"₹{data['total_discount']}"],
            ['Total Coupon Discount', f"₹{data['total_coupon_discount']}"],
            ['Total Tax', f"₹{data['total_tax']}"],
            ['Total Shipping', f"₹{data['total_shipping']}"],
            ['Net Revenue', f"₹{data['net_revenue']}"],
            ['Average Order Value', f"₹{data['avg_order_value']:.2f}"],
        ]
        
        for row in summary_data:
            ws.write(row_num, 0, row[0])
            ws.write(row_num, 1, row[1])
            row_num += 1
        
        row_num += 1
        
        # Orders header
        order_header = ['Order ID', 'Date', 'Customer', 'Amount', 'Discount', 'Coupon', 'Status', 'Payment']
        for col_num, header in enumerate(order_header):
            ws.write(row_num, col_num, header, header_style)
        row_num += 1
        
        # Orders data
        for order in data['orders']:
            ws.write(row_num, 0, order.id)
            ws.write(row_num, 1, order.created_at.strftime('%Y-%m-%d %H:%M'))
            ws.write(row_num, 2, order.user.email if order.user else 'Guest')
            ws.write(row_num, 3, float(order.total_amount))
            ws.write(row_num, 4, float(order.discount_amount))
            ws.write(row_num, 5, order.coupon.code if order.coupon else '-')
            ws.write(row_num, 6, order.get_status_display())
            ws.write(row_num, 7, order.get_payment_method_display())
            row_num += 1
        
        wb.save(response)
        return response
    
    elif export_format == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{data["start_date"]}_to_{data["end_date"]}.pdf"'
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        
        # Add title
        elements.append(Paragraph(data['date_label'], styles['Title']))
        elements.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Add summary
        elements.append(Paragraph("SUMMARY", styles['Heading2']))
        
        summary_data = [
            ['Total Sales Count', str(data['total_sales_count'])],
            ['Total Order Amount', f"₹{data['total_order_amount']}"],
            ['Total Discount', f"₹{data['total_discount']}"],
            ['Total Coupon Discount', f"₹{data['total_coupon_discount']}"],
            ['Net Revenue', f"₹{data['net_revenue']}"],
            ['Average Order Value', f"₹{data['avg_order_value']:.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Add recent orders
        elements.append(Paragraph("RECENT ORDERS", styles['Heading2']))
        
        order_data = [['Order ID', 'Date', 'Customer', 'Amount', 'Status']]
        for order in list(data['orders'])[:20]:  # Limit to 20 in PDF
            customer_email = order.user.email if order.user else 'Guest'
            if len(customer_email) > 20:
                customer_email = customer_email[:20] + '...'
            
            order_data.append([
                str(order.id),
                order.created_at.strftime('%Y-%m-%d'),
                customer_email,
                f"₹{order.total_amount}",
                order.get_status_display()
            ])
        
        order_table = Table(order_data, colWidths=[60, 80, 150, 70, 80])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(order_table)
        
        # Build PDF
        doc.build(elements)
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    # If export format is not recognized, redirect back to report
    from django.shortcuts import redirect
    return redirect('sales_report')

# Keep the existing export_sales_report function for backward compatibility
@login_required
@user_passes_test(is_admin)
def export_sales_report(request):
    """Legacy export function - redirects to new system"""
    # Get parameters from request
    report_type = request.GET.get('report_type', 'daily')
    custom_start = request.GET.get('custom_start')
    custom_end = request.GET.get('custom_end')
    export_format = request.GET.get('format', 'csv')
    
    # Build redirect URL
    redirect_url = f"{reverse('sales_report')}?report_type={report_type}"
    if custom_start:
        redirect_url += f"&custom_start={custom_start}"
    if custom_end:
        redirect_url += f"&custom_end={custom_end}"
    redirect_url += f"&export={export_format}"
    
    return redirect(redirect_url)