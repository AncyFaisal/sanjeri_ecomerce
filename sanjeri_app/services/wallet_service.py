# sanjeri_app/services/wallet_service.py
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Wallet, WalletTransaction, Order

class WalletService:
    """Service class for wallet operations"""
    
    @staticmethod
    def get_or_create_wallet(user):
        """Get or create wallet for user"""
        wallet, created = Wallet.objects.get_or_create(user=user)
        return wallet
    
    @staticmethod
    def process_cancellation_refund(order, reason=""):
        """
        Process refund for cancelled order - direct refund to wallet
        Returns: (success, message, transaction)
        """
        try:
            # Check if order was paid
            if order.payment_status not in ['completed', 'success', 'partially_paid']:
                return False, "Order was not paid, no refund needed", None
            
            # Check if refund already processed
            existing_refund = WalletTransaction.objects.filter(
                order=order,
                transaction_type='REFUND',
                status='COMPLETED'
            ).exists()
            
            if existing_refund:
                return False, "Refund already processed for this order", None
            
            # Calculate refund amount
            refund_amount = order.total_amount
            
            # Get or create wallet
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            
            with transaction.atomic():
                # Create refund transaction
                refund_transaction = WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type='REFUND',
                    status='COMPLETED',
                    admin_approved=True,
                    reason=f"Refund for cancelled order #{order.order_number}: {reason}",
                    order=order
                )
                
                # Update wallet balance
                wallet.balance += refund_amount
                wallet.save(update_fields=['balance'])
                
                # Update user's wallet_balance field
                user = order.user
                if hasattr(user, 'wallet_balance'):
                    user.wallet_balance = wallet.balance
                    user.save(update_fields=['wallet_balance'])
                
                # Update order
                order.refund_amount = refund_amount
                order.refund_to_wallet = True
                order.refund_processed_at = timezone.now()
                order.save(update_fields=['refund_amount', 'refund_to_wallet', 'refund_processed_at'])
                
                return True, f"Refund of ₹{refund_amount} processed to wallet", refund_transaction
                
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def create_return_refund_request(order, reason):
        """
        Create pending refund request for return - requires admin approval
        Returns: (success, message, transaction)
        """
        try:
            # Check if refund already requested
            existing_pending = WalletTransaction.objects.filter(
                order=order,
                transaction_type='REFUND',
                status='PENDING'
            ).exists()
            
            if existing_pending:
                return False, "Refund request already pending for this order", None
            
            # Check if refund already processed
            existing_completed = WalletTransaction.objects.filter(
                order=order,
                transaction_type='REFUND',
                status='COMPLETED'
            ).exists()
            
            if existing_completed:
                return False, "Refund already processed for this order", None
            
            # Get or create wallet
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            
            # Create pending refund transaction
            refund_request = WalletTransaction.objects.create(
                wallet=wallet,
                amount=order.total_amount,
                transaction_type='REFUND',
                status='PENDING',
                admin_approved=False,
                reason=f"Return request: {reason}",
                order=order
            )
            
            return True, "Return request submitted, pending admin approval", refund_request
            
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def approve_return_refund(transaction, approved_by):
        """
        Approve pending refund and credit to wallet
        Returns: (success, message)
        """
        try:
            if transaction.status != 'PENDING':
                return False, "Transaction is not in pending state"
            
            if transaction.transaction_type != 'REFUND':
                return False, "Transaction is not a refund"
            
            with transaction.atomic():
                # Mark as completed
                transaction.status = 'COMPLETED'
                transaction.admin_approved = True
                transaction.approved_by = approved_by
                transaction.save()
                
                # Credit to wallet
                wallet = transaction.wallet
                wallet.balance += transaction.amount
                wallet.save(update_fields=['balance'])
                
                # Update user's wallet_balance field
                user = wallet.user
                if hasattr(user, 'wallet_balance'):
                    user.wallet_balance = wallet.balance
                    user.save(update_fields=['wallet_balance'])
                
                # Update order
                order = transaction.order
                if order:
                    order.refund_amount = transaction.amount
                    order.refund_to_wallet = True
                    order.refund_processed_at = timezone.now()
                    order.save(update_fields=['refund_amount', 'refund_to_wallet', 'refund_processed_at'])
                
                return True, f"Refund of ₹{transaction.amount} approved and credited to wallet"
                
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def reject_return_refund(transaction, rejection_reason=""):
        """
        Reject pending refund request
        Returns: (success, message)
        """
        try:
            if transaction.status != 'PENDING':
                return False, "Transaction is not in pending state"
            
            transaction.status = 'CANCELLED'
            transaction.reason = f"{transaction.reason} [REJECTED: {rejection_reason}]"
            transaction.save()
            
            return True, "Refund request rejected"
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_user_wallet_balance(user):
        """Get user's wallet balance"""
        try:
            wallet = Wallet.objects.get(user=user)
            return wallet.balance
        except Wallet.DoesNotExist:
            return Decimal('0')
    
    @staticmethod
    def get_user_transactions(user, limit=None):
        """Get user's wallet transactions"""
        try:
            wallet = Wallet.objects.get(user=user)
            queryset = wallet.transactions.all().order_by('-created_at')
            if limit:
                queryset = queryset[:limit]
            return queryset
        except Wallet.DoesNotExist:
            return []