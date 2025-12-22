# Register your models here.
from django.contrib import admin
# from .models.product import Product, ProductImage
from .models.user_models import CustomUser
from .models import Product, ProductVariant, Category, ProductImage

admin.site.register(CustomUser)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'brand', 'is_active', 'min_price_display', 'total_stock_display']
    list_filter = ['category', 'brand', 'is_active', 'is_featured']
    search_fields = ['name', 'sku', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    
    def min_price_display(self, obj):
        """Display minimum price from variants"""
        return f"${obj.min_price}"
    min_price_display.short_description = 'Price'
    
    def total_stock_display(self, obj):
        """Display total stock from variants"""
        return obj.total_stock
    total_stock_display.short_description = 'Stock'

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'volume_ml', 'gender', 'sku', 'price', 'stock', 'is_active']
    list_filter = ['product', 'volume_ml', 'gender', 'is_active']
    search_fields = ['product__name', 'sku']
    list_editable = ['price', 'stock', 'is_active']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_featured', 'product_count']
    list_filter = ['is_active', 'is_featured']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image', 'is_default']
    list_filter = ['product', 'is_default']
    