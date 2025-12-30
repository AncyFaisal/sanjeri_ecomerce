from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from ..models import Cart, CartItem, ProductVariant, Wishlist, WishlistItem


@login_required
def cart_view(request):
    """Display the user's cart"""
    try:
        # Get cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get cart items with proper related data
        cart_items = CartItem.objects.filter(cart=cart).select_related(
            'variant',
            'variant__product'
        ).all()
        
        # Debug output to console
        print(f"=== CART DEBUG ===")
        print(f"User: {request.user.username}")
        print(f"Cart ID: {cart.id}")
        print(f"Cart items count: {cart_items.count()}")
        
        # Create enhanced items list for template
        enhanced_items = []
        subtotal = 0
        
        for item in cart_items:
            product = item.variant.product
            variant = item.variant
            item_total = item.total_price
            subtotal += item_total
            
            enhanced_item = {
                'item': item,
                'product': product,
                'variant': variant,
                'quantity': item.quantity,
                'total_price': item_total,
                'is_available': item.is_available,
                'is_out_of_stock': item.is_out_of_stock,
                'has_low_stock': item.has_low_stock,
                'can_increment': item.can_increment,
                'can_decrement': item.can_decrement,
                'max_allowed_quantity': item.max_allowed_quantity,
            }
            enhanced_items.append(enhanced_item)
            
            # Debug print
            print(f"Item {item.id}: {product.name} - {variant.volume_ml}ml - Qty: {item.quantity}")
        
        context = {
            'cart': cart,
            'cart_items': enhanced_items,  # This should be passed to template
            'cart_total_items': len(enhanced_items),
            'cart_subtotal': subtotal,
            'can_checkout': cart.can_checkout,
        }
        
        print(f"Context cart_items length: {len(enhanced_items)}")
        print(f"Context subtotal: {subtotal}")
        
        return render(request, 'cart.html', context)
        
    except Exception as e:
        print(f"ERROR in cart_view: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return render(request, 'cart/cart.html', {
            'error': str(e),
            'cart_items': [],
            'cart_total_items': 0,
            'cart_subtotal': 0,
            'can_checkout': False,
        })
# @login_required
# def cart_view(request):
#     """Display the user's cart with enhanced availability info"""
#     try:
#         cart, created = Cart.objects.get_or_create(user=request.user)
#         cart_items = cart.items.select_related(
#             'variant', 
#             'variant__product', 
#             'variant__product__category'
#         ).all()
        
#         # Enhanced availability info for template
#         for item in cart_items:
#             item.availability_info = {
#                 'is_available': item.is_available,
#                 'is_out_of_stock': item.is_out_of_stock,
#                 'has_low_stock': item.has_low_stock,
#                 'can_increment': item.can_increment,
#                 'can_decrement': item.can_decrement,
#                 'max_allowed_quantity': item.max_allowed_quantity,
#                 'current_stock': item.variant.stock,
#                 'is_product_blocked': not item.product.is_active or item.product.is_deleted,
#                 'is_category_blocked': not item.product.category.is_active or item.product.category.is_deleted,
#                 'is_variant_blocked': not item.variant.is_active,
#             }
        
#         context = {
#             'cart': cart,
#             'cart_items': cart_items,
#             'can_checkout': cart.can_checkout,
#             'MAX_QUANTITY': CartItem.MAX_QUANTITY,
#         }
#         return render(request, 'cart.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading cart: {str(e)}")
        return render(request, 'cart.html', {
            'cart': None,
            'cart_items': [],
            'can_checkout': False,
            'MAX_QUANTITY': CartItem.MAX_QUANTITY,
        })

