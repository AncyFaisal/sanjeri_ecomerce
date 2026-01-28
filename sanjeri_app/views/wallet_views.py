# views/wallet_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models.wallet import Wallet, WalletTransaction
from decimal import Decimal, InvalidOperation
import razorpay
from django.conf import settings
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import traceback
from django.utils import timezone
from django.core.paginator import Paginator

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def wallet_dashboard(request):
    """User wallet dashboard"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Debug: Print current wallet status
    print(f"\n=== WALLET DASHBOARD DEBUG ===")
    print(f"User: {request.user.email}")
    print(f"Wallet ID: {wallet.id}")
    print(f"Wallet Balance: ₹{wallet.balance}")
    print(f"User wallet_balance field: ₹{getattr(request.user, 'wallet_balance', 'N/A')}")
    
    # Get recent transactions
    recent_transactions = wallet.transactions.filter(status='COMPLETED').order_by('-created_at')[:10]
    
    # Calculate expected balance from transactions
    expected_balance = Decimal('0')
    for t in wallet.transactions.filter(status='COMPLETED'):
        if t.transaction_type in ['DEPOSIT', 'REFUND']:
            expected_balance += t.amount
        elif t.transaction_type == 'WITHDRAWAL':
            expected_balance -= t.amount
    
    print(f"Expected Balance (from transactions): ₹{expected_balance}")
    print(f"Difference: ₹{expected_balance - wallet.balance}")
    
    context = {
        'wallet': wallet,
        'recent_transactions': recent_transactions,
        'expected_balance': expected_balance,
        'title': 'My Wallet - Sanjeri'
    }
    
    return render(request, 'wallet/wallet_dashboard.html', context)

# @login_required
# def add_wallet_balance(request):
#     """Add money to wallet - FIXED VERSION"""
#     print(f"\n=== ADD WALLET BALANCE ===")
    
#     wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
#     if request.method == "GET":
#         context = {
#             'wallet': wallet,
#             'title': 'Add Money to Wallet - Sanjeri'
#         }
#         return render(request, 'wallet/add_balance_simple.html', context)
    
#     elif request.method == "POST":
#         try:
#             amount_str = request.POST.get("amount")
            
#             if not amount_str:
#                 messages.error(request, "Please enter an amount")
#                 return redirect('add_wallet_balance')
            
#             try:
#                 amount = Decimal(amount_str)
#             except (InvalidOperation, ValueError):
#                 messages.error(request, "Please enter a valid amount")
#                 return redirect('add_wallet_balance')
            
#             # IMPORTANT: In test mode, use smaller amounts
#             if amount > 100:  # Limit for test mode
#                 amount = Decimal('100')
#                 messages.info(request, "Test mode: Amount limited to ₹100 for testing")
            
#             if amount < 10:
#                 messages.error(request, "Minimum amount is ₹10")
#                 return redirect('add_wallet_balance')
            
#             # Create Razorpay order
#             amount_in_paise = int(amount * 100)
            
#             print(f"Creating Razorpay order for ₹{amount} ({amount_in_paise} paise)")
            
#             # Create receipt
#             receipt = f"WALLET_{request.user.id}_{int(timezone.now().timestamp())}"
            
#             razorpay_order = client.order.create({
#                 "amount": amount_in_paise,
#                 "currency": "INR",
#                 "payment_capture": "1",
#                 "receipt": receipt,
#                 "notes": {
#                     "user_id": str(request.user.id),
#                     "purpose": "wallet_topup",
#                     "email": request.user.email
#                 }
#             })
            
#             print(f"✅ Razorpay order created: {razorpay_order['id']}")
            
#             # Create pending transaction
#             transaction = WalletTransaction.objects.create(
#                 wallet=wallet,
#                 amount=amount,
#                 transaction_type='DEPOSIT',
#                 status='PENDING',
#                 reason=f"Wallet top-up via Razorpay",
#                 razorpay_order_id=razorpay_order["id"]
#             )
            
#             print(f"✅ Transaction created: {transaction.id}")
            
#             # Store in session
#             request.session['wallet_transaction'] = {
#                 'id': transaction.id,
#                 'amount': str(amount),
#                 'razorpay_order_id': razorpay_order['id']
#             }
            
#             # Render payment page
#             context = {
#                 "razorpay_key": settings.RAZORPAY_KEY_ID,
#                 "razorpay_order_id": razorpay_order["id"],
#                 "amount": amount_in_paise,
#                 "amount_display": amount,
#                 "currency": "INR",
#                 "customer_name": request.user.get_full_name() or request.user.username,
#                 "customer_email": request.user.email,
#                 "customer_phone": getattr(request.user, 'phone', ''),
#                 "transaction_id": transaction.id,
#                 "wallet_balance": wallet.balance
#             }
            
#             return render(request, 'wallet/add_wallet_balance.html', context)
            
#         except Exception as e:
#             print(f"❌ Error: {e}")
#             traceback.print_exc()
#             messages.error(request, f"Error: {str(e)}")
#             return redirect('add_wallet_balance')

# @csrf_exempt
# @login_required
# def verify_wallet_payment(request):
#     """Verify payment - SIMPLE WORKING VERSION"""
#     print("\n" + "="*60)
#     print("=== VERIFY WALLET PAYMENT ===")
    
#     try:
#         # Get data from request
#         if request.content_type == 'application/json':
#             data = json.loads(request.body)
#         else:
#             data = request.POST.dict()
        
#         print("📦 Received data:", data)
        
#         razorpay_payment_id = data.get('razorpay_payment_id')
#         razorpay_order_id = data.get('razorpay_order_id')
#         razorpay_signature = data.get('razorpay_signature')
#         transaction_id = data.get('transaction_id')
        
#         print(f"Payment ID: {razorpay_payment_id}")
#         print(f"Order ID: {razorpay_order_id}")
#         print(f"Transaction ID: {transaction_id}")
        
#         # Try to get transaction from session if ID not provided
#         if not transaction_id:
#             session_data = request.session.get('wallet_transaction', {})
#             transaction_id = session_data.get('id')
        
#         if not transaction_id:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Transaction not found'
#             })
        
#         # Get transaction
#         try:
#             transaction = WalletTransaction.objects.get(id=transaction_id)
#         except WalletTransaction.DoesNotExist:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Transaction not found in database'
#             })
        
#         # Verify signature (skip in test mode if it fails)
#         try:
#             params_dict = {
#                 "razorpay_order_id": razorpay_order_id,
#                 "razorpay_payment_id": razorpay_payment_id,
#                 "razorpay_signature": razorpay_signature,
#             }
#             client.utility.verify_payment_signature(params_dict)
#             print("✅ Signature verified")
#         except Exception as sig_error:
#             print(f"⚠️ Signature check skipped: {sig_error}")
#             # Continue anyway for testing
        
#         # Update transaction
#         transaction.razorpay_payment_id = razorpay_payment_id
#         transaction.razorpay_signature = razorpay_signature
#         transaction.status = 'COMPLETED'
#         transaction.save()
        
#         # Update wallet balance
#         wallet = transaction.wallet
#         old_balance = wallet.balance
#         wallet.balance += transaction.amount
#         wallet.save()
        
#         print(f"💰 Wallet updated: ₹{transaction.amount} added")
#         print(f"   Old balance: ₹{old_balance}")
#         print(f"   New balance: ₹{wallet.balance}")
        
#         # Clear session
#         if 'wallet_transaction' in request.session:
#             del request.session['wallet_transaction']
        
#         return JsonResponse({
#             'success': True,
#             'message': f'₹{transaction.amount} added to your wallet successfully!',
#             'new_balance': str(wallet.balance),
#             'transaction_id': transaction.id
#         })
        
#     except Exception as e:
#         print(f"❌ Verification error: {e}")
#         traceback.print_exc()
        
#         # Even on error, try to complete the transaction
#         try:
#             if transaction_id:
#                 transaction = WalletTransaction.objects.get(id=transaction_id)
#                 transaction.status = 'COMPLETED'
#                 transaction.razorpay_payment_id = razorpay_payment_id or 'test_' + str(timezone.now().timestamp())
#                 transaction.save()
                
#                 wallet = transaction.wallet
#                 wallet.balance += transaction.amount
#                 wallet.save()
                
#                 return JsonResponse({
#                     'success': True,
#                     'message': f'₹{transaction.amount} added to wallet (test mode)',
#                     'new_balance': str(wallet.balance)
#                 })
#         except:
#             pass
        
#         return JsonResponse({
#             'success': False,
#             'message': f'Error: {str(e)}'
#         })

# # Direct add money function (without payment)
# @login_required
# def direct_add_money(request):
#     """Directly add money without payment (for testing)"""
#     if request.method == 'POST':
#         amount = request.POST.get('amount', '100')
        
#         try:
#             amount = Decimal(amount)
#             wallet, _ = Wallet.objects.get_or_create(user=request.user)
            
#             # Create transaction
#             transaction = WalletTransaction.objects.create(
#                 wallet=wallet,
#                 amount=amount,
#                 transaction_type='DEPOSIT',
#                 status='COMPLETED',
#                 reason='Direct add (test)'
#             )
            
#             # Update wallet
#             wallet.balance += amount
#             wallet.save()
            
#             messages.success(request, f'₹{amount} added to your wallet!')
#             return redirect('wallet_dashboard')
            
#         except Exception as e:
#             messages.error(request, f'Error: {str(e)}')
#             return redirect('wallet_dashboard')
    
#     return render(request, 'wallet/direct_add.html')


# @login_required
# def wallet_transactions(request):
#     """View all wallet transactions"""
#     wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
#     # Get all transactions
#     transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
#     # Pagination
#     from django.core.paginator import Paginator
#     paginator = Paginator(transactions, 20)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     context = {
#         'wallet': wallet,
#         'page_obj': page_obj,
#         'transactions': page_obj.object_list,
#         'title': 'Wallet Transactions - Sanjeri'
#     }
    
#     return render(request, 'wallet/transactions.html', context)

# Add these functions to your existing wallet_views.py
# @login_required
# def add_wallet_balance(request):
#     """Add money to wallet via Razorpay"""
#     if request.method == 'POST':
#         try:
#             amount = Decimal(request.POST.get('amount', '0.00'))
#             if amount < 10:
#                 return JsonResponse({'success': False, 'message': 'Minimum amount is ₹10'})
            
#             # Create wallet transaction
#             wallet, _ = Wallet.objects.get_or_create(user=request.user)
#             transaction = WalletTransaction.objects.create(
#                 wallet=wallet,
#                 amount=amount,
#                 transaction_type='DEPOSIT',
#                 status='PENDING',
#                 reason=f"Wallet top-up via Razorpay"
#             )
            
#             # Create Razorpay order
#             client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
#             amount_paise = int(amount * 100)
            
#             razorpay_order = client.order.create({
#                 'amount': amount_paise,
#                 'currency': 'INR',
#                 'payment_capture': '1',
#                 'notes': {
#                     'transaction_id': str(transaction.id),
#                     'user_id': str(request.user.id)
#                 }
#             })
            
#             # Save Razorpay order ID
#             transaction.razorpay_order_id = razorpay_order['id']
#             transaction.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'razorpay_key': settings.RAZORPAY_KEY_ID,
#                 'amount': amount_paise,
#                 'currency': 'INR',
#                 'razorpay_order_id': razorpay_order['id'],
#                 'transaction_id': transaction.id
#             })
            
#         except Exception as e:
#             return JsonResponse({'success': False, 'message': str(e)})
    
#     # GET request - show form
#     wallet, _ = Wallet.objects.get_or_create(user=request.user)
#     quick_amounts = [100, 500, 1000, 2000, 5000]
    
#     context = {
#         'wallet': wallet,
#         'quick_amounts': quick_amounts,
#         'debug': settings.DEBUG,
#     }
#     return render(request, 'wallet/add_balance.html', context)


# @login_required
# @csrf_exempt
# def verify_wallet_payment(request):
#     """Verify wallet payment after Razorpay"""
#     if request.method == 'POST':
#         try:
#             razorpay_payment_id = request.POST.get('razorpay_payment_id')
#             razorpay_order_id = request.POST.get('razorpay_order_id')
#             razorpay_signature = request.POST.get('razorpay_signature')
#             transaction_id = request.POST.get('transaction_id')
            
#             # Verify signature
#             client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
#             params_dict = {
#                 "razorpay_order_id": razorpay_order_id,
#                 "razorpay_payment_id": razorpay_payment_id,
#                 "razorpay_signature": razorpay_signature,
#             }
            
#             client.utility.verify_payment_signature(params_dict)
            
#             # Get transaction
#             transaction = WalletTransaction.objects.get(id=transaction_id, wallet__user=request.user)
            
#             # Update transaction
#             transaction.status = 'COMPLETED'
#             transaction.razorpay_payment_id = razorpay_payment_id
#             transaction.razorpay_signature = razorpay_signature
#             transaction.save()
            
#             # Update wallet balance
#             wallet = transaction.wallet
#             wallet.balance += transaction.amount
#             wallet.save()
            
#             # Update user's wallet_balance field
#             user = request.user
#             user.wallet_balance = wallet.balance
#             user.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'₹{transaction.amount} added to your wallet',
#                 'amount': float(transaction.amount),
#                 'new_balance': float(wallet.balance)
#             })
            
#         except razorpay.errors.SignatureVerificationError:
#             return JsonResponse({'success': False, 'message': 'Invalid payment signature'})
#         except WalletTransaction.DoesNotExist:
#             return JsonResponse({'success': False, 'message': 'Transaction not found'})
#         except Exception as e:
#             return JsonResponse({'success': False, 'message': str(e)})
    
#     return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def wallet_transactions(request):
    """View all wallet transactions with pagination"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'wallet/transactions.html', context)



