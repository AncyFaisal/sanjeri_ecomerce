# sanjeri_app/models/referral.py
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

class ReferralCoupon(models.Model):
    """Coupon generated for referrer when their referral signs up"""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    # Link to the referrer who earned this coupon
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='earned_referral_coupons'
    )
    
    # Link to the new user who was referred
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='used_referral_link'
    )
    
    # Coupon details
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='fixed')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=100)  # ₹100 default
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    
    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    
    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='used_referral_coupons'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.referrer.username}"
    
    def generate_code(self):
        """Generate unique coupon code"""
        prefix = "REF"
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"{prefix}{unique_id}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.valid_to:
            # Default validity: 30 days from now
            self.valid_to = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if coupon is still valid"""
        now = timezone.now()
        return not self.is_used and self.valid_from <= now <= self.valid_to
    
    def mark_as_used(self, user):
        """Mark coupon as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.used_by = user
        self.save()
        