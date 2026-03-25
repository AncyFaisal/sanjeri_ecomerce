from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from ..models import Wishlist, WishlistItem, Product,Category,ProductVariant
from django.db.models import Q
from django.template.loader import render_to_string 
from ..models import Cart,CartItem
import json

@login_required
def wishlist_view(request):
    """Display the user's wishlist with search and filter"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product__category')
        
        # Get all categories for dropdown
        all_categories = Category.objects.filter(is_active=True)
        
        # Get search query
        search_query = request.GET.get('search', '')
        if search_query:
            wishlist_items = wishlist_items.filter(
                Q(product__name__icontains=search_query) |
                Q(product__description__icontains=search_query) |
                Q(product__brand__icontains=search_query) |
                Q(product__fragrance_type__icontains=search_query)
            )
        
        # Get category filter
        category_id = request.GET.get('category', '')
        if category_id:
            wishlist_items = wishlist_items.filter(product__category_id=category_id)
        
        # Get gender filter
        gender = request.GET.get('gender', '')
        if gender:
            # Find products that have variants with this gender
            product_ids = ProductVariant.objects.filter(
                gender=gender
            ).values_list('product_id', flat=True)
            wishlist_items = wishlist_items.filter(
                product_id__in=product_ids
            )
        # Get ALL possible genders from ALL products (not just wishlist items)
        # This ensures all gender options appear in the dropdown
        all_genders = ProductVariant.objects.filter(
            is_active=True
        ).values_list('gender', flat=True).distinct()
        
        # Get available genders from wishlist items (for context)
        # available_genders_in_wishlist = []
        # for item in wishlist_items:
        #     for variant in item.product.variants.all():
        #         if variant.gender not in available_genders_in_wishlist:
        #             available_genders_in_wishlist.append(variant.gender)
        
        # AJAX response
        if request.GET.get('ajax') == '1':
            html = render_to_string('wishlist_items_partial.html', {
                'wishlist_items': wishlist_items,
                'wishlist': wishlist,
            }, request=request)
            
            return JsonResponse({
                'html': html,
                'count': wishlist_items.count()
            })
        
        context = {
            'wishlist': wishlist,
            'wishlist_items': wishlist_items,
            'all_categories': all_categories,
            'search_query': search_query,
            'selected_category': int(category_id) if category_id else '',
            'selected_gender': gender,
            'available_genders': sorted(set(all_genders)),  # Use ALL genders
            'available_genders_in_wishlist': sorted(set(available_genders_in_wishlist)),  # Optional: for debugging
        }
        return render(request, 'wishlist.html', context)
        
    except Wishlist.DoesNotExist:
        # Create empty wishlist if it doesn't exist
        wishlist = Wishlist.objects.create(user=request.user)
        
        # Get all possible genders
        all_genders = ProductVariant.objects.filter(
            is_active=True
        ).values_list('gender', flat=True).distinct()
        
        context = {
            'wishlist': wishlist,
            'wishlist_items': [],
            'all_categories': Category.objects.filter(is_active=True),
            'search_query': '',
            'selected_category': '',
            'selected_gender': '',
            'available_genders': sorted(set(all_genders)),  # Use ALL genders
            'available_genders_in_wishlist': [],
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
def remove_from_wishlist(request, variant_id):
    """Remove product from wishlist by product_id"""
    try:
        # Get the wishlist item using product_id
        wishlist_item = WishlistItem.objects.filter(
            wishlist__user=request.user,
            product_id=variant_id
        ).first()
        
        if not wishlist_item:
            return JsonResponse({
                'success': False,
                'message': 'Item not found in wishlist'
            })
        
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
    

    # In views/wishlist.py
@login_required
@require_POST
@transaction.atomic
def add_to_cart_from_wishlist(request, product_id):
    """Add product to cart and remove from wishlist in one operation"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
        
        # Get the first available variant
        variant = product.variants.filter(is_active=True, stock__gt=0).first()
        if not variant:
            return JsonResponse({
                'success': False,
                'message': 'No available variants in stock'
            })
        
        # Add to cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': 1}
        )
        
        if not item_created:
            # Update quantity if it exists
            if cart_item.can_increment:
                cart_item.quantity += 1
                cart_item.save()
                message = "Product quantity updated in cart!"
            else:
                message = "Maximum quantity reached!"
        else:
            message = "Product added to cart!"
        
        # Remove from wishlist
        removed = False
        try:
            wishlist_item = WishlistItem.objects.filter(
                wishlist__user=request.user,
                product=product
            ).first()
            if wishlist_item:
                wishlist_item.delete()
                removed = True
        except Exception:
            pass
        
        # Get updated counts
        cart_count = cart.total_items
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart_count,
            'wishlist_count': wishlist_count,
            'removed_from_wishlist': removed,
            'variant_id': variant.id,
            'product_name': product.name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error: {str(e)}"
        })

