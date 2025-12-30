# # your_project/your_app/context_processors.py
from django.db.models import Sum
from .models import Cart, Wishlist

def cart_and_wishlist_context(request):
    """
    Consolidated context processor for both cart and wishlist
    """
    context = {}
    
    if request.user.is_authenticated:
        # Cart count
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_item_count'] = cart.total_items
            context['cart_items_count'] = cart.total_items
        except Cart.DoesNotExist:
            context['cart_item_count'] = 0
            context['cart_items_count'] = 0
        
        # Wishlist count - SIMPLIFIED FIXED VERSION
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            # Use the total_items property we just added
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

# def cart_context(request):
#     context = {}
#     if request.user.is_authenticated:
#         try:
#             cart = Cart.objects.get(user=request.user)
#             context['cart_item_count'] = cart.total_items
#         except Cart.DoesNotExist:
#             context['cart_item_count'] = 0
        
#         try:
#             wishlist = Wishlist.objects.get(user=request.user)
#             context['wishlist_item_count'] = wishlist.total_items
#         except Wishlist.DoesNotExist:
#             context['wishlist_item_count'] = 0
#     else:
#         context['cart_item_count'] = 0
#         context['wishlist_item_count'] = 0
#     return context

# def cart_context(request):
#     cart_count = 0
#     if request.user.is_authenticated:
#         try:
#             cart = Cart.objects.get(user=request.user)
#             cart_count = cart.total_items
#         except Cart.DoesNotExist:
#             pass
#     return {'cart_item_count': cart_count}


# def wishlist_context(request):
#     """Add wishlist count to all templates"""
#     context = {}
#     if request.user.is_authenticated:
#         try:
#             wishlist = Wishlist.objects.get(user=request.user)
#             wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
#             context['wishlist_count'] = wishlist_count
#         except Wishlist.DoesNotExist:
#             context['wishlist_count'] = 0
#     else:
#         context['wishlist_count'] = 0
#     return context