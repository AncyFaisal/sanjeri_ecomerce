# sanjeri_app/views/admin_wallet_views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from ..models import WalletTransaction
from ..services.wallet_service import WalletService

@staff_member_required
def admin_pending_refunds(request):
    """View all pending refund requests"""
    pending_refunds = WalletTransaction.objects.filter(
        transaction_type='REFUND',
        status='PENDING'
    ).select_related('wallet__user', 'order').order_by('-created_at')
    
    total_pending_amount = pending_refunds.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    today = timezone.now().date()
    approved_today = WalletTransaction.objects.filter(
        transaction_type='REFUND',
        status='COMPLETED',
        updated_at__date=today
    ).count()
    
    context = {
        'pending_refunds': pending_refunds,
        'total_pending_amount': total_pending_amount,
        'total_approved': approved_today,
        'title': 'Pending Refunds - Admin'
    }
    
    return render(request, 'admin/wallet/pending_refunds.html', context)


@staff_member_required
def admin_approve_refund(request, refund_id):
    """Approve pending refund"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    
    try:
        transaction = get_object_or_404(
            WalletTransaction,
            id=refund_id,
            transaction_type='REFUND',
            status='PENDING'
        )
        
        success, message = WalletService.approve_return_refund(
            transaction,
            approved_by=request.user
        )
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'success': False, 'message': message})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@staff_member_required
def admin_reject_refund(request, refund_id):
    """Reject pending refund"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    
    try:
        transaction = get_object_or_404(
            WalletTransaction,
            id=refund_id,
            transaction_type='REFUND',
            status='PENDING'
        )
        
        rejection_reason = request.POST.get('rejection_reason', '')
        
        success, message = WalletService.reject_return_refund(
            transaction,
            rejection_reason
        )
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'success': False, 'message': message})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})