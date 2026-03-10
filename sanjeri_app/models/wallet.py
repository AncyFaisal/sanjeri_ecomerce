# sanjeri_app/models/wallet.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

class Wallet(models.Model):
    """User wallet for storing credit balance"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
    
    def __str__(self):
        return f"Wallet - {self.user.email} (₹{self.balance})"
    
    @property
    def available_balance(self):
        """Get available balance (excluding pending withdrawals)"""
        pending_withdrawals = self.transactions.filter(
            status='PENDING',
            transaction_type='WITHDRAWAL'
        ).aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0')
        
        return self.balance - pending_withdrawals
    
    def withdraw(self, amount, reason="", order=None):
        """Withdraw money from wallet"""
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive")
        
        # Quantize amount to 2 decimal places
        from decimal import Decimal, ROUND_DOWN
        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        
        # Use select_for_update to prevent race conditions
        from django.db import transaction
        
        with transaction.atomic():
            # Refresh wallet from database and lock it
            wallet = Wallet.objects.select_for_update().get(id=self.id)
            
            # Also quantize wallet balance for comparison
            wallet_balance = wallet.balance.quantize(Decimal('0.01'))
            amount = amount.quantize(Decimal('0.01'))
            
            if wallet_balance < amount:
                raise ValidationError(
                    f"Insufficient balance. Available: ₹{wallet_balance}, Requested: ₹{amount}"
                )
            
            # Create withdrawal transaction
            transaction_obj = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='WITHDRAWAL',
                status='COMPLETED',
                reason=reason,
                order=order
            )
            
            # Update wallet balance
            wallet.balance = (wallet.balance - amount).quantize(Decimal('0.01'))
            wallet.save(update_fields=['balance'])
            
            # Update user's wallet_balance field
            user = wallet.user
            if hasattr(user, 'wallet_balance'):
                user.wallet_balance = wallet.balance
                user.save(update_fields=['wallet_balance'])
            
            return transaction_obj
    
    def deposit(self, amount, reason="", order=None, transaction_type='DEPOSIT'):
        """Deposit money to wallet"""
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive")
        
        # Create deposit transaction
        transaction = WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type=transaction_type,
            status='COMPLETED',
            reason=reason,
            order=order
        )
        
        # Update balance
        self.balance += amount
        self.save(update_fields=['balance'])
        
        # Update user's wallet_balance field
        user = self.user
        if hasattr(user, 'wallet_balance'):
            user.wallet_balance = self.balance
            user.save(update_fields=['wallet_balance'])
        
        return transaction


class WalletTransaction(models.Model):
    """Wallet transaction history"""
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('REFUND', 'Refund'),
        ('CASHBACK', 'Cashback'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Razorpay fields for wallet top-ups
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Reference to order (if applicable)
    order = models.ForeignKey(
        'Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    
    # Reason for transaction
    reason = models.TextField(blank=True)
    
    # Admin approval for refunds
    admin_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
    
    def __str__(self):
        return f"{self.transaction_type} - ₹{self.amount} - {self.status}"
    
    def clean(self):
        """Validate transaction"""
        if self.amount <= 0:
            raise ValidationError("Amount must be positive")
    
    def save(self, *args, **kwargs):
        # Quantize amount before saving
        from decimal import Decimal
        if self.amount:
            self.amount = Decimal(str(self.amount)).quantize(Decimal('0.01'))
        self.full_clean()
        super().save(*args, **kwargs)
    
    def mark_as_completed(self, approved_by=None):
        """Mark transaction as completed (for refunds)"""
        # ===== ADD THIS: Prevent double completion =====
        if self.status == 'COMPLETED':
            print(f"⚠️ Transaction {self.id} already completed")
            return True
        # ===== END ADDITION =====
        
        if self.status == 'PENDING' and self.transaction_type == 'REFUND':
            self.status = 'COMPLETED'
            self.admin_approved = True
            if approved_by:
                self.approved_by = approved_by
            self.save()
            
            # Add amount to wallet balance
            self.wallet.balance += self.amount
            self.wallet.save(update_fields=['balance'])
            
            # Update user's wallet_balance field
            user = self.wallet.user
            if hasattr(user, 'wallet_balance'):
                user.wallet_balance = self.wallet.balance
                user.save(update_fields=['wallet_balance'])
            
            return True
        return False
    
    def mark_as_failed(self):
        """Mark transaction as failed"""
        self.status = 'FAILED'
        self.save()
    
    @property
    def is_deposit(self):
        return self.transaction_type == 'DEPOSIT'
    
    @property
    def is_withdrawal(self):
        return self.transaction_type == 'WITHDRAWAL'
    
    @property
    def is_refund(self):
        return self.transaction_type == 'REFUND'
    
    @property
    def display_amount(self):
        """Display amount with +/- sign"""
        if self.is_deposit or self.is_refund:
            return f"+₹{self.amount}"
        else:
            return f"-₹{self.amount}"