from django.contrib import admin
from django.urls import path, include
from .views.category import category_add, category_manage, category_edit, category_success, category_filter, category_delete
from .views.product import *  # REMOVED product_delete
from .views.user_views import *
from .views.home_views import homeproduct
from .views.view_userside import *
from .views.homepage import *
from .views.admin_views import *
from .views.user_userprofile_manage import *
from .views.user_address_manage import *
from .views.cart import *
from .views.checkout import *
from .views.admin_order_management import *
from .views.payment import *
from .views.wishlist import *
from .views.view_userside import (
    home, men_products, women_products, unisex_products, 
    brands, product_search, wishlist, cart, all_products, brand_products
)
from .views.order_management import order_list, order_detail, cancel_order, cancel_order_item, return_order, download_invoice

urlpatterns = [
    # Admin routes
    path('dashboard/', admin_dashboard, name='admin_dashboard'),

    # User management
    path('user-list/', user_list, name='user_list'),
    path('users/<int:user_id>/', user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle-status/', toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
    
    # Category management
    path('categories/add/', category_add, name='category_add'),
    path('category-success/', category_success, name='category_success'),
    path('categories/', category_manage, name='category_manage'),
    path('category-filter/', category_filter, name='category_filter'),
    path('categories/<int:pk>/edit/', category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', category_delete, name='category_delete'),
    
    # Product management--admin
    path('product-add/', product_add, name='product_add'),
    path('product-list/', product_list, name='product_list'),
    path('product-edit/<int:pk>/', product_edit, name='product_edit'),
    
    # Soft delete product URLs
    path('products/<int:pk>/soft-delete/', product_soft_delete, name='product_soft_delete'),
    path('products/<int:pk>/restore/', product_restore, name='product_restore'),
    path('products/<int:pk>/permanent-delete/', product_permanent_delete, name='product_permanent_delete'),
    path('products/trash/', product_trash, name='product_trash'),
    path('products/<int:product_pk>/variants/<int:variant_pk>/edit/', variant_edit, name='variant_edit'),
path('products/<int:product_pk>/variants/<int:variant_pk>/soft-delete/', variant_soft_delete, name='variant_soft_delete'),
path('products/<int:product_pk>/variants/<int:variant_pk>/restore/', variant_restore, name='variant_restore'), 


    # Product detail page using ID
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    
    # Authentication
    path('accounts/', include('allauth.urls')),
    path('user-signup/', user_signup, name='user_signup'),
    path('user-login/', user_login, name='user_login'),
    path('user-logout/', user_logout, name='user_logout'),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("verify-otp/", verify_reset_otp, name="verify_otp"),
    path("reset-password/", reset_password, name="reset_password"),
    path("verify-signup-otp/", verify_signup_otp, name="verify_signup_otp"),
    path("resend-signup-otp/", resend_signup_otp, name="resend_signup_otp"),
    path("resend-reset-otp/", resend_reset_otp, name="resend_reset_otp"),
    
    # Main website
    path('', homepage, name='homepage'),
    path('commonhome/', homeproduct, name='commonhome'),
    path('home-product-search',home_product_search,name='home_product_search'), #for search results of home search bar
    
    # Product pages
    path('men/', men_products, name='men'),  
    path('women/', women_products, name='women'),
    path('unisex/', unisex_products, name='unisex'),
    path('brands/', brands, name='brands'),
    path('brands/<str:brand_name>/', brand_products, name='brand_products'),
    path('products/', all_products, name='all_products'),
    path('search/', product_search, name='product_search'),

    
    # Wishlist URLs
    # Add this to your urlpatterns
    path('wishlist/count/', wishlist_count, name='wishlist_count'),
    path('wishlist/get-item-id/<int:product_id>/', get_wishlist_item_id, name='get_wishlist_item_id'),
    path('wishlist/check/<int:product_id>/', check_wishlist_status, name='check_wishlist_status'),
 path('wishlist/count/', get_wishlist_count, name='get_wishlist_count'),
    path('wishlist/', wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', remove_from_wishlist, name='remove_from_wishlist'),

    # Cart URLs
    path('cart/check-variant/<int:variant_id>/', check_variant_in_cart, name='check_variant_in_cart'),
    path('cart/debug/', cart_debug, name='cart_debug'),  # Add this
    path('cart/', cart_view, name='cart'),
    path('cart/add/<int:variant_id>/', add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', clear_cart, name='clear_cart'),
    path('cart/count/', get_cart_count, name='get_cart_count'),

    # path('test-cart/', test_cart, name='test_cart'),

    # User Profile management from userside URLs
    path('profile/', user_profile, name='user_profile'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/change-email/', change_email, name='change_email'),
    path('profile/verify-email-change/', verify_email_change, name='verify_email_change'),
    path('profile/resend-email-otp/', resend_email_change_otp, name='resend_email_change_otp'),
    path('profile/change-password/', change_password, name='change_password'),

    # User Address Management URLs
    path('profile/addresses/', address_list, name='user_address_list'),
    path('profile/addresses/add/', add_address, name='user_add_address'),
    path('profile/addresses/<int:address_id>/edit/', edit_address, name='user_edit_address'),
    path('profile/addresses/<int:address_id>/delete/', delete_address, name='user_delete_address'),
    path('profile/addresses/<int:address_id>/set-default/', set_default_address, name='user_set_default_address'),
    path('profile/addresses/add-ajax/', add_address_ajax, name='user_add_address_ajax'),
    path('profile/verify-password-change/', verify_password_change, name='verify_password_change'),
    path('profile/resend-password-otp/', resend_password_change_otp, name='resend_password_change_otp'),

     # Checkout URLs
    path('checkout/', checkout_view, name='checkout'),
    path('checkout/place-order/', place_order, name='place_order'),
    path('order-success/<int:order_id>/', order_success, name='order_success'),

    # User Order Management URLs
    path('orders/', order_list, name='order_list'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('orders/<int:order_id>/cancel/', cancel_order, name='cancel_order'),
    path('order-items/<int:item_id>/cancel/', cancel_order_item, name='cancel_order_item'),
    path('orders/<int:order_id>/return/', return_order, name='return_order'),
    path('orders/<int:order_id>/invoice/', download_invoice, name='download_invoice'),

    # Keep the profile orders as a redirect to the new system
    path('profile/orders/', order_list, name='order_history'),  # Redirect to new order list

    # Admin Order Management URLs
    # path('admin/orders/', admin_order_list, name='admin_order_list'),
    # path('admin/orders/<int:order_id>/', admin_order_detail, name='admin_order_detail'),
    # path('admin/orders/<int:order_id>/update-status/', update_order_status, name='update_order_status'),

    # Admin Inventory Management URLs
    # path('admin/inventory/', admin_inventory_management, name='admin_inventory_management'),
    # path('admin/inventory/<int:variant_id>/update-stock/', update_stock, name='update_stock'),

    path('order-management/', admin_order_list, name='admin_order_list'),
    path('inventory-management/', admin_inventory_management, name='admin_inventory_management'),

    # Order Management URLs
path('order-management/', admin_order_list, name='admin_order_list'),
path('order-management/<int:order_id>/', admin_order_detail, name='admin_order_detail'),
path('order-management/<int:order_id>/update-status/', update_order_status, name='update_order_status'),

# Inventory Management URLs
path('inventory-management/', admin_inventory_management, name='admin_inventory_management'),
path('inventory-management/<int:variant_id>/update-stock/', update_stock, name='update_stock'),

 # Payment URLs
    path('payment/initiate/<int:order_id>/', initiate_payment, name='initiate_payment'),
    path('payment/success/', payment_success, name='payment_success'),
    path('payment/failed/', payment_failed, name='payment_failed'),
    path('payment/retry/<int:order_id>/', retry_payment, name='retry_payment'),
]