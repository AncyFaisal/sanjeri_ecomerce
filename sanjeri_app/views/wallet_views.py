# sanjeri_app/views/wallet_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import json
import traceback
from django.conf import settings

from ..models.wallet import Wallet, WalletTransaction
from ..services.razorpay_service import RazorpayService
from ..services.wallet_service import WalletService

# Initialize services
razorpay_service = RazorpayService()

@login_required
def wallet_dashboard(request):
    """User wallet dashboard"""
    wallet = WalletService.get_or_create_wallet(request.user)
    # Get all transactions but filter for COMPLETED only
    all_transactions = WalletService.get_user_transactions(request.user, limit=20)
    transactions = [t for t in all_transactions if t.status == 'COMPLETED'][:10]
    
    context = {
        'wallet': wallet,
        'recent_transactions': transactions,
        'title': 'My Wallet - Sanjeri'
    }
    
    return render(request, 'wallet/wallet_dashboard.html', context)


@login_required
def add_wallet_balance(request):
    """Add money to wallet via Razorpay"""
    wallet = WalletService.get_or_create_wallet(request.user)
    
    if request.method == "GET":
        context = {
            'wallet': wallet,
            'title': 'Add Money to Wallet - Sanjeri'
        }
        return render(request, 'wallet/add_balance.html', context)
    
    elif request.method == "POST":
        try:
            amount_str = request.POST.get("amount")
            
            if not amount_str:
                return JsonResponse({'success': False, 'message': 'Please enter an amount'})
            
            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                return JsonResponse({'success': False, 'message': 'Please enter a valid amount'})
            
            # Validation
            if amount < 10:
                return JsonResponse({'success': False, 'message': 'Minimum amount is ₹10'})
            
            if amount > 10000:
                return JsonResponse({'success': False, 'message': 'Maximum amount is ₹10,000'})
            
            # Create pending transaction
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='DEPOSIT',
                status='PENDING',
                reason="Wallet top-up via Razorpay"
            )
            
            # Create Razorpay order
            notes = {
                'transaction_id': str(transaction.id),
                'user_id': str(request.user.id),
                'type': 'wallet_topup'
            }
            
            result = razorpay_service.create_order(amount, notes=notes)
            
            if not result['success']:
                transaction.status = 'FAILED'
                transaction.save()
                return JsonResponse({'success': False, 'message': result['error']})
            
            # Update transaction with Razorpay order ID
            transaction.razorpay_order_id = result['order_id']
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'key': settings.RAZORPAY_KEY_ID,
                'amount': result['amount'],
                'currency': result['currency'],
                'order_id': result['order_id'],
                'transaction_id': transaction.id,
                'customer_name': request.user.get_full_name() or request.user.username,
                'customer_email': request.user.email,
                'customer_phone': getattr(request.user, 'phone', '')
            })
            
        except Exception as e:
            print(f"Error in add_wallet_balance: {e}")
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)})


@csrf_exempt
@require_POST
@login_required
def verify_wallet_payment(request):
    """Verify wallet payment after Razorpay"""
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
        
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        transaction_id = data.get('transaction_id')
        
        if not transaction_id:
            return JsonResponse({'success': False, 'message': 'Transaction ID not provided'})
        
        # Get transaction
        try:
            transaction = WalletTransaction.objects.get(
                id=transaction_id,
                wallet__user=request.user
            )
        except WalletTransaction.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transaction not found'})
        
        # Verify signature
        if not razorpay_service.verify_payment_signature(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature
        ):
            transaction.status = 'FAILED'
            transaction.save()
            return JsonResponse({'success': False, 'message': 'Invalid payment signature'})
        
        # Update transaction
        transaction.status = 'COMPLETED'
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.razorpay_signature = razorpay_signature
        transaction.save()
        
        # Update wallet balance
        wallet = transaction.wallet
        wallet.balance += transaction.amount
        wallet.save(update_fields=['balance'])
        
        # Update user's wallet_balance field
        user = request.user
        if hasattr(user, 'wallet_balance'):
            user.wallet_balance = wallet.balance
            user.save(update_fields=['wallet_balance'])
        
        return JsonResponse({
            'success': True,
            'message': f'₹{transaction.amount} added to your wallet successfully!',
            'amount': float(transaction.amount),
            'new_balance': float(wallet.balance)
        })
        
    except Exception as e:
        print(f"Error in verify_wallet_payment: {e}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def wallet_transactions(request):
    """View all wallet transactions with pagination"""
    wallet = WalletService.get_or_create_wallet(request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj,
        'title': 'Wallet Transactions - Sanjeri'
    }
    
    return render(request, 'wallet/transactions.html', context)


@login_required
def wallet_balance(request):
    """Get wallet balance (AJAX)"""
    wallet = WalletService.get_or_create_wallet(request.user)
    
    return JsonResponse({
        'success': True,
        'balance': float(wallet.balance),
        'available_balance': float(wallet.available_balance)
    })


# Test/direct add for development
@login_required
@require_POST
def direct_add_money(request):
    """Directly add money without payment (for testing only)"""
    if not settings.DEBUG:
        return JsonResponse({'success': False, 'message': 'Not available in production'})
    
    try:
        amount_str = request.POST.get('amount', '100')
        amount = Decimal(amount_str)
        
        wallet = WalletService.get_or_create_wallet(request.user)
        
        transaction = wallet.deposit(
            amount=amount,
            reason='Direct test add',
            transaction_type='DEPOSIT'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'₹{amount} added to wallet (test mode)',
            'new_balance': float(wallet.balance),
            'transaction_id': transaction.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})