# sanjeri_app/views/wishlist.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ..models import Wishlist, WishlistItem, Product

@login_required
def wishlist_view(request):
    """Display the user's wishlist"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_items = wishlist.items.select_related('product').all()
        
        context = {
            'wishlist': wishlist,
            'wishlist_items': wishlist_items,
        }
        return render(request, 'wishlist.html', context)
        
    except Wishlist.DoesNotExist:
        # Create empty wishlist if it doesn't exist
        wishlist = Wishlist.objects.create(user=request.user)
        context = {
            'wishlist': wishlist,
            'wishlist_items': [],
        }
        return render(request, 'wishlist.html', context)

@login_required
@require_POST
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
        
        # Get or create wishlist
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        # Check if item already exists in wishlist
        wishlist_item, item_created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product
        )
        
        if item_created:
            messages.success(request, "Product added to wishlist!")
        else:
            messages.info(request, "Product is already in your wishlist.")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Product added to wishlist successfully!',
                'wishlist_total_items': wishlist.total_items
            })
        
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, f"Error adding product to wishlist: {str(e)}")
        return redirect('product_detail', product_id=product_id)

@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    """Remove item from wishlist"""
    try:
        wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
        product_name = wishlist_item.product.name
        wishlist_item.delete()
        messages.success(request, f"'{product_name}' removed from wishlist.")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            wishlist = Wishlist.objects.get(user=request.user)
            return JsonResponse({
                'success': True,
                'message': 'Item removed from wishlist',
                'wishlist_total_items': wishlist.total_items
            })
        
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, f"Error removing item from wishlist: {str(e)}")
        return redirect('wishlist')