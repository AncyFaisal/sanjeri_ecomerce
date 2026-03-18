# sanjeri_app/views/admin_wallet_views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from ..models import WalletTransaction, CustomUser
from ..services.wallet_service import WalletService
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@staff_member_required
def admin_pending_refunds(request):
    """View all pending refund requests"""
    pending_refunds = WalletTransaction.objects.filter(
        transaction_type='REFUND',
        status='PENDING'
    ).select_related('wallet__user', 'order').order_by('-created_at')
    
    # Get page size from request (default to 10)
    page_size = request.GET.get('page_size', 10)
    try:
        page_size = int(page_size)
    except ValueError:
        page_size = 10
    
    # Paginate the results
    paginator = Paginator(pending_refunds, page_size)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

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
        'page_obj': page_obj,  
        'paginator': paginator,
        'total_pending_amount': total_pending_amount,
        'total_approved': approved_today,
        'title': 'Pending Refunds - Admin'
    }
    
    return render(request, 'admin/wallet/pending_refunds.html', context)


@staff_member_required
def admin_wallet_transactions(request):
    """
    Display all wallet transactions with basic details:
    - Transaction ID
    - Transaction Date
    - User
    - Transaction Type
    - Amount
    """
    # Get all transactions with related user data
    transactions = WalletTransaction.objects.select_related(
        'wallet__user', 'order'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(id__icontains=search_query) |
            Q(wallet__user__email__icontains=search_query) |
            Q(wallet__user__username__icontains=search_query) |
            Q(wallet__user__first_name__icontains=search_query) |
            Q(wallet__user__last_name__icontains=search_query) |
            Q(order__order_number__icontains=search_query) |
            Q(transaction_type__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    # Filter by transaction type
    transaction_type = request.GET.get('type', '')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        transactions = transactions.filter(status=status)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary statistics
    total_transactions = transactions.count()
    total_amount = transactions.aggregate(total=Sum('amount'))['total'] or 0
    completed_count = transactions.filter(status='COMPLETED').count()
    pending_count = transactions.filter(status='PENDING').count()
    
    context = {
        'transactions': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_type': transaction_type,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'total_transactions': total_transactions,
        'total_amount': total_amount,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'transaction_types': WalletTransaction.TRANSACTION_TYPES,
        'status_choices': WalletTransaction.STATUS_CHOICES,
        'title': 'Wallet Transactions - Admin'
    }
    
    return render(request, 'admin/wallet/transactions.html', context)


@staff_member_required
def admin_wallet_transaction_detail(request, transaction_id):
    """
    Detailed view for each transaction with:
    - User Details
    - Transaction ID
    - Transaction Date
    - Transaction Type
    - Source of Transaction
    - If due to returned/cancelled product, button to order detail page
    """
    transaction = get_object_or_404(
        WalletTransaction.objects.select_related(
            'wallet__user', 'order', 'approved_by'
        ),
        id=transaction_id
    )
    
    # Get user details
    user = transaction.wallet.user
    
    # Check if transaction is related to an order (cancelled/returned)
    is_order_related = transaction.order is not None
    
    context = {
        'transaction': transaction,
        'user': user,
        'is_order_related': is_order_related,
        'title': f'Transaction #{transaction.id} - Admin'
    }
    
    return render(request, 'admin/wallet/transaction_detail.html', context)


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


@staff_member_required
def admin_user_wallet(request, user_id):
    """View specific user's wallet and transactions"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    try:
        wallet = user.wallet
        transactions = wallet.transactions.all().order_by('-created_at')
    except:
        wallet = None
        transactions = []
    
    # Pagination for transactions
    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary
    total_deposits = transactions.filter(
        transaction_type__in=['DEPOSIT', 'REFUND'],
        status='COMPLETED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdrawals = transactions.filter(
        transaction_type='WITHDRAWAL',
        status='COMPLETED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'wallet_user': user,
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'current_balance': wallet.balance if wallet else 0,
        'title': f'Wallet - {user.get_full_name()}'
    }
    
    return render(request, 'admin/wallet/user_wallet.html', context)