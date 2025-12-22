# # your_project/your_app/context_processors.py
from django.db.models import Sum
from .models import Cart, Wishlist

from .models import Cart, Wishlist

def cart_and_wishlist_context(request):
    context = {}
    
    if request.user.is_authenticated:
        # Cart count - using your existing property
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_items_count'] = cart.total_items
        except Cart.DoesNotExist:
            context['cart_items_count'] = 0
        
        # Wishlist count - fixed version
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            
            # Check if wishlist has total_items property
            if hasattr(wishlist, 'total_items'):
                context['wishlist_items_count'] = wishlist.total_items
            # Check if wishlist.items is a QuerySet (has count method)
            elif hasattr(wishlist, 'items') and hasattr(wishlist.items, 'count'):
                context['wishlist_items_count'] = wishlist.items.count()
            # Check if wishlist.items is a list
            elif hasattr(wishlist, 'items') and isinstance(wishlist.items, list):
                context['wishlist_items_count'] = len(wishlist.items)
            # Check for default related name
            elif hasattr(wishlist, 'wishlistitem_set'):
                context['wishlist_items_count'] = wishlist.wishlistitem_set.count()
            else:
                context['wishlist_items_count'] = 0
                
        except Wishlist.DoesNotExist:
            context['wishlist_items_count'] = 0
    else:
        context['cart_items_count'] = 0
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

def cart_context(request):
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    return {'cart_item_count': cart_count}