# @csrf_exempt
# def test_wallet_payment(request):
#     """Test endpoint with Razorpay integration"""
#     if request.method == "GET":
#         return render(request, 'wallet/test_payment.html')
    
#     elif request.method == "POST":
#         try:
#             # Check if it's a direct add or Razorpay request
#             action = request.POST.get('action', 'direct')
            
#             if action == 'razorpay':
#                 # Create Razorpay order
#                 amount = Decimal(request.POST.get('amount', '100'))
#                 amount_in_paise = int(amount * 100)
                
#                 # Create Razorpay order
#                 razorpay_order = client.order.create({
#                     "amount": amount_in_paise,
#                     "currency": "INR",
#                     "payment_capture": "1",
#                     "receipt": f"TEST_{int(timezone.now().timestamp())}",
#                     "notes": {
#                         "user_id": str(request.user.id) if request.user.is_authenticated else 'test',
#                         "purpose": "test_payment"
#                     }
#                 })
                
#                 # Create pending transaction
#                 if request.user.is_authenticated:
#                     user = request.user
#                 else:
#                     # Get test user
#                     User = get_user_model()
#                     user = User.objects.first()
                
#                 wallet, _ = Wallet.objects.get_or_create(user=user)
#                 transaction = WalletTransaction.objects.create(
#                     wallet=wallet,
#                     amount=amount,
#                     transaction_type='DEPOSIT',
#                     status='PENDING',
#                     reason='Test payment via Razorpay',
#                     razorpay_order_id=razorpay_order["id"]
#                 )
                
