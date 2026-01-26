# context_processors.py
from django.db.models import Sum
from .models import Cart, Wishlist
from django.contrib.auth import get_user_model

User = get_user_model()

# def wallet_balance(request):
#     if request.user.is_authenticated:
#         try:
#             # Import inside the function to avoid circular imports
#             from sanjeri_app.models.wallet import Wallet
#             wallet = Wallet.objects.get(user=request.user)
#             return {'wallet_balance': wallet.balance}
#         except Exception as e:
#             # Log the error for debugging
#             print(f"Wallet context processor error: {e}")
#             return {'wallet_balance': 0}
#     return {'wallet_balance': 0}

def cart_and_wishlist_context(request):
    """
    Consolidated context processor for both cart and wishlist
    """
    context = {}
    
    if request.user.is_authenticated:
        # Import inside function
        from sanjeri_app.models.cart import Cart
        from sanjeri_app.models.wishlist import Wishlist
        
        # Cart count
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_item_count'] = cart.total_items
            context['cart_items_count'] = cart.total_items
        except Cart.DoesNotExist:
            context['cart_item_count'] = 0
            context['cart_items_count'] = 0
        
        # Wishlist count
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            context['wishlist_count'] = wishlist.total_items
            context['wishlist_items_count'] = wishlist.total_items
        except Wishlist.DoesNotExist:
            context['wishlist_count'] = 0
            context['wishlist_items_count'] = 0
    else:
        context['cart_item_count'] = 0
        context['cart_items_count'] = 0
        context['wishlist_count'] = 0
        context['wishlist_items_count'] = 0
    
    return context

