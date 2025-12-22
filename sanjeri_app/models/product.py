# # models/product.py

# models/product.py
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from .category import Category
from django.db.models import Q, UniqueConstraint


class ProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        return super().get_queryset()
    
    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)

class ProductVariantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        return super().get_queryset()
    
    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)
    

class Product(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"), 
        ("Unisex", "Unisex")
    ]
    
    # Basic Info (common to all variants)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(null=True, blank=True)
    sku = models.CharField(max_length=50)  # KEPT AS sku, NOT unique
    
    # Common product description
    description = models.TextField()
    main_image = models.ImageField(upload_to="products/main/", blank=True, null=True)
    
    # Brand & Perfume-specific (common to all variants)
    brand = models.CharField(max_length=100, blank=True, null=True)
    fragrance_type = models.CharField(max_length=50, blank=True, null=True)
    occasion = models.CharField(max_length=50, blank=True, null=True)
    
    # SEO & Marketing
    is_featured = models.BooleanField(default=False)
    is_best_selling = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, default=0.0)
    rating_count = models.PositiveIntegerField(default=0)
    
    # System
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = ProductManager()

    def save(self, *args, **kwargs):
        if self.is_deleted is None:
            self.is_deleted = False

        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug, is_deleted=False).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    # Helper properties for common variant operations
    @property
    def min_price(self):
        """Get the minimum price among all variants"""
        from django.db.models import Min
        return self.variants.aggregate(min_price=Min('price'))['min_price'] or 0

    @property
    def max_price(self):
        """Get the maximum price among all variants"""
        from django.db.models import Max
        return self.variants.aggregate(max_price=Max('price'))['max_price'] or 0

    @property
    def total_stock(self):
        """Get total stock across all variants"""
        return self.variants.aggregate(total_stock=models.Sum('stock'))['total_stock'] or 0

    @property
    def available_volumes(self):
        """Get list of available volumes"""
        return list(self.variants.filter(is_active=True).values_list('volume_ml', flat=True).distinct().order_by('volume_ml'))

    @property
    def available_genders(self):
        """Get list of available genders"""
        return list(self.variants.filter(is_active=True).values_list('gender', flat=True).distinct())

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["slug"],
                condition=Q(is_deleted=False),
                name="unique_slug_not_deleted"
            ),
        ]


class ProductVariant(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"), 
        ("Unisex", "Unisex")
    ]
    
    # Basic product info (common to all variants)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    
    # Variant-specific fields
    volume_ml = models.PositiveIntegerField(help_text="Volume in ml (e.g., 50, 100)")
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    
    # Variant-specific pricing and inventory
    sku = models.CharField(max_length=100, unique=True)  # Unique SKU for this variant
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    
    # Variant-specific image (optional)
    variant_image = models.ImageField(upload_to="products/variants/", blank=True, null=True)
    
    # System fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = ProductVariantManager()
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['product', 'volume_ml', 'gender'],
                condition=Q(is_deleted=False),
                name='unique_variant_combination'
            )
        ]
        ordering = ['volume_ml', 'gender']
    
    def __str__(self):
        return f"{self.product.name} - {self.volume_ml}ml - {self.gender} ({self.sku})"
    
    def save(self, *args, **kwargs):
        # Generate SKU if not provided
        if not self.sku:
            base_sku = f"{self.product.sku}-{self.volume_ml}-{self.gender[:3].upper()}"
            
            # Ensure uniqueness
            counter = 1
            sku = base_sku
            while ProductVariant.objects.filter(sku=sku).exclude(pk=self.pk).exists():
                sku = f"{base_sku}-{counter}"
                counter += 1
                
            self.sku = sku
        super().save(*args, **kwargs)
    
    @property
    def display_price(self):
        return self.discount_price if self.discount_price else self.price
    
    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def min_price(self):
        """Get minimum price from active variants"""
        variants = self.variants.filter(is_active=True)
        if variants.exists():
            return min(variant.price for variant in variants)
        return 0
    
    @property
    def max_price(self):
        """Get maximum price from active variants"""
        variants = self.variants.filter(is_active=True)
        if variants.exists():
            return max(variant.price for variant in variants)
        return 0
    
    @property
    def total_stock(self):
        """Get total stock from active variants"""
        variants = self.variants.filter(is_active=True)
        return sum(variant.stock for variant in variants)
    
    @property
    def main_image(self):
        """Get main product image"""
        main_img = self.images.filter(is_default=True).first()
        if main_img:
            return main_img.image
        first_img = self.images.first()
        if first_img:
            return first_img.image
        return None

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=150, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"