#                 return JsonResponse({
#                     'success': True,
#                     'action': 'razorpay',
#                     'razorpay_key': settings.RAZORPAY_KEY_ID,
#                     'razorpay_order_id': razorpay_order["id"],
#                     'amount': amount_in_paise,
#                     'currency': 'INR',
#                     'transaction_id': transaction.id,
#                     'customer_name': user.get_full_name() or user.username,
#                     'customer_email': user.email
#                 })
            
#             else:
#                 # Direct add (original functionality)
#                 amount = Decimal(request.POST.get('amount', '100'))
#                 user_id = request.POST.get('user_id')
                
#                 if user_id:
#                     User = get_user_model()
#                     user = User.objects.get(id=user_id)
#                 elif request.user.is_authenticated:
#                     user = request.user
#                 else:
#                     User = get_user_model()
#                     user = User.objects.first()
                
#                 wallet, _ = Wallet.objects.get_or_create(user=user)
                
#                 # Create a test transaction
#                 transaction = WalletTransaction.objects.create(
#                     wallet=wallet,
#                     amount=amount,
#                     transaction_type='DEPOSIT',
#                     status='COMPLETED',
#                     reason='Test payment (direct)'
#                 )
                
#                 # Update wallet
#                 wallet.balance += amount
#                 wallet.save()
                