@login_required
def check_wishlist_status(request, variant_id):
    """Check if variant is in user's wishlist"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        in_wishlist = WishlistItem.objects.filter(
            wishlist=wishlist, 
            variant_id=variant_id
        ).exists()
        
        return JsonResponse({
            'in_wishlist': in_wishlist,
            'variant_id': variant_id
        })
    except Wishlist.DoesNotExist:
        return JsonResponse({'in_wishlist': False, 'variant_id': variant_id})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from ..models import Wishlist, WishlistItem, Product, Category, ProductVariant
from django.db.models import Q
from django.template.loader import render_to_string 
from ..models import Cart, CartItem

@login_required
def wishlist_view(request):
    """Display the user's wishlist with search and filter"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product__category')
        
        # Get all categories for dropdown
        all_categories = Category.objects.filter(is_active=True)
        
        # Get search query
        search_query = request.GET.get('search', '')
        if search_query:
            wishlist_items = wishlist_items.filter(
                Q(product__name__icontains=search_query) |
                Q(product__description__icontains=search_query) |
                Q(product__brand__icontains=search_query) |
                Q(product__fragrance_type__icontains=search_query)
            )
        
        # Get category filter
        category_id = request.GET.get('category', '')
        if category_id:
            wishlist_items = wishlist_items.filter(product__category_id=category_id)
        
        # Get gender filter
        gender = request.GET.get('gender', '')
        if gender:
            # Find products that have variants with this gender
            product_ids = ProductVariant.objects.filter(
                gender=gender
            ).values_list('product_id', flat=True)
            wishlist_items = wishlist_items.filter(
                product_id__in=product_ids
            )
        
        # Get ALL possible genders from ALL products
        all_genders = ProductVariant.objects.filter(
            is_active=True
        ).values_list('gender', flat=True).distinct()
        
        # AJAX response
        if request.GET.get('ajax') == '1':
            html = render_to_string('wishlist_items_partial.html', {
                'wishlist_items': wishlist_items,
                'wishlist': wishlist,
            }, request=request)
            
            return JsonResponse({
                'html': html,
                'count': wishlist_items.count()
            })
        
        context = {
            'wishlist': wishlist,
            'wishlist_items': wishlist_items,
            'all_categories': all_categories,
            'search_query': search_query,
            'selected_category': int(category_id) if category_id else '',
            'selected_gender': gender,
            'available_genders': sorted(set(all_genders)),
        }
        return render(request, 'wishlist.html', context)
        
    except Wishlist.DoesNotExist:
        wishlist = Wishlist.objects.create(user=request.user)
        all_genders = ProductVariant.objects.filter(is_active=True).values_list('gender', flat=True).distinct()
        
        context = {
            'wishlist': wishlist,
            'wishlist_items': [],
            'all_categories': Category.objects.filter(is_active=True),
            'search_query': '',
            'selected_category': '',
            'selected_gender': '',
            'available_genders': sorted(set(all_genders)),
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
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist by product_id"""
    try:
        wishlist_item = WishlistItem.objects.filter(
            wishlist__user=request.user,
            product_id=product_id
        ).first()
        
        if not wishlist_item:
            return JsonResponse({
                'success': False,
                'message': 'Item not found in wishlist'
            })
        
        product_name = wishlist_item.product.name
        wishlist = wishlist_item.wishlist
        wishlist_item.delete()
        
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

@login_required
@require_POST
@transaction.atomic
def add_to_cart_from_wishlist(request, product_id):
    """Add product to cart and remove from wishlist in one operation"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
        
        # Get the first available variant
        variant = product.variants.filter(is_active=True, stock__gt=0).first()
        if not variant:
            return JsonResponse({
                'success': False,
                'message': 'No available variants in stock'
            })
        
        # Add to cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': 1}
        )
        
        if not item_created:
            if cart_item.can_increment:
                cart_item.quantity += 1
                cart_item.save()
                message = "Product quantity updated in cart!"
            else:
                message = "Maximum quantity reached!"
        else:
            message = "Product added to cart!"
        
        # Remove from wishlist
        removed = False
        try:
            wishlist_item = WishlistItem.objects.filter(
                wishlist__user=request.user,
                product=product
            ).first()
            if wishlist_item:
                wishlist_item.delete()
                removed = True
        except Exception:
            pass
        
        # Get updated counts
        cart_count = cart.total_items
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart_count,
            'wishlist_count': wishlist_count,
            'removed_from_wishlist': removed,
            'variant_id': variant.id,
            'product_name': product.name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error: {str(e)}"
        })

@login_required
@require_http_methods(["POST"])
def check_multiple_wishlist(request):
    """Check multiple products in wishlist at once"""
    try:
        import json
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_product_ids = set(
            WishlistItem.objects.filter(
                wishlist=wishlist,
                product_id__in=product_ids
            ).values_list('product_id', flat=True)
        )
        
        result = {str(pid): pid in wishlist_product_ids for pid in product_ids}
        result['total_count'] = len(wishlist_product_ids)
        
        return JsonResponse(result)
    except Wishlist.DoesNotExist:
        result = {str(pid): False for pid in product_ids}
        result['total_count'] = 0
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)