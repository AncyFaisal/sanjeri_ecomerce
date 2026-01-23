from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from ..models.wallet import Wallet, WalletTransaction
from decimal import Decimal
import razorpay
from django.conf import settings
from django.http import JsonResponse
import json
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt


# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def wallet_dashboard(request):
    """User wallet dashboard"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Get recent transactions
    recent_transactions = wallet.transactions.all().order_by('-created_at')[:20]
    
    context = {
        'wallet': wallet,
        'transactions': recent_transactions,
        'user_wallet_balance': request.user.wallet_balance,  # From CustomUser model
        'title': 'My Wallet - Sanjeri'
    }
    
    return render(request, 'wallet/dashboard.html', context)

@login_required
def add_wallet_balance(request):
    """Add balance to wallet via Razorpay"""
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            amount = Decimal(amount)
            if amount < 10:  # Minimum ₹10
                messages.error(request, "Minimum amount is ₹10")
                return redirect('wallet_dashboard')
            
            if amount > 10000:  # Maximum ₹10,000 per transaction
                messages.error(request, "Maximum amount is ₹10,000")
                return redirect('wallet_dashboard')
            
            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            amount_in_paise = int(amount * 100)
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1',
                'receipt': f'WALLET_{request.user.id}_{int(timezone.now().timestamp())}'
            })
            
            # Create pending wallet transaction
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='DEPOSIT',
                status='PENDING',
                reason=f"Wallet top-up",
                razorpay_order_id=razorpay_order['id']
            )
            
            return JsonResponse({
                'success': True,
                'order_id': razorpay_order['id'],
                'amount': amount_in_paise,
                'key': settings.RAZORPAY_KEY_ID,
                'transaction_id': transaction.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@csrf_exempt
@login_required
def verify_wallet_payment(request):
    """Verify Razorpay payment for wallet top-up"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')
            transaction_id = data.get('transaction_id')
            
            # Verify signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id
            }
            
            client.utility.verify_payment_signature(params_dict, razorpay_signature)
            
            # Get the pending transaction
            from ..models.wallet import WalletTransaction
            transaction = WalletTransaction.objects.get(
                id=transaction_id,
                wallet=request.user.wallet,
                status='PENDING',
                razorpay_order_id=razorpay_order_id
            )
            
            # Mark transaction as completed
            transaction.status = 'COMPLETED'
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.save()
            
            # Add money to wallet
            request.user.wallet.deposit(
                amount=transaction.amount,
                reason=f"Wallet top-up completed - Payment ID: {razorpay_payment_id}",
                order=None
            )
            
            return JsonResponse({
                'success': True,
                'message': f'₹{transaction.amount} added to your wallet successfully!',
                'new_balance': str(request.user.wallet.balance)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Payment verification failed: {str(e)}'
            })
        
@login_required
def wallet_transactions(request):
    """View all wallet transactions with pagination"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Get all transactions
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)  # 20 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transactions': page_obj.object_list,
        'wallet': wallet,
        'title': 'Wallet Transactions - Sanjeri'
    }
    
    return render(request, 'wallet/transactions.html', context)