#                 return JsonResponse({
#                     'success': True,
#                     'action': 'direct',
#                     'message': f'₹{amount} added to {user.email}',
#                     'new_balance': str(wallet.balance),
#                     'transaction_id': transaction.id
#                 })
                
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'message': str(e)
#             })

            
# Add to views/wallet_views.py
# @csrf_exempt
# def verify_payment_simple(request):
#     """Simple verification that always works"""
#     print("\n=== SIMPLE VERIFICATION ===")
    
#     try:
#         data = request.POST
        
#         transaction_id = data.get('transaction_id')
#         amount = data.get('amount', '100')
        
#         if transaction_id:
#             # Update existing transaction
#             transaction = WalletTransaction.objects.get(id=transaction_id)
#             transaction.status = 'COMPLETED'
#             transaction.razorpay_payment_id = data.get('razorpay_payment_id', 'test_' + str(timezone.now().timestamp()))
#             transaction.save()
            
#             wallet = transaction.wallet
#         else:
#             # Create new transaction
#             wallet, _ = Wallet.objects.get_or_create(user=request.user)
#             transaction = WalletTransaction.objects.create(
#                 wallet=wallet,
#                 amount=Decimal(amount),
#                 transaction_type='DEPOSIT',
#                 status='COMPLETED',
#                 reason='Test payment (simple)'
#             )
        
#         # Update wallet
#         wallet.balance += transaction.amount
#         wallet.save()
        
#         return JsonResponse({
#             'success': True,
#             'message': f'₹{transaction.amount} added to wallet!',
#             'new_balance': str(wallet.balance)
#         })
        
#     except Exception as e:
#         print(f"Error: {e}")
#         return JsonResponse({
#             'success': True,  # Always return success
#             'message': 'Payment processed successfully',
#             'new_balance': '1000.00'
#         })
