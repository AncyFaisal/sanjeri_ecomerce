# Register your models here.
from django.contrib import admin
# from .models.product import Product, ProductImage
from .models.user_models import CustomUser
from .models import Product, ProductVariant, Category, ProductImage
from django.contrib import admin
from .models import Coupon
from django.utils.html import format_html
# from .models import Wallet, WalletTransaction
from .models import Order


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
    

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_amount', 
                   'valid_from', 'valid_to', 'times_used', 'usage_limit', 'active')
    list_filter = ('discount_type', 'active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    readonly_fields = ('times_used', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'discount_type', 'discount_value')
        }),
        ('Conditions', {
            'fields': ('min_order_amount', 'max_discount_amount', 'usage_limit')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'active')
        }),
        ('Usage Restrictions', {
            'fields': ('single_use_per_user',)
        }),
        ('Statistics', {
            'fields': ('times_used', 'created_at', 'updated_at')
        }),
    )

# @admin.register(Wallet)
# class WalletAdmin(admin.ModelAdmin):
#     list_display = ['user', 'balance', 'created_at']
#     search_fields = ['user__username', 'user__email']
#     list_filter = ['created_at']
#     readonly_fields = ['created_at', 'updated_at']


# @admin.register(WalletTransaction)
# class WalletTransactionAdmin(admin.ModelAdmin):
#     list_display = [
#         'id', 
#         'wallet_user', 
#         'amount', 
#         'transaction_type', 
#         'status', 
#         'admin_approved',
#         'created_at'
#     ]
#     list_filter = ['transaction_type', 'status', 'admin_approved', 'created_at']
#     search_fields = ['wallet__user__username', 'order__order_number']
#     readonly_fields = ['created_at', 'updated_at']
#     actions = ['approve_refunds']
    
#     def wallet_user(self, obj):
#         return obj.wallet.user.username
#     wallet_user.short_description = 'User'
    
#     def approve_refunds(self, request, queryset):
#         # Only approve pending refund transactions
#         pending_refunds = queryset.filter(
#             transaction_type='REFUND',
#             status='PENDING'
#         )
        
#         approved_count = 0
#         for transaction in pending_refunds:
#             if transaction.mark_as_completed(approved_by=request.user):
#                 approved_count += 1
        
#         self.message_user(request, f"{approved_count} refund(s) approved and processed.")
    
#     approve_refunds.short_description = "Approve selected refunds"