from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from ..models import Wishlist, WishlistItem, Product

@login_required
def wishlist_view(request):
    """Display the user's wishlist"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product')
        
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
@require_http_methods(["POST"])
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
        
        wishlist_items_count = WishlistItem.objects.filter(wishlist=wishlist).count()
        
        if item_created:
            message = "Product added to wishlist!"
            success = True
        else:
            message = "Product is already in your wishlist."
            success = False
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': success,
                'message': message,
                'wishlist_count': wishlist_items_count
            })
        
        if item_created:
            messages.success(request, message)
        else:
            messages.info(request, message)
        
        # Return to previous page or product detail
        referer = request.META.get('HTTP_REFERER', 'homepage')
        return redirect(referer)
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f"Error: {str(e)}"
            })
        messages.error(request, f"Error adding product to wishlist: {str(e)}")
        return redirect('product_detail', product_id=product_id)

@login_required
@require_http_methods(["POST", "DELETE"])
def remove_from_wishlist(request, item_id):
    """Remove item from wishlist"""
    try:
        wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
        product_name = wishlist_item.product.name
        wishlist = wishlist_item.wishlist
        wishlist_item.delete()
        
        # Get updated count
        wishlist_items_count = WishlistItem.objects.filter(wishlist=wishlist).count()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"'{product_name}' removed from wishlist.",
                'wishlist_count': wishlist_items_count
            })
        
        messages.success(request, f"'{product_name}' removed from wishlist.")
        return redirect('wishlist')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f"Error: {str(e)}"
            })
        messages.error(request, f"Error removing item from wishlist: {str(e)}")
        return redirect('wishlist')

@login_required
def get_wishlist_count(request):
    """Get wishlist item count for AJAX requests"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        count = WishlistItem.objects.filter(wishlist=wishlist).count()
        return JsonResponse({'count': count})
    except Wishlist.DoesNotExist:
        return JsonResponse({'count': 0})
    
    # Add this to your wishlist views
@login_required
def check_wishlist_status(request, product_id):
    """Check if product is in user's wishlist"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        in_wishlist = WishlistItem.objects.filter(
            wishlist=wishlist, 
            product_id=product_id
        ).exists()
        
        return JsonResponse({
            'in_wishlist': in_wishlist,
            'product_id': product_id
        })
    except Wishlist.DoesNotExist:
        return JsonResponse({'in_wishlist': False, 'product_id': product_id})
    
@login_required
def wishlist_count(request):
    """Get current wishlist count"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        count = wishlist.total_items
    except Wishlist.DoesNotExist:
        count = 0
    
    return JsonResponse({'count': count})

@login_required
def get_wishlist_item_id(request, product_id):
    """Get wishlist item ID for a product"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_item = WishlistItem.objects.get(wishlist=wishlist, product_id=product_id)
        return JsonResponse({'item_id': wishlist_item.id})
    except (Wishlist.DoesNotExist, WishlistItem.DoesNotExist):
        return JsonResponse({'item_id': None})