@login_required
@require_POST
@transaction.atomic
def add_to_cart(request, variant_id):
    """Add product variant to cart with comprehensive validation"""
    print(f"DEBUG: add_to_cart called for variant_id: {variant_id}")
    print(f"DEBUG: User: {request.user.username}")
    print(f"DEBUG: Is AJAX? {request.headers.get('x-requested-with')}")
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id)
        product = variant.product
        
        # Comprehensive availability checks
        if not product.is_active or product.is_deleted:
            return _error_response(request, "This product is currently unavailable.", product.id)
        
        if not product.category.is_active or product.category.is_deleted:
            return _error_response(request, "This product category is currently unavailable.", product.id)
        
        if not variant.is_active:
            return _error_response(request, "This product variant is not available.", product.id)
        
        if variant.stock <= 0:
            return _error_response(request, "This product is out of stock.", product.id)
        
        # Get quantity from request
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity <= 0:
            return _error_response(request, "Invalid quantity.", product.id)
        
        if quantity > variant.stock:
            return _error_response(request, f"Only {variant.stock} items available in stock.", product.id)
        
        if quantity > CartItem.MAX_QUANTITY:
            return _error_response(request, f"Cannot add more than {CartItem.MAX_QUANTITY} items of this product.", product.id)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if item already exists in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Item exists, update quantity with validation
            new_quantity = cart_item.quantity + quantity
            
            if new_quantity > CartItem.MAX_QUANTITY:
                cart_item.quantity = CartItem.MAX_QUANTITY
                message = f"Updated to maximum allowed quantity: {CartItem.MAX_QUANTITY}"
            elif new_quantity > variant.stock:
                cart_item.quantity = variant.stock
                message = f"Updated to maximum available stock: {variant.stock}"
            else:
                cart_item.quantity = new_quantity
                message = "Product quantity updated in cart!"
            
            cart_item.save()
        else:
            message = "Product added to cart successfully!"
        
        # Remove from wishlist if exists
        cart_item.remove_from_wishlist_if_exists(request.user)
        
        # Get updated cart data
        cart = Cart.objects.get(user=request.user)
        
        return _success_response(request, message, cart, cart_item, product.name)
        
    except Exception as e:
        return _error_response(request, f"Error adding product to cart: {str(e)}", None)

@login_required
@require_POST
@transaction.atomic
def update_cart_item(request, item_id):
    """Update cart item quantity with real-time validation"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        variant = cart_item.variant
        action = request.POST.get('action')
        
        if action == 'increment':
            return _handle_increment(request, cart_item, variant)
        elif action == 'decrement':
            return _handle_decrement(request, cart_item, variant)
        elif action == 'set_quantity':
            return _handle_set_quantity(request, cart_item, variant)
        else:
            return _error_response(request, "Invalid action.", None)
        
    except Exception as e:
        return _error_response(request, f"Error updating cart: {str(e)}", None)

@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.variant.product.name
        cart_item.delete()
        
        message = f"'{product_name}' removed from cart."
        cart = Cart.objects.get(user=request.user)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_total_items': cart.total_items,
                'subtotal': float(cart.subtotal),
                'item_removed': True
            })
        
        messages.success(request, message)
        return redirect('cart')
        
    except Exception as e:
        return _error_response(request, f"Error removing item from cart: {str(e)}", None)

@login_required
@require_POST
def clear_cart(request):
    """Clear entire cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        item_count = cart.total_items
        
        # Get all variant IDs before clearing (for localStorage cleanup)
        variant_ids = list(cart.items.values_list('variant_id', flat=True))
        
        cart.clear_cart()
        
        message = f"Cart cleared successfully! {item_count} items removed."
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_total_items': 0,
                'subtotal': 0,
                'cart_empty': True,
                'cleared_variants': variant_ids  # Send variant IDs that were cleared
            })
        
        messages.success(request, message)
        return redirect('cart')
        
    except Exception as e:
        return _error_response(request, f"Error clearing cart: {str(e)}", None)

def get_cart_count(request):
    """Get cart item count for AJAX requests"""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return JsonResponse({
                'count': cart.total_items,
                'subtotal': float(cart.subtotal)
            })
        except Cart.DoesNotExist:
            return JsonResponse({'count': 0, 'subtotal': 0})
    return JsonResponse({'count': 0, 'subtotal': 0})

# Helper functions
def _handle_increment(request, cart_item, variant):
    """Handle quantity increment with validation"""
    if not cart_item.can_increment:
        if cart_item.quantity >= CartItem.MAX_QUANTITY:
            message = f"Cannot add more than {CartItem.MAX_QUANTITY} items of this product"
        else:
            message = f"Only {variant.stock} items available in stock"
        return _error_response(request, message, None)
    
    cart_item.quantity += 1
    cart_item.save()
    return _success_update_response(request, "Quantity increased!", cart_item)

def _handle_decrement(request, cart_item, variant):
    """Handle quantity decrement"""
    if cart_item.quantity <= 1:
        # Remove item if quantity becomes 0
        product_name = cart_item.variant.product.name
        cart_item.delete()
        message = f"'{product_name}' removed from cart."
        cart = Cart.objects.get(user=request.user)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'item_removed': True,
                'cart_total_items': cart.total_items,
                'subtotal': float(cart.subtotal)
            })
        
        messages.success(request, message)
        return redirect('cart')
    
    cart_item.quantity -= 1
    cart_item.save()
    return _success_update_response(request, "Quantity decreased!", cart_item)

