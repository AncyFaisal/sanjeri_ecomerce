# sanjeri_app/models/coupon.py
from django.db import models
from django.utils import timezone
from django.conf import settings
# Use string reference to avoid circular import
from django.db.models import Q
from decimal import Decimal

  #CUSTOM MANAGER FOR COUPONS
class CouponManager(models.Manager):
    """Custom manager for Coupon model with soft delete support"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        return super().get_queryset()
    
    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)
    
    def active(self):
        return self.get_queryset().filter(active=True, is_deleted=False)
    
    def expired(self):
        return self.get_queryset().filter(valid_to__lt=timezone.now(), is_deleted=False)
    

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    single_use_per_user = models.BooleanField(default=True)
    
    #  SOFT DELETE
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='deleted_coupons')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use custom manager
    objects = CouponManager()
    
    class Meta:
        ordering = ['-created_at']

    
    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percentage' else '₹'})"
    
    def is_valid(self, user=None, order_amount=0):
        """Check if coupon is valid for use"""
        from django.utils import timezone
        now = timezone.now()
        
        # Basic checks
        if not self.active:
            return False, "Coupon is not active"
        
        # SOFT DELETE CHECK
        if self.is_deleted:
            return False, "Coupon has been deleted"
        
        if not (self.valid_from <= now <= self.valid_to):
            return False, "Coupon is not valid at this time"
        
        if self.times_used >= self.usage_limit:
            return False, "Coupon usage limit reached"
        
        # Minimum order amount check
        if order_amount < self.min_order_amount:
            return False, f"Minimum order amount of ₹{self.min_order_amount} required"
        
        # Single use per user check
        if self.single_use_per_user and user and user.is_authenticated:
            # Import here to avoid circular import
            from .order import Order
            used_count = Order.objects.filter(
                user=user,
                coupon=self,
                status__in=['confirmed', 'shipped', 'delivered', 'out_for_delivery']
            ).count()
            if used_count > 0:
                return False, "Coupon already used"
        
        return True, "Valid coupon"
        
       
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount for given order amount"""
        from decimal import Decimal
        
        if self.discount_type == 'percentage':
            discount = (order_amount * self.discount_value) / 100
            if self.max_discount_amount and discount > self.max_discount_amount:
                discount = self.max_discount_amount
        else:
            discount = self.discount_value
            if discount > order_amount:
                discount = order_amount
        
        return discount
    
    def increment_usage(self):
        """Increment usage count"""
        self.times_used += 1
        self.save()

    def soft_delete(self, user=None):
        """Soft delete the coupon"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        """Restore soft deleted coupon"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    def permanent_delete(self):
        """Permanently delete the coupon"""
        super().delete()
    
    @property
    def is_expired(self):
        """Check if coupon is expired"""
        return timezone.now() > self.valid_to
    
    @property
    def days_since_deleted(self):
        """Get days since coupon was deleted"""
        if self.deleted_at:
            return (timezone.now() - self.deleted_at).days
        return 0
    
    @property
    def can_be_permanently_deleted(self):
        """Check if coupon can be permanently deleted (after 30 days)"""
        return self.days_since_deleted >= 30
    
    @property
    def get_usage_percentage(self):
        """Get percentage of usage limit used"""
        if self.usage_limit == 0:
            return 0
        return round((self.times_used / self.usage_limit) * 100, 1)
    
    
    # MODIFY QUERYSET MANAGER
    class Meta:
        # Add custom manager for active coupons
        pass

  