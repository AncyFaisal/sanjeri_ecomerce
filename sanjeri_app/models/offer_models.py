# sanjeri_app/models/offer_models.py
from django.db import models
from django.utils import timezone
from decimal import Decimal

class BaseOffer(models.Model):
    """Abstract base class for all offers - SIMPLIFIED AND CONSISTENT"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # DISCOUNT FIELDS - Use either percentage OR fixed amount
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, 
                                              help_text="Percentage discount (e.g., 20 for 20%)")
    discount_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                         help_text="Fixed amount discount in ₹")
    
                                                
    
    # CONDITIONS
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                              help_text="Minimum order amount required")
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Maximum discount amount (for percentage offers)")
    
    # VALIDITY
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # USAGE TRACKING
    usage_limit = models.IntegerField(default=0, help_text="0 = unlimited")
    times_used = models.IntegerField(default=0)
    
    # SYSTEM
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def calculate_discount(self, price):
        """
        Calculate discount for a single item price
        Returns (discount_amount, discounted_price)
        """
        discount = Decimal('0')
        
        if self.discount_percentage > 0:
            # Percentage discount
            discount = price * (self.discount_percentage / 100)
            # Apply max discount cap if set
            if self.max_discount and discount > self.max_discount:
                discount = self.max_discount
        elif self.discount_fixed > 0:
            # Fixed amount discount
            discount = self.discount_fixed
            # Can't discount more than the price
            if discount > price:
                discount = price
        
        discounted_price = price - discount
        return discount, discounted_price

    def is_valid(self, cart_value):
        """Check if offer is valid for given cart value"""
        now = timezone.now()
        
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            cart_value >= self.min_purchase_amount and
            (self.usage_limit == 0 or self.times_used < self.usage_limit)
        )

    def increment_usage(self):
        """Increment usage count"""
        if self.usage_limit > 0:
            self.times_used += 1
            self.save(update_fields=['times_used'])


class ProductOffer(BaseOffer):
    """Offer specific to a product - can apply to multiple products"""
    products = models.ManyToManyField('Product', related_name='product_offers', blank=True)
    apply_to_all_variants = models.BooleanField(default=True,help_text="Apply discount to all variants of the product")

    class Meta:
        app_label = 'sanjeri_app'
        verbose_name = 'Product Offer'
        verbose_name_plural = 'Product Offers'
        
    def __str__(self):
        product_count = self.products.count()
        if product_count == 1:
            return f"{self.name} - {self.products.first().name}"
        elif product_count > 1:
            return f"{self.name} - {product_count} products"
        return self.name


class CategoryOffer(BaseOffer):
    """Offer for entire category"""
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='category_offers')
    

    class Meta:
        app_label = 'sanjeri_app'
        verbose_name = 'Category Offer'
        verbose_name_plural = 'Category Offers'

    def __str__(self):
        return f"{self.name} - {self.category.name}"


class OfferApplication(models.Model):
    """Track which offers were applied to which order items"""
    OFFER_TYPES = [
        ('product', 'Product Offer'),
        ('category', 'Category Offer'),
    ]
    
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPES)
    product_offer = models.ForeignKey(
        'ProductOffer', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='applications'
    )
    category_offer = models.ForeignKey(
        'CategoryOffer', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='applications'
    )
    order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE, 
        related_name='offer_applications'
    )
    order_item = models.ForeignKey(
        'OrderItem', 
        on_delete=models.CASCADE,
        related_name='offer_applications'
    )
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    
    # Price breakdown
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offer_name = models.CharField(max_length=200, blank=True, help_text="Snapshot of offer name at time of application")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'sanjeri_app'
        verbose_name = 'Offer Application'
        verbose_name_plural = 'Offer Applications'
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        # Capture offer name at time of application
        if not self.offer_name:
            if self.product_offer:
                self.offer_name = self.product_offer.name
            elif self.category_offer:
                self.offer_name = self.category_offer.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.offer_name} on {self.product.name} for Order #{self.order.order_number}"