# models/order.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from .product import ProductVariant
from .user_models import Address
from decimal import Decimal
from datetime import timedelta 

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
    return_reason = models.TextField(blank=True, null=True)
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
        
        # AUTO-UPDATE PAYMENT STATUS FOR COD
        # This ensures payment_status updates when status changes to delivered
        if self.status == 'delivered' and self.delivered_at is None:
            self.delivered_at = timezone.now()
            
            # COD payment completes upon delivery
            if self.payment_method == 'cod' and self.payment_status == 'pending':
                self.payment_status = 'completed'
        
        # Update wallet usage flag
        if self.wallet_amount > 0 or self.wallet_amount_used > 0:
            self.wallet_used = True
            
            # If wallet covers full amount
            wallet_amount = self.wallet_amount or self.wallet_amount_used
            if wallet_amount >= self.total_amount and self.payment_status == 'pending':
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
        valid_statuses = ['pending', 'confirmed']
        
        # Payment must be pending or partially paid
        valid_payment_statuses = ['pending', 'partially_paid']
        
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
                if self.wallet_amount > 0 and self.wallet_used:
                    try:
                        from .wallet import WalletTransaction
                        # Create COMPLETED refund transaction
                        WalletTransaction.objects.create(
                            wallet=self.user.wallet,
                            amount=self.wallet_amount,
                            transaction_type='REFUND',
                            status='COMPLETED',
                            reason=f"Refund for cancelled order #{self.order_number}: {reason}",
                            order=self,
                            admin_approved=True
                        )
                        
                        # Actually refund to wallet
                        self.user.wallet.deposit(
                            self.wallet_amount,
                            reason=f"Refund for cancelled order #{self.order_number}",
                            order=self
                        )
                        
                        self.refund_to_wallet = True
                        refund_amount += self.wallet_amount
                        print(f"✅ Wallet refund of ₹{self.wallet_amount} processed")
                    except Exception as e:
                        print(f"❌ Wallet refund failed: {e}")
                
                # Refund Razorpay amount if paid online
                if self.payment_status == 'success' and self.razorpay_payment_id:
                    # Calculate online payment amount
                    online_amount = self.total_amount - self.wallet_amount
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
                            self.payment_status = 'refunded'
                            print(f"✅ Razorpay refund initiated: {refund.get('id')}")
                            
                        except Exception as e:
                            print(f"❌ Razorpay refund failed: {e}")
                            # Still mark as refunded in our system
                            self.payment_status = 'refunded'
            else:
                # User didn't pay, so no refund needed
                self.payment_status = 'cancelled'  # Set payment status to 'cancelled'
                print(f"ℹ️ Order cancelled - no refund needed (payment was pending)")
            # ========== END FIX ==========
            
            # Update order status and cancellation details
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.cancelled_at = timezone.now()
            self.refund_amount = refund_amount
            self.refund_processed_at = timezone.now() if user_paid else None  # Only set if refund was processed
            
            # Force save to ensure all fields are updated
            self.save(update_fields=[
                'status',
                'payment_status',
                'cancellation_reason',
                'cancelled_at',
                'refund_amount',
                'refund_processed_at',
                'refund_to_wallet',
                'updated_at'  # This is important for admin to see the update
            ])
            
            print(f"✅ Order #{self.order_number} cancelled successfully")
            print(f"   Status: {self.status}, Payment Status: {self.payment_status}")
            print(f"   Cancelled at: {self.cancelled_at}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error cancelling order {self.order_number}: {e}")
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
        
        try:
            # Update return status
            self.return_status = 'approved'
            self.return_approved_at = timezone.now()
            self.return_approved_by = approved_by
            self.status = 'refunded'
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
                refund_transaction.mark_as_completed(approved_by=approved_by)
                print(f"✅ Return approved and ₹{refund_transaction.amount} refunded to wallet")
            
            # If there was online payment, also initiate Razorpay refund
            if self.payment_status == 'success' and self.razorpay_payment_id:
                try:
                    import razorpay
                    from django.conf import settings
                    
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    
                    # Create refund in Razorpay
                    refund = client.payment.refund(
                        self.razorpay_payment_id,
                        {
                            'amount': int(self.total_amount * 100),
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
            
            return True
            
        except Exception as e:
            print(f"Error approving return: {e}")
            return False
    
    def reject_return(self, rejection_reason=""):
        """Admin rejects return request"""
        if self.return_status != 'requested':
            return False
        
        try:
            self.return_status = 'rejected'
            self.return_reason = f"{self.return_reason} [REJECTED: {rejection_reason}]"
            self.save()
            
            # Mark pending refund as failed
            from .wallet import WalletTransaction
            refund_transaction = WalletTransaction.objects.filter(
                order=self,
                transaction_type='REFUND',
                status='PENDING'
            ).first()
            
            if refund_transaction:
                refund_transaction.mark_as_failed()
            
            return True
            
        except Exception as e:
            print(f"Error rejecting return: {e}")
            return False
    
    def calculate_totals(self):
        """
        Calculate order totals including coupon discount.
        This should be called after order items are added.
        """
        from decimal import Decimal
        
        # Calculate subtotal from items
        self.subtotal = sum(item.total_price for item in self.items.all())
        
        # Apply coupon discount
        if self.coupon:
            self.coupon_discount = self.coupon.calculate_discount(self.subtotal)
            # Don't discount more than subtotal
            if self.coupon_discount > self.subtotal:
                self.coupon_discount = self.subtotal
        else:
            self.coupon_discount = Decimal('0')
        
        subtotal_after_coupon = self.subtotal - self.coupon_discount
        
        # Apply other discounts (existing 10% discount)
        other_discount = Decimal('0')
        if subtotal_after_coupon > Decimal('1000'):
            other_discount = subtotal_after_coupon * Decimal('0.10')
        
        # Combine all discounts
        self.discount_amount = self.coupon_discount + other_discount
        
        subtotal_after_all_discounts = self.subtotal - self.discount_amount
        
        # Calculate shipping and tax
        self.shipping_charge = Decimal('0') if subtotal_after_all_discounts > Decimal('500') else Decimal('40')
        self.tax_amount = subtotal_after_all_discounts * Decimal('0.18')
        
        # Calculate total amount
        self.total_amount = subtotal_after_all_discounts + self.shipping_charge + self.tax_amount
        
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
    
    # Store image at time of order
    product_image = models.ImageField(upload_to='order_items/', blank=True, null=True)
    
    class Meta:
        ordering = ['-id']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name} in Order #{self.order.order_number}"
    
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