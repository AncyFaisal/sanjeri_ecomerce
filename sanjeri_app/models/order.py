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
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_paid', 'Partially Paid'),
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
    
    # NEW: Cancellation and Return fields
    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)  # ADD THIS FIELD
    
    # Payment gateway fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Wallet fields
    wallet_used = models.BooleanField(default=False)
    wallet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_to_wallet = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_processed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
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
        
        # Update payment status based on wallet usage
        if self.wallet_amount > 0:
            self.wallet_used = True
            
            # If wallet covers full amount, mark as partially paid
            if self.wallet_amount >= self.total_amount and self.payment_status == 'pending':
                self.payment_status = 'partially_paid'
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        timestamp = timezone.now().strftime('%Y%m%d')
        last_order = Order.objects.filter(order_number__startswith=f'ORD{timestamp}').order_by('-id').first()
        
        if last_order:
            last_num = int(last_order.order_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
            
        return f"ORD{timestamp}{new_num:04d}"
    
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
        if self.payment_status == 'completed':
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
        if self.payment_status == 'completed':
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
        if self.payment_status == 'completed':
            return False
        
        self.payment_status = 'completed'
        self.status = 'confirmed'
        
        if razorpay_payment_id:
            self.razorpay_payment_id = razorpay_payment_id
        
        if razorpay_signature:
            self.razorpay_signature = razorpay_signature
        
        self.save()
        return True
    
    def update_payment_info(self, razorpay_order_id):
        """Update Razorpay order ID for tracking"""
        self.razorpay_order_id = razorpay_order_id
        self.save()
    
    def cancel_order(self, reason=""):
        """Cancel order and handle wallet refund"""
        if not self.can_be_cancelled:
            return False
        
        try:
            # Restore stock for all items
            for item in self.items.all():
                item.variant.stock += item.quantity
                item.variant.save()
            
            # Handle wallet refund if wallet was used
            if self.wallet_amount > 0 and self.wallet_used:
                from .wallet import WalletTransaction
                
                # Create refund transaction
                WalletTransaction.objects.create(
                    wallet=self.user.wallet,
                    amount=self.wallet_amount,
                    transaction_type='REFUND',
                    status='COMPLETED',
                    reason=f"Refund for cancelled order #{self.order_number}: {reason}",
                    order=self,
                    admin_approved=True
                )
                
                # Update wallet balance
                self.user.wallet.deposit(
                    self.wallet_amount,
                    reason=f"Refund for cancelled order #{self.order_number}",
                    order=self
                )
                
                self.refund_to_wallet = True
                self.refund_amount = self.wallet_amount
                self.refund_processed_at = timezone.now()
            
            # Update order status
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.cancelled_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            print(f"Error cancelling order {self.order_number}: {e}")
            return False
    
    def request_return(self, reason):
        """Request return for delivered order"""
        if not self.can_be_returned:
            return False
        
        if not reason or not reason.strip():
            return False
        
        self.status = 'return_requested'
        self.return_reason = reason
        self.save()
        
        # Create pending refund transaction
        try:
            from .wallet import WalletTransaction
            WalletTransaction.objects.create(
                wallet=self.user.wallet,
                amount=self.total_amount,
                transaction_type='REFUND',
                status='PENDING',
                reason=f"Return request: {reason}",
                order=self,
                admin_approved=False
            )
        except Exception as e:
            print(f"Error creating refund transaction: {e}")
        
        return True
    
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