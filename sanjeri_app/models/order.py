# models/order.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from .product import ProductVariant
from .user_models import Address
from decimal import Decimal
from datetime import timedelta 
# from .wallet import WalletTransaction,Wallet

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('out_for_delivery', 'Out for Delivery'),
        ('return_requested', 'Return Requested'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
        ('wallet', 'Wallet Payment'),
        ('mixed', 'Mixed Payment (Wallet + Online)'),
    ]
    
    # UPDATED: Added 'partially_paid' to payment status choices
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_paid', 'Partially Paid'),
        # Keep existing choices, add 'success' for Razorpay
        ('success', 'Success'),
    ]
    
    # Order basics
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    
    # Shipping address (snapshot at time of order)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Coupon
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    offer_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Order status and dates
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Cancellation and Return fields (already present)
    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True) #Stores the customer's reason for requesting a return
    return_rejection_reason = models.TextField(blank=True, null=True) #Stores the admin's reason for rejecting a return request 
    cancelled_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # ADDED: Razorpay payment gateway fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Wallet fields 
    wallet_used = models.BooleanField(default=False)
    wallet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_to_wallet = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_processed_at = models.DateTimeField(null=True, blank=True)
    wallet_amount_used = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Amount paid from wallet"
    )
    
    # Additional info
    notes = models.TextField(blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
    return_rejected_at = models.DateTimeField(null=True, blank=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)
    return_approved_at = models.DateTimeField(null=True, blank=True)
    return_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_returns'
    )
    return_status = models.CharField(
        max_length=20,
        choices=[
            ('not_requested', 'Not Requested'),
            ('requested', 'Return Requested'),
            ('approved', 'Return Approved'),
            ('rejected', 'Return Rejected'),
            ('completed', 'Return Completed'),
        ],
        default='not_requested'
    )

    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'created_at'] 
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['payment_status', 'status']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.user.get_full_name() or self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Update payment status for COD on delivery
        if self.status == 'delivered' and self.delivered_at is None:
            self.delivered_at = timezone.now()
            if self.payment_method == 'cod' and self.payment_status == 'pending':
                self.payment_status = 'completed'
        
        # Update wallet usage flag
        if self.wallet_amount_used > 0:
            self.wallet_used = True
            self.wallet_amount = self.wallet_amount_used  # Ensure consistency
        
        # Determine payment status based on wallet usage
        if self.wallet_used and self.wallet_amount_used > 0:
            if self.wallet_amount_used >= self.total_amount:
                # Full wallet payment
                if self.payment_status in ['pending', 'partially_paid']:
                    self.payment_status = 'completed'
            else:
                # Partial wallet payment
                if self.payment_status == 'pending':
                    self.payment_status = 'partially_paid'
        
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number within 20 character limit"""
        import random
        import time
        
        # Use shorter timestamp format (YYYYMMDD + time in seconds)
        timestamp = timezone.now().strftime('%y%m%d%H%M%S')  # %y = 2-digit year
        
        # Generate shorter random string
        import secrets
        random_str = secrets.token_hex(2)[:3].upper()  # 3 characters
        
        # Create order number: ORD + timestamp (14) + random (3) = 20 characters
        order_number = f"ORD{timestamp}{random_str}"
        
        # Ensure it's exactly 20 characters
        order_number = order_number[:20]
        
        # Ensure uniqueness
        while Order.objects.filter(order_number=order_number).exists():
            random_str = secrets.token_hex(2)[:3].upper()
            order_number = f"ORD{timestamp}{random_str}"[:20]
        
        return order_number
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']
    
    @property
    def can_be_returned(self):
        """Check if order can be returned (delivered and within return period)"""
        if self.status != 'delivered':
            return False
        
        # Check if within return period (e.g., 7 days from delivery)
        return_period = timezone.now() - timedelta(days=7)
        if self.delivered_at:
            return self.delivered_at >= return_period
        return self.created_at >= return_period
    
    @property
    def amount_to_pay(self):
        """
        Calculate remaining amount to pay after wallet deduction.
        This is the amount that needs to be paid via Razorpay.
        """
        if self.payment_status in ['completed', 'success']:
            return Decimal('0')
        
        # Calculate remaining amount
        if self.wallet_used and self.wallet_amount > 0:
            remaining = self.total_amount - self.wallet_amount
            return max(remaining, Decimal('0'))
        
        return self.total_amount
    
   
    @property
    def can_pay_online(self):
        """Check if order can be paid online"""
        # Order must be in a state where online payment makes sense
        valid_statuses = ['pending', 'confirmed', 'pending_payment']
        
        # Payment must be pending, partially paid, OR failed (for retry)
        valid_payment_statuses = ['pending', 'partially_paid', 'failed']
        
        # Payment method must support online payment
        valid_payment_methods = ['online', 'mixed']
        
        return (
            self.status in valid_statuses and
            self.payment_status in valid_payment_statuses and
            self.payment_method in valid_payment_methods and
            self.amount_to_pay > 0
        )

    @property
    def is_fully_paid(self):
        """Check if order is fully paid"""
        if self.payment_status in ['completed', 'success']:
            return True
        
        # If wallet covers entire amount
        if self.wallet_used and self.wallet_amount >= self.total_amount:
            return True
        
        return False
    
    @property
    def payment_summary(self):
        """Get payment summary for display"""
        summary = {
            'subtotal': self.subtotal,
            'discount': self.discount_amount,
            'shipping': self.shipping_charge,
            'tax': self.tax_amount,
            'total': self.total_amount,
            'wallet_used': self.wallet_amount,
            'amount_to_pay': self.amount_to_pay,
        }
        
        if self.coupon:
            summary['coupon'] = {
                'code': self.coupon.code,
                'discount': self.coupon_discount
            }
        
        return summary
    
    
    def mark_as_paid(self, razorpay_payment_id=None, razorpay_signature=None):
        """Mark order as paid (complete payment)"""
        if self.payment_status in ['completed', 'success']:
            return False
        
        # Use 'success' for Razorpay payments
        if razorpay_payment_id:
            self.payment_status = 'success'
        else:
            self.payment_status = 'completed'
        
        # Update status if it's pending
        if self.status == 'pending':
            self.status = 'confirmed'
        
        if razorpay_payment_id:
            self.razorpay_payment_id = razorpay_payment_id
        
        if razorpay_signature:
            self.razorpay_signature = razorpay_signature
        
        self.save()
        return True
    

    def update_razorpay_info(self, razorpay_order_id):
        """Update Razorpay order ID for tracking"""
        self.razorpay_order_id = razorpay_order_id
        self.save()
    
    def mark_payment_failed(self):
        """Mark payment as failed for Razorpay"""
        self.payment_status = 'failed'
        self.save()
    
    def cancel_order(self, reason=""):
        """Cancel order - only refund if payment was made"""
        from django.apps import apps
        Wallet = apps.get_model('sanjeri_app', 'Wallet')
        WalletTransaction = apps.get_model('sanjeri_app', 'WalletTransaction')

        if not self.can_be_cancelled:
            return False
        
        try:
            # Restore stock for all items
            for item in self.items.all():
                item.variant.stock += item.quantity
                item.variant.save()
            
            # ========== FIXED REFUND LOGIC ==========
            refund_amount = Decimal('0')
            
            # Check if user actually paid anything
            user_paid = self.payment_status in ['completed', 'success', 'partially_paid']
            
            # Only process refunds if user actually paid
            if user_paid:
                # Refund wallet amount if used
                if self.wallet_amount_used > 0 and self.wallet_used:
                    try:
                        from .wallet import WalletTransaction
                        # Get user's wallet
                        wallet, created = Wallet.objects.get_or_create(user=self.user)
                        
                        # Create COMPLETED refund transaction
                        transaction = WalletTransaction.objects.create(
                            wallet=wallet,
                            amount=self.wallet_amount_used,
                            transaction_type='REFUND',
                            status='COMPLETED',
                            reason=f"Refund for cancelled order #{self.order_number}: {reason}",
                            order=self,
                            admin_approved=True
                        )
                        
                        # Update wallet balance through the signal
                        wallet.refresh_from_db()
                        wallet.balance += Decimal(self.wallet_amount_used)
                        wallet.save(update_fields=['balance'])
                        
                        # Update user's wallet_balance field
                        self.user.wallet_balance = wallet.balance
                        self.user.save(update_fields=['wallet_balance'])
                        
                        self.refund_to_wallet = True
                        refund_amount += self.wallet_amount_used
                        print(f"✅ Wallet refund of ₹{self.wallet_amount_used} processed")
                        print(f"   Wallet balance updated to: ₹{wallet.balance}")
                        
                    except Exception as e:
                        print(f"❌ Wallet refund failed: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Refund Razorpay amount if paid online
                if self.payment_status == 'success' and self.razorpay_payment_id:
                    # Calculate online payment amount
                    online_amount = self.total_amount - self.wallet_amount_used
                    if online_amount > 0:
                        try:
                            # Initiate Razorpay refund
                            import razorpay
                            from django.conf import settings
                            
                            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                            
                            # Create refund in Razorpay
                            refund = client.payment.refund(
                                self.razorpay_payment_id,
                                {
                                    'amount': int(online_amount * 100),  # Convert to paise
                                    'notes': {
                                        'order_id': str(self.id),
                                        'order_number': self.order_number,
                                        'reason': f"Cancellation: {reason}"
                                    }
                                }
                            )
                            
                            # Record refund details
                            self.razorpay_refund_id = refund.get('id')
                            refund_amount += online_amount
                            print(f"✅ Razorpay refund initiated: {refund.get('id')}")
                            
                            # Also refund to wallet for online payments
                            wallet, created = Wallet.objects.get_or_create(user=self.user)
                            wallet_transaction = WalletTransaction.objects.create(
                                wallet=wallet,
                                amount=online_amount,
                                transaction_type='REFUND',
                                status='COMPLETED',
                                reason=f"Razorpay refund for cancelled order #{self.order_number}",
                                order=self,
                                admin_approved=True
                            )
                            
                            # Update wallet balance
                            wallet.balance += Decimal(online_amount)
                            wallet.save(update_fields=['balance'])
                            
                            # Update user's wallet_balance field
                            self.user.wallet_balance = wallet.balance
                            self.user.save(update_fields=['wallet_balance'])
                            
                        except Exception as e:
                            print(f"❌ Razorpay refund failed: {e}")
                            import traceback
                            traceback.print_exc()
            else:
                # User didn't pay, so no refund needed
                print(f"ℹ️ Order cancelled - no refund needed (payment was pending)")
            
            # ========== END FIX ==========
            
            # Update order status and cancellation details
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.cancelled_at = timezone.now()
            self.refund_amount = refund_amount
            self.refund_processed_at = timezone.now() if user_paid else None
            
            # Update payment status based on whether it was paid
            if user_paid:
                self.payment_status = 'refunded'
            else:
                self.payment_status = 'cancelled'
            
            # Force save to ensure all fields are updated
            self.save()
            
            print(f"✅ Order #{self.order_number} cancelled successfully")
            print(f"   Status: {self.status}, Payment Status: {self.payment_status}")
            print(f"   Refund Amount: ₹{refund_amount}")
            print(f"   Cancelled at: {self.cancelled_at}")
            
            # DEBUG: Check wallet balance
            try:
                wallet = Wallet.objects.get(user=self.user)
                print(f"💰 Wallet balance after cancellation: ₹{wallet.balance}")
                print(f"👤 User wallet_balance field: ₹{self.user.wallet_balance}")
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ Error cancelling order {self.order_number}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def request_return(self, reason):
        """Request return - creates PENDING refund (requires admin approval)"""
        if not self.can_be_returned:
            return False
        
        if not reason or not reason.strip():
            return False
        
        try:
            # Update order status
            self.status = 'return_requested'
            self.return_reason = reason
            self.return_requested_at = timezone.now()
            self.return_status = 'requested'
            self.save()
            
            # Create PENDING refund transaction (requires admin approval)
            from .wallet import WalletTransaction
            WalletTransaction.objects.create(
                wallet=self.user.wallet,
                amount=self.total_amount,
                transaction_type='REFUND',
                status='PENDING',  # PENDING - needs admin approval
                reason=f"Return request: {reason}",
                order=self,
                admin_approved=False
            )
            
            print(f"✅ Return requested for order #{self.order_number}")
            print(f"⚠️ Refund of ₹{self.total_amount} is PENDING admin approval")
            
            return True
            
        except Exception as e:
            print(f"Error requesting return: {e}")
            return False
    
    def approve_return(self, approved_by):
        """Admin approves return and processes refund"""
        if self.return_status != 'requested':
            return False
        
        # ===== ADD THIS: Prevent double processing =====
        # Check if already approved
        if self.return_status == 'approved':
            print(f"⚠️ Return for order #{self.order_number} already approved")
            return False
        
        # Check if refund already processed
        from .wallet import WalletTransaction
        existing_refund = WalletTransaction.objects.filter(
            order=self,
            transaction_type='REFUND',
            status='COMPLETED'
        ).exists()
        
        if existing_refund:
            print(f"⚠️ Refund already processed for order #{self.order_number}")
            return False
        # ===== END ADDITION =====

        try:
            # Get user's wallet
            from .wallet import Wallet
            wallet, created = Wallet.objects.get_or_create(user=self.user)
            
            # Update return status
            self.return_status = 'approved'
            self.return_approved_at = timezone.now()
            self.return_approved_by = approved_by
            self.status = 'refunded'
            
            # Calculate refund amount
            refund_amount = self.total_amount
            
            # Update payment status
            if self.payment_status in ['completed', 'success', 'partially_paid']:
                self.payment_status = 'refunded'
            
            self.save()
            
            # Find and approve the pending refund transaction
            from .wallet import WalletTransaction
            refund_transaction = WalletTransaction.objects.filter(
                order=self,
                transaction_type='REFUND',
                status='PENDING'
            ).first()
            
            if refund_transaction:
                # Mark as completed
                refund_transaction.status = 'COMPLETED'
                refund_transaction.admin_approved = True
                refund_transaction.approved_by = approved_by
                refund_transaction.save()
                
                # Update wallet balance
                wallet.refresh_from_db()
                wallet.balance += Decimal(refund_amount)
                wallet.save(update_fields=['balance'])
                
                # Update user's wallet_balance field
                self.user.wallet_balance = wallet.balance
                self.user.save(update_fields=['wallet_balance'])
                
                print(f"✅ Return approved and ₹{refund_transaction.amount} refunded to wallet")
                print(f"💰 Wallet balance: ₹{wallet.balance}")
            
            # If there was online payment, also initiate Razorpay refund
            if self.payment_status == 'refunded' and self.razorpay_payment_id:
                try:
                    import razorpay
                    from django.conf import settings
                    
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    
                    # Calculate online portion of refund
                    online_amount = self.total_amount - self.wallet_amount_used
                    if online_amount > 0:
                        # Create refund in Razorpay
                        refund = client.payment.refund(
                            self.razorpay_payment_id,
                            {
                                'amount': int(online_amount * 100),
                                'notes': {
                                    'order_id': str(self.id),
                                    'order_number': self.order_number,
                                    'reason': 'Order return approved'
                                }
                            }
                        )
                        
                        print(f"✅ Razorpay refund initiated: {refund.get('id')}")
                    
                except Exception as e:
                    print(f"⚠️ Razorpay refund failed (but wallet refund processed): {e}")
                    import traceback
                    traceback.print_exc()
            
            return True
            
        except Exception as e:
            print(f"Error approving return: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def reject_return(self, rejection_reason=""):
        """Admin rejects return request"""
        if self.return_status != 'requested':
            return False
        
        try:
            self.return_status = 'rejected'
            self.return_rejection_reason = rejection_reason  # Store reason separately
            self.return_rejected_at = timezone.now() 
            self.status = 'delivered'  # Revert to delivered
            self.save()
            
            # Mark pending refund as failed
            from .wallet import WalletTransaction
            refund_transaction = WalletTransaction.objects.filter(
                order=self,
                transaction_type='REFUND',
                status='PENDING'
            ).first()
            
            if refund_transaction:
                refund_transaction.status = 'CANCELLED'
                refund_transaction.reason = f"Return rejected: {rejection_reason}"
                refund_transaction.save()
            
            return True
            
        except Exception as e:
            print(f"Error rejecting return: {e}")
            return False
    
    def calculate_totals(self):
        """
        Calculate order totals. This should ONLY be called when:
        1. Order items are added/changed (admin edits)
        2. After returns/cancellations
        NOT during normal checkout flow
        """
        from decimal import Decimal
        
        # Calculate subtotal from items
        self.subtotal = sum(item.total_price for item in self.items.all())
        
        # ONLY recalculate coupon if it exists and discount is 0
        if self.coupon and self.coupon_discount == 0:
            self.coupon_discount = self.coupon.calculate_discount(self.subtotal)
            # Don't discount more than subtotal
            if self.coupon_discount > self.subtotal:
                self.coupon_discount = self.subtotal
        
        # Use existing discount_amount if already set (from checkout)
        if self.discount_amount == 0:
            # Calculate total discount from all sources
            self.discount_amount = self.coupon_discount + (self.offer_discount or 0)
        
        # Calculate final amounts
        after_discount = self.subtotal - self.discount_amount
        
        # Shipping (free above ₹500)
        self.shipping_charge = Decimal('0') if after_discount > Decimal('500') else Decimal('40')
        
        # Tax (18% GST)
        self.tax_amount = after_discount * Decimal('0.18')
        
        # Total amount
        self.total_amount = after_discount + self.shipping_charge + self.tax_amount
        
        self.save()


class OrderItem(models.Model):
    """Individual items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)  # Snapshot of product name
    variant_details = models.CharField(max_length=100)  # Snapshot of variant details
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Individual item cancellation
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    return_requested = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True, null=True)
    return_rejection_reason = models.TextField(blank=True, null=True)
    return_status = models.CharField(
        max_length=20,
        choices=[
            ('not_requested', 'Not Requested'),
            ('requested', 'Return Requested'),
            ('approved', 'Return Approved'),
            ('rejected', 'Return Rejected'),
            ('completed', 'Return Completed'),
        ],
        default='not_requested'
    )
    return_requested_at = models.DateTimeField(null=True, blank=True)
    return_approved_at = models.DateTimeField(null=True, blank=True)
    return_rejected_at = models.DateTimeField(null=True, blank=True)

    # Store image at time of order
    product_image = models.ImageField(upload_to='order_items/', blank=True, null=True)
    
    class Meta:
        ordering = ['-id']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name} in Order #{self.order.order_number}"
    
    def request_item_return(self, reason):
        """Request return for individual item"""
        if self.is_cancelled:
            return False, "Item is already cancelled"
        
        if self.return_status != 'not_requested':
            return False, f"Return already {self.get_return_status_display()}"
        
        try:
            self.return_requested = True
            self.return_reason = reason
            self.return_status = 'requested'
            self.return_requested_at = timezone.now()
            self.save()
            
            # Create PENDING refund transaction for this item
            from .wallet import WalletTransaction
            WalletTransaction.objects.create(
                wallet=self.order.user.wallet,
                amount=self.total_price,
                transaction_type='REFUND',
                status='PENDING',
                reason=f"Return request for item: {self.product_name} (Order #{self.order.order_number})",
                order=self.order,
                admin_approved=False
            )
            
            print(f"✅ Item return requested: {self.product_name} - ₹{self.total_price} PENDING")
            return True, "Return request submitted successfully"
            
        except Exception as e:
            print(f"Error requesting item return: {e}")
            return False, str(e)
    
    def approve_item_return(self, approved_by):
        """Admin approves individual item return"""
        if self.return_status != 'requested':
            return False
        
        try:
            self.return_status = 'approved'
            self.return_approved_at = timezone.now()
            self.save()
            
            # Find and approve the pending refund transaction for this item
            from .wallet import WalletTransaction
            refund = WalletTransaction.objects.filter(
                order=self.order,
                transaction_type='REFUND',
                status='PENDING',
                reason__contains=f"item: {self.product_name}"
            ).first()
            
            if refund:
                refund.status = 'COMPLETED'
                refund.admin_approved = True
                refund.approved_by = approved_by
                refund.save()
                
                # Update wallet balance
                wallet = self.order.user.wallet
                wallet.balance += self.total_price
                wallet.save()
                
                # Update user's wallet_balance field
                self.order.user.wallet_balance = wallet.balance
                self.order.user.save(update_fields=['wallet_balance'])
            
            # Restore stock
            self.variant.stock += self.quantity
            self.variant.save()
            
            print(f"✅ Item return approved: {self.product_name} - ₹{self.total_price} refunded")
            return True
            
        except Exception as e:
            print(f"Error approving item return: {e}")
            return False
    
    def reject_item_return(self, rejection_reason, rejected_by):
        """Admin rejects individual item return"""
        if self.return_status != 'requested':
            return False
        
        try:
            self.return_status = 'rejected'
            self.return_rejected_at = timezone.now()
            self.return_rejection_reason = rejection_reason
            self.save()
            
            # Cancel pending refund
            from .wallet import WalletTransaction
            refund = WalletTransaction.objects.filter(
                order=self.order,
                transaction_type='REFUND',
                status='PENDING',
                reason__contains=f"item: {self.product_name}"
            ).first()
            
            if refund:
                refund.status = 'CANCELLED'
                refund.reason = f"Item return rejected: {rejection_reason}"
                refund.save()
            
            print(f"❌ Item return rejected: {self.product_name} - Reason: {rejection_reason}")
            return True
            
        except Exception as e:
            print(f"Error rejecting item return: {e}")
            return False
        
    def save(self, *args, **kwargs):
        # Set default values if not provided
        if not self.product_name and self.variant and self.variant.product:
            self.product_name = self.variant.product.name
        
        if not self.variant_details and self.variant:
            self.variant_details = f"{self.variant.volume_ml}ml - {self.variant.gender}"
        
        if not self.unit_price and self.variant:
            self.unit_price = self.variant.display_price
        
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        
        if not self.product_image and self.variant and self.variant.product:
            self.product_image = self.variant.product.main_image
        
        super().save(*args, **kwargs)
    
    def cancel_item(self, reason=""):
        """Cancel individual order item and restore stock"""
        if self.is_cancelled:
            return False
        
        try:
            # Restore stock
            self.variant.stock += self.quantity
            self.variant.save()
            
            self.is_cancelled = True
            self.cancellation_reason = reason
            self.save()
            return True
            
        except Exception as e:
            print(f"Error cancelling order item: {e}")
            return False
    
    @property
    def display_price(self):
        """Formatted price for display"""
        return f"₹{self.unit_price:,.2f}"
    
    @property
    def display_total(self):
        """Formatted total price for display"""
        return f"₹{self.total_price:,.2f}"