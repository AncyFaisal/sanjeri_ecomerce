# admin.py

# Register your models here.
from django.contrib import admin
# from .models.product import Product, ProductImage
from .models.user_models import CustomUser
from .models import Product, ProductVariant, Category, ProductImage
from django.contrib import admin
from .models import Coupon
from django.utils.html import format_html
# from .models import Wallet, WalletTransaction
from .models import Order, OrderItem
from django.urls import reverse
from .models.wallet import Wallet, WalletTransaction
from .models.offer_models import ProductOffer, CategoryOffer, OfferApplication

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

    # admin.py - Update OrderAdmin

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 
        'user', 
        'total_amount', 
        'payment_status', 
        'status',
        'return_status_display',
        'return_actions',
        'created_at',    
        'payment_method',
        'cancelled_at',    # This shows when cancelled
        'updated_at'
    ]
    list_filter = [
        'payment_status', 
        'status', 
        'return_status',
        'payment_method',
        'created_at'
    ]
    search_fields = [
        'order_number', 
        'user__email', 
        'user__username',
        'razorpay_order_id',
        'razorpay_payment_id'
    ]
    readonly_fields = [
        'order_number', 
        'created_at', 
        'updated_at',
        'return_requested_at',
        'return_approved_at',
        'cancelled_at',
        'returned_at'
    ]
    actions = ['approve_selected_returns', 'reject_selected_returns','recalculate_order_totals']
    
    # FIXED: Removed duplicate 'payment_status' from 'Order Information' fieldset
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')  # Removed 'payment_status' from here
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'total_amount', 
                      'wallet_amount', 'wallet_used', 'razorpay_order_id',
                      'razorpay_payment_id')
        }),
        
        ('Return & Cancellation', {
            'fields': ('return_status', 'return_reason', 'return_requested_at',
                      'return_approved_at', 'return_approved_by',
                      'cancellation_reason', 'cancelled_at',
                      'refund_amount', 'refund_processed_at')
        }),
        ('Address & Shipping', {
            'fields': ('shipping_address', 'shipping_charge', 'tracking_number',
                      'delivered_at')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'discount_amount', 'coupon_discount', 'tax_amount')
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Override save_model to recalculate totals when admin edits an order
        """
        # Save the order first
        super().save_model(request, obj, form, change)
        
        # If this is an existing order being changed (not a new one)
        if change:
            # Recalculate totals after admin edits
            obj.calculate_totals()
    
    def recalculate_order_totals(self, request, queryset):
        """Admin action to recalculate totals for selected orders"""
        recalculated_count = 0
        for order in queryset:
            old_total = order.total_amount
            order.calculate_totals()
            new_total = order.total_amount
            recalculated_count += 1
            self.message_user(
                request, 
                f"Order #{order.order_number}: ₹{old_total} → ₹{new_total}",
                level='INFO'
            )
        
        self.message_user(
            request, 
            f"Recalculated totals for {recalculated_count} order(s)."
        )

    recalculate_order_totals.short_description = "Recalculate totals for selected orders"

    def return_status_display(self, obj):
        colors = {
            'not_requested': 'secondary',
            'requested': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'completed': 'info'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.return_status, 'secondary'),
            obj.get_return_status_display()
        )
    return_status_display.short_description = 'Return Status'
    
    def return_actions(self, obj):
        if obj.return_status == 'requested':
            approve_url = reverse('admin:approve_return', args=[obj.id])
            reject_url = reverse('admin:reject_return', args=[obj.id])
            return format_html(
                '<a href="{}" class="btn btn-sm btn-success me-1">Approve</a>'
                '<a href="{}" class="btn btn-sm btn-danger">Reject</a>',
                approve_url, reject_url
            )
        return "-"
    return_actions.short_description = 'Actions'
    
    def approve_selected_returns(self, request, queryset):
        """Admin action to approve selected returns"""
        approved_count = 0
        for order in queryset.filter(return_status='requested'):
            if order.approve_return(approved_by=request.user):
                approved_count += 1
        
        self.message_user(
            request, 
            f"{approved_count} return request(s) approved and refunds processed."
        )
    
    approve_selected_returns.short_description = "Approve selected returns"
    
    def reject_selected_returns(self, request, queryset):
        """Admin action to reject selected returns"""
        rejected_count = 0
        for order in queryset.filter(return_status='requested'):
            if order.reject_return(rejection_reason="Bulk rejection"):
                rejected_count += 1
        
        self.message_user(
            request, 
            f"{rejected_count} return request(s) rejected."
        )
    
    reject_selected_returns.short_description = "Reject selected returns"
    
    # Custom admin views for return actions
    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path('<int:order_id>/approve-return/',
                 self.admin_site.admin_view(self.approve_return_view),
                 name='approve_return'),
            path('<int:order_id>/reject-return/',
                 self.admin_site.admin_view(self.reject_return_view),
                 name='reject_return'),
        ]
        return custom_urls + urls
    
    def approve_return_view(self, request, order_id):
        """View to approve a return"""
        from django.shortcuts import redirect
        from django.contrib import messages
        
        order = Order.objects.get(id=order_id)
        if order.approve_return(approved_by=request.user):
            messages.success(request, f"Return for order #{order.order_number} approved and refund processed.")
        else:
            messages.error(request, f"Failed to approve return for order #{order.order_number}.")
        
        return redirect(reverse('admin:sanjeri_app_order_changelist'))
    
    def reject_return_view(self, request, order_id):
        """View to reject a return"""
        from django.shortcuts import redirect
        from django.contrib import messages
        
        order = Order.objects.get(id=order_id)
        rejection_reason = request.POST.get('rejection_reason', 'Not specified')
        
        if order.reject_return(rejection_reason=rejection_reason):
            messages.success(request, f"Return for order #{order.order_number} rejected.")
        else:
            messages.error(request, f"Failed to reject return for order #{order.order_number}.")
        
        return redirect(reverse('admin:sanjeri_app_order_changelist'))

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'available_balance', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def available_balance(self, obj):
        return obj.available_balance
    available_balance.short_description = 'Available Balance'

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'wallet_user', 
        'amount_display', 
        'transaction_type', 
        'status', 
        'admin_approved',
        'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'admin_approved', 'created_at']
    search_fields = ['wallet__user__username', 'order__order_number', 'reason']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_refunds', 'mark_as_completed', 'mark_as_failed']
    
    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'User'
    
    def amount_display(self, obj):
        return obj.display_amount
    amount_display.short_description = 'Amount'
    
    def approve_refunds(self, request, queryset):
        """Approve selected refund transactions"""
        pending_refunds = queryset.filter(
            transaction_type='REFUND',
            status='PENDING'
        )
        
        approved_count = 0
        for transaction in pending_refunds:
            if transaction.mark_as_completed(approved_by=request.user):
                approved_count += 1
        
        self.message_user(request, f"{approved_count} refund(s) approved and processed.")
    
    approve_refunds.short_description = "Approve selected refunds"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected transactions as completed"""
        updated_count = queryset.update(status='COMPLETED')
        self.message_user(request, f"{updated_count} transaction(s) marked as completed.")
    
    mark_as_completed.short_description = "Mark as completed"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected transactions as failed"""
        updated_count = queryset.update(status='FAILED')
        self.message_user(request, f"{updated_count} transaction(s) marked as failed.")
    
    mark_as_failed.short_description = "Mark as failed"


# admin.py - Add these after your existing imports


@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'display_products', 
        'discount_percentage', 
        'discount_fixed',  # Changed from discount_amount
        'valid_from', 
        'valid_to', 
        'is_active',       # Changed from active
        'times_used'
    ]
    list_filter = ['is_active', 'valid_from', 'valid_to']  # Removed 'product' from filters
    search_fields = ['name', 'products__name']  # Changed 'product__name' to 'products__name'
    filter_horizontal = ['products']  # Add this for better ManyToMany UI
    
    def display_products(self, obj):
        """Display first 3 products in the offer"""
        products = obj.products.all()[:3]
        if products:
            return ", ".join([p.name for p in products]) + ("..." if obj.products.count() > 3 else "")
        return "-"
    display_products.short_description = 'Products'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'products')  # Changed 'product' to 'products'
        }),
        ('Discount Details', {
            'fields': ('discount_percentage', 'discount_fixed', 'max_discount')
        }),
        ('Conditions', {
            'fields': ('min_purchase_amount', 'min_cart_value', 'usage_limit')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to',  'is_active')
        }),
    )


@admin.register(CategoryOffer)
class CategoryOfferAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'discount_percentage', 'discount_fixed',
                   'valid_from', 'valid_to', 'is_active', 'times_used']  # 'category' is fine (ForeignKey)
    list_filter = ['is_active', 'category', 'valid_from', 'valid_to']
    search_fields = ['name', 'category__name']
    # No filter_horizontal needed for ForeignKey
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')  # 'category' is fine
        }),
        ('Discount Details', {
            'fields': ('discount_percentage', 'discount_fixed',  'max_discount')
        }),
        ('Conditions', {
            'fields': ('min_purchase_amount', 'min_cart_value', 'usage_limit')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'is_active')
        }),
    )

@admin.register(OfferApplication)
class OfferApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'offer_type', 'discount_amount']
    list_filter = ['offer_type']
    search_fields = ['order__order_number', 'product__name']
    readonly_fields = ['offer_name', 'original_price', 'discount_amount', 'final_price'] 



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