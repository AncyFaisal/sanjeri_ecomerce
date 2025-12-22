from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from .product import Product, ProductVariant
from .wishlist import Wishlist, WishlistItem

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def can_checkout(self):
        """Check if all items in cart are available for checkout"""
        return all(item.is_available for item in self.items.all()) and self.total_items > 0

    def clear_cart(self):
        """Clear all items from cart"""
        self.items.all().delete()

    def get_available_items(self):
        """Get only items that are available for checkout"""
        return [item for item in self.items.all() if item.is_available]

    def get_unavailable_items(self):
        """Get items that cannot be checked out"""
        return [item for item in self.items.all() if not item.is_available]

class CartItem(models.Model):
    MAX_QUANTITY = 10  # Maximum quantity per product
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'variant']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.quantity} x {self.variant} in {self.cart}"

    @property
    def product(self):
        """Get the product through the variant"""
        return self.variant.product

    @property
    def total_price(self):
        return self.quantity * self.variant.display_price

    @property
    def is_available(self):
        """Check if this item can be added to cart based on business rules"""
        # Check if product is active and not deleted
        if not self.product.is_active or self.product.is_deleted:
            return False
        
        # Check if product category is active
        if not self.product.category.is_active or self.product.category.is_deleted:
            return False
        
        # Check if variant is active
        if not self.variant.is_active:
            return False
        
        # Check stock availability
        if self.variant.stock < self.quantity:
            return False
        
        # Check maximum quantity
        if self.quantity > self.MAX_QUANTITY:
            return False
        
        return True

    @property
    def is_out_of_stock(self):
        return self.variant.stock == 0

    @property
    def has_low_stock(self):
        return 0 < self.variant.stock < self.quantity

    @property
    def can_increment(self):
        """Check if quantity can be increased"""
        return (self.quantity < self.MAX_QUANTITY and 
                self.variant.stock > self.quantity and
                self.is_available)

    @property
    def can_decrement(self):
        """Check if quantity can be decreased"""
        return self.quantity > 1

    @property
    def max_allowed_quantity(self):
        """Get maximum allowed quantity considering stock and limits"""
        return min(self.variant.stock, self.MAX_QUANTITY)

    def clean(self):
        """Validate before saving"""
        # Check product availability
        if not self.product.is_active or self.product.is_deleted:
            raise ValidationError("Product is not available")
        
        # Check category availability
        if not self.product.category.is_active or self.product.category.is_deleted:
            raise ValidationError("Product category is not available")
        
        # Check variant availability
        if not self.variant.is_active:
            raise ValidationError("Product variant is not available")
        
        # Check stock availability
        if self.variant.stock < self.quantity:
            raise ValidationError(f"Only {self.variant.stock} items available in stock")
        
        # Check maximum quantity limit
        if self.quantity > self.MAX_QUANTITY:
            raise ValidationError(f"Cannot add more than {self.MAX_QUANTITY} items of this product")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def remove_from_wishlist_if_exists(self, user):
        """Remove this product from user's wishlist"""
        try:
            wishlist_item = WishlistItem.objects.filter(
                wishlist__user=user,
                product=self.product
            ).first()
            if wishlist_item:
                wishlist_item.delete()
                return True
        except Exception:
            pass
        return False