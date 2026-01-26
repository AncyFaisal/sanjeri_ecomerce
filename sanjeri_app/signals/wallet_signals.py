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
    
    # If it's a new COMPLETED transaction
    if created and instance.status == 'COMPLETED':
        update_wallet_balance_amount(instance)
    
    # If an existing transaction status changed to COMPLETED
    elif not created:
        try:
            old_transaction = WalletTransaction.objects.get(pk=instance.pk)
            if old_transaction.status != 'COMPLETED' and instance.status == 'COMPLETED':
                update_wallet_balance_amount(instance)
        except WalletTransaction.DoesNotExist:
            pass


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


def process_wallet_refund(order):
    """Process refund to wallet when order is marked as refunded"""
    try:
        # Get or create wallet
        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        
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
            # Update existing pending refund to COMPLETED
            pending_refund.status = 'COMPLETED'
            pending_refund.admin_approved = True
            pending_refund.reason = f"Approved refund for order #{order.order_number}"
            pending_refund.save()
            
            print(f"✅ Updated pending refund to COMPLETED for order #{order.order_number}")
        else:
            # Create new COMPLETED refund transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=order.total_amount,
                transaction_type='REFUND',
                status='COMPLETED',
                reason=f"Refund for order #{order.order_number}",
                order=order,
                admin_approved=True
            )
            print(f"✅ Created new refund transaction for order #{order.order_number}")
        
        # Update wallet balance (signal will handle this automatically)
        # But we need to trigger it by saving the transaction
        if pending_refund:
            # Save to trigger the update_wallet_balance signal
            pending_refund.save()
        else:
            # The signal will handle the newly created transaction
            pass
        
        # Update order fields
        order.refund_amount = order.total_amount
        order.refund_processed_at = timezone.now()
        
        # Save order without triggering the signal again
        Order.objects.filter(pk=order.pk).update(
            refund_amount=order.total_amount,
            refund_processed_at=order.refund_processed_at
        )
        
        # Also update user's wallet_balance field if it exists
        if hasattr(order.user, 'wallet_balance'):
            order.user.wallet_balance += order.total_amount
            order.user.save(update_fields=['wallet_balance'])
        
        print(f"✅ Refund processed: ₹{order.total_amount} added to {order.user.email}'s wallet")
        
    except Exception as e:
        print(f"❌ Error processing refund: {e}")
        import traceback
        traceback.print_exc()