def _handle_set_quantity(request, cart_item, variant):
    """Handle direct quantity setting"""
    new_quantity = int(request.POST.get('quantity', 1))
    
    if new_quantity < 1:
        return _error_response(request, "Quantity must be at least 1", None)
    
    if new_quantity > CartItem.MAX_QUANTITY:
        return _error_response(request, f"Cannot add more than {CartItem.MAX_QUANTITY} items", None)
    
    if new_quantity > variant.stock:
        return _error_response(request, f"Only {variant.stock} items available", None)
    
    cart_item.quantity = new_quantity
    cart_item.save()
    return _success_update_response(request, "Quantity updated!", cart_item)

def _success_response(request, message, cart, cart_item, product_name):
    """Send success response"""
    response_data = {
        'success': True,
        'message': message,
        'cart_total_items': cart.total_items,
        'subtotal': float(cart.subtotal),
        'product_name': product_name,
        'item_quantity': cart_item.quantity,
        'item_total': float(cart_item.total_price),
        'item_id': cart_item.id if hasattr(cart_item, 'id') else None,
        'can_increment': cart_item.can_increment,
        'can_decrement': cart_item.can_decrement,
        'max_quantity': cart_item.max_allowed_quantity,
    }
    
    print(f"DEBUG: _success_response data: {response_data}")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(response_data)
    
    messages.success(request, message)
    return redirect('cart')
   
    # """Send success response"""
    # response_data = {
    #     'success': True,
    #     'message': message,
    #     'cart_total_items': cart.total_items,
    #     'subtotal': float(cart.subtotal),
    #     'product_name': product_name
    # }
    
    # if hasattr(cart_item, 'quantity'):
    #     response_data['item_quantity'] = cart_item.quantity
    #     response_data['item_total'] = float(cart_item.total_price)
    
    # if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    #     return JsonResponse(response_data)
    
    # messages.success(request, message)
    # return redirect('cart')

def _success_update_response(request, message, cart_item):
    """Send success response for updates"""
    cart = cart_item.cart
    response_data = {
        'success': True,
        'message': message,
        'item_quantity': cart_item.quantity,
        'item_total': float(cart_item.total_price),
        'cart_total_items': cart.total_items,
        'subtotal': float(cart.subtotal),
        'can_increment': cart_item.can_increment,
        'can_decrement': cart_item.can_decrement,
        'max_quantity': cart_item.max_allowed_quantity,
        'current_stock': cart_item.variant.stock,
        'item_id': cart_item.id
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(response_data)
    
    messages.success(request, message)
    return redirect('cart')

def _error_response(request, message, product_id=None):
    """Send error response"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': message
        }, status=400)
    
    messages.error(request, message)
    if product_id:
        return redirect('product_detail', product_id=product_id)
    return redirect('cart')

# for debugging
@login_required
def cart_debug(request):
    """Debug view to see what's in the cart"""
    # from .models import Cart, CartItem
    
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = list(cart.items.all())
        
        # Prepare debug info
        debug_data = {
            'cart_id': cart.id,
            'user': request.user.username,
            'total_items': cart.total_items,
            'subtotal': float(cart.subtotal),
            'items_count': cart.items.count(),
            'items': []
        }
        
        for item in cart_items:
            debug_data['items'].append({
                'id': item.id,
                'product_id': item.variant.product.id,
                'product_name': item.variant.product.name,
                'variant_id': item.variant.id,
                'variant_price': float(item.variant.display_price),
                'quantity': item.quantity,
                'total_price': float(item.total_price),
                'is_available': item.is_available,
                'stock': item.variant.stock,
                'variant_active': item.variant.is_active,
                'product_active': item.variant.product.is_active,
            })
        
        return render(request, 'cart_debug.html', {
            'debug_data': debug_data,
            'raw_items': cart_items,
        })
        
    except Exception as e:
        return render(request, 'cart_debug.html', {
            'error': str(e),
            'debug_data': None,
        })
    
@login_required
def check_variant_in_cart(request, variant_id):
    """Check if a variant is in the user's cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        in_cart = cart.items.filter(variant_id=variant_id).exists()
        
        return JsonResponse({
            'in_cart': in_cart,
            'variant_id': variant_id
        })
    except Cart.DoesNotExist:
        return JsonResponse({'in_cart': False, 'variant_id': variant_id})