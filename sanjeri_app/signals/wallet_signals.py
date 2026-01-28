from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from ..models import Wallet, WalletTransaction, Order, CustomUser

@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    """Automatically create wallet for new users"""
    if created:
        Wallet.objects.get_or_create(user=instance)


@receiver(post_save, sender=WalletTransaction)
def update_wallet_balance(sender, instance, created, **kwargs):
    """Update wallet balance when transaction status changes"""
    
    # Skip if it's a pending transaction
    if instance.status != 'COMPLETED':
        return
    
    try:
        wallet = instance.wallet
        old_balance = wallet.balance
        
        if instance.transaction_type in ['DEPOSIT', 'REFUND']:
            wallet.balance += instance.amount
            print(f"➕ Adding ₹{instance.amount} to wallet {wallet.id}")
        elif instance.transaction_type == 'WITHDRAWAL':
            wallet.balance -= instance.amount
            print(f"➖ Subtracting ₹{instance.amount} from wallet {wallet.id}")
        
        # Save the wallet
        wallet.save(update_fields=['balance'])
        
        # Also update the user's wallet_balance field
        user = wallet.user
        if hasattr(user, 'wallet_balance'):
            user.wallet_balance = wallet.balance
            user.save(update_fields=['wallet_balance'])
        
        print(f"💰 Wallet {wallet.id} updated: {old_balance} → {wallet.balance}")
        
    except Exception as e:
        print(f"❌ Error in update_wallet_balance: {e}")
def update_wallet_balance_amount(transaction):
    """Update wallet balance based on transaction"""
    try:
        if transaction.transaction_type in ['DEPOSIT', 'REFUND']:
            transaction.wallet.balance += transaction.amount
        elif transaction.transaction_type == 'WITHDRAWAL':
            transaction.wallet.balance -= transaction.amount
        
        transaction.wallet.save()
        print(f"💰 Wallet {transaction.wallet.user.email} updated: {transaction.transaction_type} ₹{transaction.amount}")
        
    except Exception as e:
        print(f"❌ Error updating wallet balance: {e}")


@receiver(post_save, sender=Order)
def handle_order_refund_signals(sender, instance, created, **kwargs):
    """Handle all order-related wallet signals"""
    
    # 1. Create pending refund when return is requested
    if not created and instance.status == 'return_requested':
        try:
            wallet, _ = Wallet.objects.get_or_create(user=instance.user)
            
            # Check if pending refund already exists
            existing = WalletTransaction.objects.filter(
                order=instance,
                transaction_type='REFUND',
                status='PENDING'
            ).exists()
            
            if not existing:
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=instance.total_amount,
                    transaction_type='REFUND',
                    status='PENDING',
                    reason=f"Return request: {instance.return_reason}",
                    order=instance,
                    admin_approved=False
                )
                print(f"✅ Pending refund created for order #{instance.order_number}")
        except Exception as e:
            print(f"❌ Error creating refund transaction: {e}")
    
    # 2. Process wallet refund when status changes to refunded
    elif not created:  # Only for existing orders
        try:
            if instance.pk:
                # Get the previous state
                old_order = Order.objects.get(pk=instance.pk)
                
                # Check if status changed to refunded
                if old_order.status != 'refunded' and instance.status == 'refunded':
                    print(f"🔄 Processing refund for order #{instance.order_number}")
                    
                    # Process wallet refund
                    process_wallet_refund(instance)
                    
        except Order.DoesNotExist:
            pass
        except Exception as e:
            print(f"❌ Error in handle_order_refund_signals: {e}")

# Update this function in your signals.py
def process_wallet_refund(order):
    """Process refund to wallet when order is marked as refunded"""
    try:
        print(f"🔄 Processing wallet refund for order #{order.order_number}")
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(user=order.user)
        print(f"Wallet for {order.user.email}: {wallet.id}, balance: {wallet.balance}")
        
        # Calculate refund amount
        refund_amount = order.total_amount
        print(f"Refund amount: ₹{refund_amount}")
        
        # Check if refund already processed
        existing_refund = WalletTransaction.objects.filter(
            order=order,
            transaction_type='REFUND',
            status='COMPLETED'
        ).exists()
        
        if existing_refund:
            print(f"⚠️ Refund already processed for order #{order.order_number}")
            return
        
        # Check for pending refund (from return request)
        pending_refund = WalletTransaction.objects.filter(
            order=order,
            transaction_type='REFUND',
            status='PENDING'
        ).first()
        
        if pending_refund:
            print(f"Found pending refund transaction: {pending_refund.id}")
            # Update existing pending refund to COMPLETED
            pending_refund.status = 'COMPLETED'
            pending_refund.admin_approved = True
            pending_refund.reason = f"Approved refund for order #{order.order_number}"
            pending_refund.save()  # This will trigger the signal
            
        else:
            # Create new COMPLETED refund transaction
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                amount=refund_amount,
                transaction_type='REFUND',
                status='COMPLETED',
                reason=f"Refund for order #{order.order_number}",
                order=order,
                admin_approved=True
            )
            print(f"✅ Created new refund transaction: {transaction.id}")
        
        # Manually update wallet balance to ensure it's updated
        wallet.refresh_from_db()  # Get latest wallet data
        wallet.balance += Decimal(refund_amount)
        wallet.save(update_fields=['balance'])
        
        # Update user's wallet_balance field
        user = order.user
        if hasattr(user, 'wallet_balance'):
            user.wallet_balance = wallet.balance
            user.save(update_fields=['wallet_balance'])
            print(f"Updated user wallet_balance: ₹{user.wallet_balance}")
        
        print(f"✅ Final wallet balance for {order.user.email}: ₹{wallet.balance}")
        
    except Exception as e:
        print(f"❌ Error processing refund: {e}")
        import traceback
        traceback.print_exc()