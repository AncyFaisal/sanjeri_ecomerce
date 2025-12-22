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
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Order basics
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    
    # Shipping address (snapshot at time of order)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    
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
    
    # Additional info
    notes = models.TextField(blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
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
        if hasattr(self, 'delivered_at') and self.delivered_at:
            return self.delivered_at >= return_period
        return self.created_at >= return_period
    
    def calculate_totals(self):
        """Calculate order totals from order items"""
        # FIXED: Use Decimal consistently
        self.subtotal = sum(item.total_price for item in self.items.all())
        subtotal_after_discount = self.subtotal - self.discount_amount
        # Use Decimal for all values
        self.shipping_charge = Decimal('0') if self.subtotal > Decimal('500') else Decimal('40')
        self.tax_amount = self.subtotal * Decimal('0.18')
        self.total_amount = self.subtotal + self.shipping_charge + self.tax_amount - self.discount_amount
        self.save()
    
    def cancel_order(self, reason=""):
        """Cancel order and restore stock"""
        if self.can_be_cancelled:
            # Restore stock for all items
            for item in self.items.all():
                item.variant.stock += item.quantity
                item.variant.save()
            
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.cancelled_at = timezone.now()
            self.save()
            return True
        return False
    
    def return_order(self, reason):
        """Return delivered order"""
        if self.can_be_returned and reason.strip():
            # Restore stock for all items
            for item in self.items.all():
                item.variant.stock += item.quantity
                item.variant.save()
            
            self.status = 'refunded'
            self.return_reason = reason
            self.returned_at = timezone.now()
            self.save()
            return True
        return False

class OrderItem(models.Model):
    """Individual items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)  # Snapshot of product name
    variant_details = models.CharField(max_length=100)  # Snapshot of variant details
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # NEW: Individual item cancellation
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # Store image at time of order
    product_image = models.ImageField(upload_to='order_items/', blank=True, null=True)
    
    class Meta:
        ordering = ['-id']
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name} in Order #{self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.product_name:
            self.product_name = self.variant.product.name
        if not self.variant_details:
            self.variant_details = f"{self.variant.volume_ml}ml - {self.variant.gender}"
        if not self.unit_price:
            self.unit_price = self.variant.display_price
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        if not self.product_image and self.variant.product.main_image:
            self.product_image = self.variant.product.main_image
        
        super().save(*args, **kwargs)
    
    def cancel_item(self, reason=""):
        """Cancel individual order item and restore stock"""
        if not self.is_cancelled:
            # Restore stock
            self.variant.stock += self.quantity
            self.variant.save()
            
            self.is_cancelled = True
            self.cancellation_reason = reason
            self.save()
            return True
        return False