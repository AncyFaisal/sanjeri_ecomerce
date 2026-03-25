# views/homepage.py
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import Product, ProductVariant,Cart,CartItem,Wishlist


def homepage(request):
    """Home page view with actual products and search functionality"""
    query = request.GET.get('q', '')
    
     # Get all active products
    all_products = Product.objects.filter(is_active=True, is_deleted=False)
    cart_item_count = 0
    
    # Get wishlist product IDs for authenticated user
    wishlist_product_ids = []
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item_count = cart.total_items
        except Cart.DoesNotExist:
            pass
        
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))
        except Wishlist.DoesNotExist:
            pass
    
    # Apply search filter if query exists
    if query:
        search_products = all_products.filter(
            Q(name__icontains=query) | 
            Q(brand__icontains=query) |
            Q(description__icontains=query) |
            Q(fragrance_type__icontains=query)
        )
        is_searching = True
        search_results_count = search_products.count()
    else:
        search_products = None
        is_searching = False
        search_results_count = 0

    # Get featured products (only show if not searching)
    if not is_searching:
        featured_products = all_products.filter(is_featured=True)[:8]
    else:
        featured_products = search_products[:8] if search_products else []
    
    # Get products by gender for different sections
    mens_products = all_products.filter(
        variants__gender="Male",
        variants__is_active=True
    ).distinct()[:4]
    
    womens_products = all_products.filter(
        variants__gender="Female", 
        variants__is_active=True
    ).distinct()[:4]
    
    unisex_products = all_products.filter(
        variants__gender="Unisex", 
        variants__is_active=True
    ).distinct()[:4]

    # Add is_in_wishlist attribute to each product
    for product in featured_products:
        product.is_in_wishlist = product.id in wishlist_product_ids
    
    for product in mens_products:
        product.is_in_wishlist = product.id in wishlist_product_ids
    
    for product in womens_products:
        product.is_in_wishlist = product.id in wishlist_product_ids
    
    for product in unisex_products:
        product.is_in_wishlist = product.id in wishlist_product_ids

    context = {
        'title': 'Home - Sanjeri',
        'featured_products': featured_products,
        'mens_products': mens_products,
        'womens_products': womens_products,
        'unisex_products': unisex_products,
        'user': request.user,
        'search_query': query,
        'is_searching': is_searching,
        'search_results_count': search_results_count,
        'search_products': search_products,
        'cart_item_count': cart_item_count,
        'wishlist_product_ids': wishlist_product_ids, 
        # 'wishlist_product_ids': list(wishlist_items),
    }
    return render(request, 'homepage.html', context)



# def home_product_search(request):
#     """Unified search function for all search bars"""
#     query = request.GET.get('q', '')
#     products = Product.objects.filter(is_active=True, is_deleted=False)
    
#     if query:
#         # Search in product name, brand, description, and fragrance type
#         products = products.filter(
#             Q(name__icontains=query) | 
#             Q(brand__icontains=query) |
#             Q(description__icontains=query) |
#             Q(fragrance_type__icontains=query)
#         )
    
#     # Pagination
#     paginator = Paginator(products, 3)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     context = {
#         'products': page_obj,
#         'query': query,  # This is IMPORTANT - makes the clear button appear
#         'results_count': products.count(),
#         'title': f"Search Results for '{query}' - Sanjeri"
#     }
    
#     return render(request, 'headsearch_result.html', context)
