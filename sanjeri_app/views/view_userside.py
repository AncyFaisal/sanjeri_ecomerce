from django.shortcuts import render, redirect, get_object_or_404
from ..models import Product, ProductVariant,Cart,CartItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.db import models 
from django.db.models.functions import Coalesce
from ..models import Wishlist,WishlistItem
from ..models.offer_models import ProductOffer, CategoryOffer
from django.utils import timezone

def home(request):
    """Home page view showing variants individually"""
    # Get cart item count
    cart_item_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    # Get active variants for each category (like your men's page)
    mens_variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_deleted=False,
        gender='Male'
    ).select_related('product').prefetch_related('product__images')[:12]  # Limit to 12 variants
    
    womens_variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_deleted=False,
        gender='Female'
    ).select_related('product').prefetch_related('product__images')[:12]
    
    unisex_variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_deleted=False,
        gender='Unisex'
    ).select_related('product').prefetch_related('product__images')[:12]
    
    # Get featured variants
    featured_variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_featured=True,
        product__is_active=True,
        product__is_deleted=False
    ).select_related('product').prefetch_related('product__images')[:8]
    
    context = {
        'title': 'Home - Sanjeri',
        'mens_variants': mens_variants,
        'womens_variants': womens_variants,
        'unisex_variants': unisex_variants,
        'featured_variants': featured_variants,
        'cart_item_count': cart_item_count
    }
    return render(request, 'home.html', context)

def men_products(request):
    """Men's products view showing each variant as separate card"""
    # Get all parameters including search
    # At the beginning of the view function:
 
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')
    gender_filter = request.GET.get('gender', 'Male')  # Add this line
    
    cart_item_count = 0
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

    
    # Start with VARIANTS, not products
    variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_deleted=False,
        gender=gender_filter  # Use the variable here
    ).select_related('product')
    
    # Apply search filter if query exists
    if search_query:
        variants = variants.filter(
            Q(product__name__icontains=search_query) |
            Q(product__description__icontains=search_query) |
            Q(product__brand__icontains=search_query) |
            Q(product__fragrance_type__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Apply filters - FIXED LOGIC
    if price_range:
        if price_range == 'under-1000':
            variants = variants.filter(discount_price__lt=1000)
        elif price_range == '1000-2000':
            variants = variants.filter(discount_price__range=(1000, 2000))
        elif price_range == '2000-3000':
            variants = variants.filter(discount_price__range=(2000, 3000))
        elif price_range == '3000-5000':  
            variants = variants.filter(discount_price__range=(3000, 5000))
        elif price_range == 'above-5000':
            variants = variants.filter(discount_price__gt=5000)
    
    if fragrance_type:
        variants = variants.filter(product__fragrance_type=fragrance_type)
    
    if occasion:
        variants = variants.filter(product__occasion=occasion)
    
    if volume:
        try:
            volume_int = int(volume)
            variants = variants.filter(volume_ml=volume_int)
        except ValueError:
            pass  # Handle invalid volume gracefully
    
    # Apply sorting
    if sort_by == 'best-selling':
        variants = variants.filter(product__is_best_selling=True).order_by('-product__created_at')
    elif sort_by == 'price-low-high':
        variants = variants.order_by('discount_price', 'price')
    elif sort_by == 'price-high-low':
        variants = variants.order_by('-discount_price', '-price')
    elif sort_by == 'newest':
        variants = variants.order_by('-product__created_at')
    elif sort_by == 'customer-rating':
        variants = variants.order_by('-product__avg_rating')
    elif sort_by == 'alphabetical-az':
        variants = variants.order_by('product__name')
    elif sort_by == 'alphabetical-za':
        variants = variants.order_by('-product__name')
    else:  # featured (default)
        variants = variants.filter(product__is_featured=True).order_by('-product__created_at')
    
    # Add wishlist status to each variant's product
    for variant in variants:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids
    

    # Get available filter options
    available_volumes = ProductVariant.objects.filter(
        product__is_active=True,
        gender=gender_filter,  # Use the variable
        is_active=True
    ).values_list('volume_ml', flat=True).distinct().order_by('volume_ml')
    
    available_fragrance_types = Product.objects.filter(
        variants__gender=gender_filter,  # Use the variable
        is_active=True,
        is_deleted=False
    ).exclude(fragrance_type__isnull=True).exclude(fragrance_type='').values_list(
        'fragrance_type', flat=True
    ).distinct()
    
    available_occasions = Product.objects.filter(
        variants__gender=gender_filter,  # Use the variable
        is_active=True,
        is_deleted=False
    ).exclude(occasion__isnull=True).exclude(occasion='').values_list(
        'occasion', flat=True
    ).distinct()
    
    
    # Pagination
    paginator = Paginator(variants, 5)  # Changed from 5 to 12 for 4 per row × 3 rows
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'variants': page_obj,  # Use paginated variants
        'page_obj': page_obj,
        'products_count': variants.count(),
        'search_query': search_query,
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'title': 'Men\'s Fragrances - Sanjeri',
        'cart_item_count': cart_item_count,
        'active_filters': {
            'price_range': price_range,
            'fragrance_type': fragrance_type,
            'occasion': occasion,
            'volume': volume,
        },
        'now': timezone.now()
    }
    return render(request, 'men.html', context)


def women_products(request):
    """Women's products view showing each variant as separate card"""
    # Get all parameters including search

    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')
    
    cart_item_count = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item_count = cart.total_items
        except Cart.DoesNotExist:
            pass

        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_product_ids = list(WishlistItem.objects.filter(
                wishlist=wishlist
            ).values_list('product_id', flat=True))        
        except Wishlist.DoesNotExist:
            pass
    
    # DEBUG: Print filter parameters
    print(f"=== DEBUG WOMEN FILTERS ===")
    print(f"Price Range: {price_range}")
    print(f"Fragrance Type: {fragrance_type}")
    print(f"Occasion: {occasion}")
    print(f"Volume: {volume}")
    print(f"Sort By: {sort_by}")
    print(f"Search Query: {search_query}")
    
    # Query VARIANTS for Women
    variants = ProductVariant.objects.filter(
        gender='Female',  # Note: Your model has 'Female', not 'Women'
        is_active=True,
        product__is_active=True,
        product__is_deleted=False
    ).select_related('product')
    
    print(f"Initial variants count: {variants.count()}")
    
    # Apply search filter if query exists
    if search_query:
        variants = variants.filter(
            Q(product__name__icontains=search_query) |
            Q(product__description__icontains=search_query) |
            Q(product__brand__icontains=search_query) |
            Q(product__fragrance_type__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
        print(f"After search filter: {variants.count()}")
    
    # Apply price filter - USING DISCOUNT_PRICE ONLY (same as unisex)
    if price_range:
        if price_range == 'under-1000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__lt=1000)
        elif price_range == '1000-2000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__range=(1000, 2000))
        elif price_range == '2000-3000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__range=(2000, 3000))
        elif price_range == '3000-5000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__range=(3000, 5000))
        elif price_range == 'above-5000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__gt=5000)
        print(f"After price filter '{price_range}': {variants.count()}")
    
    # Apply fragrance type filter
    if fragrance_type:
        variants = variants.filter(product__fragrance_type=fragrance_type)
        print(f"After fragrance filter '{fragrance_type}': {variants.count()}")
    
    # Apply occasion filter
    if occasion:
        variants = variants.filter(product__occasion=occasion)
        print(f"After occasion filter '{occasion}': {variants.count()}")
    
    # Apply volume filter - convert string to integer
    if volume:
        try:
            volume_int = int(volume)
            variants = variants.filter(volume_ml=volume_int)
            print(f"After volume filter '{volume_int}ml': {variants.count()}")
        except ValueError:
            pass
    
    # Apply sorting - USING DISCOUNT_PRICE FOR SORTING TOO
    if sort_by == 'best-selling':
        variants = variants.filter(product__is_best_selling=True).order_by('-product__created_at')
    elif sort_by == 'price-low-high':
        # Sort by effective price (discount_price first, then price)
        variants = variants.annotate(
            effective_price=Coalesce('discount_price', 'price')
        ).order_by('effective_price')
    elif sort_by == 'price-high-low':
        # Sort by effective price (discount_price first, then price)
        variants = variants.annotate(
            effective_price=Coalesce('discount_price', 'price')
        ).order_by('-effective_price')
    elif sort_by == 'newest':
        variants = variants.order_by('-product__created_at')
    elif sort_by == 'customer-rating':
        variants = variants.order_by('-product__avg_rating')
    elif sort_by == 'alphabetical-az':
        variants = variants.order_by('product__name')
    elif sort_by == 'alphabetical-za':
        variants = variants.order_by('-product__name')
    else:  # featured (default)
        variants = variants.filter(product__is_featured=True).order_by('-product__created_at')
    
    # Then for each variant, add:
    for variant in variants:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids


    print(f"Final variants count before pagination: {variants.count()}")
    print("=== END DEBUG ===")
    
    # Pagination - 12 per page (4 per row × 3 rows)
    paginator = Paginator(variants, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    available_volumes = ProductVariant.objects.filter(
        gender='Female',
        is_active=True,
        product__is_active=True,
        product__is_deleted=False
    ).values_list('volume_ml', flat=True).distinct().order_by('volume_ml')
    
    available_fragrance_types = Product.objects.filter(
        variants__gender='Female',
        is_active=True,
        is_deleted=False
    ).exclude(fragrance_type__isnull=True).exclude(fragrance_type='').values_list(
        'fragrance_type', flat=True
    ).distinct()
    
    available_occasions = Product.objects.filter(
        variants__gender='Female',
        is_active=True,
        is_deleted=False
    ).exclude(occasion__isnull=True).exclude(occasion='').values_list(
        'occasion', flat=True
    ).distinct()
    
    # For each variant, check if its product is in wishlist
   
    context = {
        'variants': page_obj,  # Use paginated variants
        'page_obj': page_obj,
        'products_count': variants.count(),
        'search_query': search_query,
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'title': 'Women\'s Fragrances - Sanjeri',
        'cart_item_count': cart_item_count,
        'wishlist_count': len(wishlist_product_ids),
        'active_filters': {
            'price_range': price_range,
            'fragrance_type': fragrance_type,
            'occasion': occasion,
            'volume': volume,
        }
    }
    return render(request, 'women.html', context)

def unisex_products(request):
    """Unisex products view showing each variant as separate card"""
    # Get all parameters including search

   
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')
    
    cart_item_count = 0
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
    
    # DEBUG: Print filter parameters
    print(f"=== DEBUG UNISEX FILTERS ===")
    print(f"Price Range: {price_range}")
    print(f"Fragrance Type: {fragrance_type}")
    print(f"Occasion: {occasion}")
    print(f"Volume: {volume}")
    print(f"Sort By: {sort_by}")
    print(f"Search Query: {search_query}")
    
    # Query VARIANTS for Unisex
    variants = ProductVariant.objects.filter(
        gender='Unisex',  # Capital 'U' matches your model
        is_active=True,
        product__is_active=True,
        product__is_deleted=False
    ).select_related('product')
    
    print(f"Initial variants count: {variants.count()}")
    
    # Apply search filter if query exists
    if search_query:
        variants = variants.filter(
            Q(product__name__icontains=search_query) |
            Q(product__description__icontains=search_query) |
            Q(product__brand__icontains=search_query) |
            Q(product__fragrance_type__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
        print(f"After search filter: {variants.count()}")
    
    # Apply price filter - USING DISCOUNT_PRICE ONLY
    if price_range:
        if price_range == 'under-1000':
            # Use COALESCE to use discount_price if exists, otherwise price
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__lt=1000)
        elif price_range == '1000-2000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__range=(1000, 2000))
        elif price_range == '2000-3000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__range=(2000, 3000))
        elif price_range == '3000-5000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__range=(3000, 5000))
        elif price_range == 'above-5000':
            variants = variants.annotate(
                effective_price=Coalesce('discount_price', 'price')
            ).filter(effective_price__gt=5000)
        print(f"After price filter '{price_range}': {variants.count()}")
    
    # Apply fragrance type filter
    if fragrance_type:
        variants = variants.filter(product__fragrance_type=fragrance_type)
        print(f"After fragrance filter '{fragrance_type}': {variants.count()}")
    
    # Apply occasion filter
    if occasion:
        variants = variants.filter(product__occasion=occasion)
        print(f"After occasion filter '{occasion}': {variants.count()}")
    
    # Apply volume filter - convert string to integer
    if volume:
        try:
            volume_int = int(volume)
            variants = variants.filter(volume_ml=volume_int)
            print(f"After volume filter '{volume_int}ml': {variants.count()}")
        except ValueError:
            pass
    
    # Apply sorting - ALSO USING DISCOUNT_PRICE FOR SORTING
    if sort_by == 'best-selling':
        variants = variants.filter(product__is_best_selling=True).order_by('-product__created_at')
    elif sort_by == 'price-low-high':
        # Sort by effective price (discount_price first, then price)
        variants = variants.annotate(
            effective_price=Coalesce('discount_price', 'price')
        ).order_by('effective_price')
    elif sort_by == 'price-high-low':
        # Sort by effective price (discount_price first, then price)
        variants = variants.annotate(
            effective_price=Coalesce('discount_price', 'price')
        ).order_by('-effective_price')
    elif sort_by == 'newest':
        variants = variants.order_by('-product__created_at')
    elif sort_by == 'customer-rating':
        variants = variants.order_by('-product__avg_rating')
    elif sort_by == 'alphabetical-az':
        variants = variants.order_by('product__name')
    elif sort_by == 'alphabetical-za':
        variants = variants.order_by('-product__name')
    else:  # featured (default)
        variants = variants.filter(product__is_featured=True).order_by('-product__created_at')
    
     # Then for each variant, add:
    for variant in variants:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids


    print(f"Final variants count before pagination: {variants.count()}")
    print("=== END DEBUG ===")
    
    # Pagination - 12 per page (4 per row × 3 rows)
    paginator = Paginator(variants, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    available_volumes = ProductVariant.objects.filter(
        gender='Unisex',
        is_active=True,
        product__is_active=True,
        product__is_deleted=False
    ).values_list('volume_ml', flat=True).distinct().order_by('volume_ml')
    
    available_fragrance_types = Product.objects.filter(
        variants__gender='Unisex',
        is_active=True,
        is_deleted=False
    ).exclude(fragrance_type__isnull=True).exclude(fragrance_type='').values_list(
        'fragrance_type', flat=True
    ).distinct()
    
    available_occasions = Product.objects.filter(
        variants__gender='Unisex',
        is_active=True,
        is_deleted=False
    ).exclude(occasion__isnull=True).exclude(occasion='').values_list(
        'occasion', flat=True
    ).distinct()
    
    # For each variant, check if its product is in wishlist
    for variant in page_obj.object_list:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids
    
    context = {
        'variants': page_obj,  # Use paginated variants, not all variants
        'page_obj': page_obj,
        'products_count': variants.count(),
        'search_query': search_query,
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'title': 'Unisex Fragrances - Sanjeri',
        'cart_item_count': cart_item_count,
        'active_filters': {
            'price_range': price_range,
            'fragrance_type': fragrance_type,
            'occasion': occasion,
            'volume': volume,
        }
    }
    return render(request, 'unisex.html', context)
def brands(request):
    """Brands page view"""
    # Get all unique brands from products
    brands = Product.objects.filter(
        is_active=True,
        is_deleted=False,
        variants__is_active=True
    ).exclude(brand__isnull=True).exclude(brand='').values_list(
        'brand', flat=True
    ).distinct().order_by('brand')
    
    # Get products count per brand
    brand_counts = {}
    for brand in brands:
        brand_counts[brand] = Product.objects.filter(
            brand=brand,
            is_active=True,
            is_deleted=False,
            variants__is_active=True
        ).distinct().count()
    
    context = {
        'title': "Brands - Sanjeri",
        'brands': brands,
        'brand_counts': brand_counts
    }
    return render(request, 'brands.html', context)

def brand_products(request, brand_name):
    """Products by specific brand"""
    products = Product.objects.filter(
        brand=brand_name,
        is_active=True,
        is_deleted=False,
        variants__is_active=True
    ).distinct()
    
    # Handle sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'best-selling':
        products = products.filter(is_best_selling=True).order_by('-created_at')
    elif sort_by == 'price-low-high':
        products = sorted(products, key=lambda p: p.min_price)
    elif sort_by == 'price-high-low':
        products = sorted(products, key=lambda p: p.max_price, reverse=True)
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'customer-rating':
        products = products.order_by('-avg_rating')
    elif sort_by == 'alphabetical-az':
        products = products.order_by('name')
    elif sort_by == 'alphabetical-za':
        products = products.order_by('-name')
    else:  # featured (default)
        products = products.filter(is_featured=True).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'brand_name': brand_name,
        'products_count': products.count(),
        'sort_by': sort_by,
        'title': f'{brand_name} - Sanjeri'
    }
    return render(request, 'brand_products.html', context)

def product_search(request):
    """Search functionality"""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'relevance')
    
    if query:
        # Search in products and variants
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(brand__icontains=query) |
            Q(fragrance_type__icontains=query) |
            Q(variants__sku__icontains=query) |
            Q(category__name__icontains=query),
            is_active=True,
            is_deleted=False,
            variants__is_active=True
        ).distinct()
        
        # Filter by category if provided
        if category:
            products = products.filter(category__name__icontains=category)
        
        # Handle sorting
        if sort_by == 'price-low-high':
            products = sorted(products, key=lambda p: p.min_price)
        elif sort_by == 'price-high-low':
            products = sorted(products, key=lambda p: p.max_price, reverse=True)
        elif sort_by == 'newest':
            products = products.order_by('-created_at')
        elif sort_by == 'customer-rating':
            products = products.order_by('-avg_rating')
        elif sort_by == 'alphabetical-az':
            products = products.order_by('name')
        elif sort_by == 'alphabetical-za':
            products = products.order_by('-name')
        else:  # relevance (default)
            # Basic relevance sorting
            products = products.order_by('-is_featured', '-avg_rating')
        
        # Pagination
        paginator = Paginator(products, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'title': f"Search Results for '{query}' - Sanjeri",
            'query': query,
            'page_obj': page_obj,
            'results_count': products.count(),
            'sort_by': sort_by
        }
    else:
        context = {
            'title': "Search - Sanjeri",
            'query': '',
            'page_obj': None,
            'results_count': 0
        }
    
    return render(request, 'search_results.html', context)

def wishlist(request):
    """Wishlist page - placeholder"""
    # You'll need to implement wishlist functionality
    wishlist_items = []  # Get from session or database
    
    context = {
        'title': 'Wishlist - Sanjeri',
        'wishlist_count': len(wishlist_items),
        'wishlist_items': wishlist_items
    }
    return render(request, 'wishlist.html', context)

def cart(request):
    """Cart page - placeholder"""
    # You'll need to implement cart functionality
    cart_items = []  # Get from session or database
    total_price = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
    
    context = {
        'title': 'Cart - Sanjeri',
        'cart_count': len(cart_items),
        'cart_items': cart_items,
        'total_price': total_price
    }
    return render(request, 'cart.html', context)

def all_products(request):
    """All products page with filtering and sorting"""
    # Get filter parameters
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')
    gender = request.GET.get('gender', '')
    category = request.GET.get('category', '')
    
    # Start with base queryset
    products = Product.objects.filter(
        is_active=True,
        is_deleted=False,
        variants__is_active=True
    ).distinct()
    
    # Apply filters
    if price_range:
        if price_range == 'under-1000':
            products = products.filter(variants__price__lt=1000)
        elif price_range == '1000-3000':
            products = products.filter(variants__price__range=(1000, 3000))
        elif price_range == '3000-5000':
            products = products.filter(variants__price__range=(3000, 5000))
        elif price_range == '5000-10000':
            products = products.filter(variants__price__range=(5000, 10000))
        elif price_range == 'above-10000':
            products = products.filter(variants__price__gt=10000)
    
    if fragrance_type:
        products = products.filter(fragrance_type=fragrance_type)
    
    if occasion:
        products = products.filter(occasion=occasion)
    
    if volume:
        products = products.filter(variants__volume_ml=volume)
    
    if gender:
        products = products.filter(variants__gender=gender)
    
    if category:
        products = products.filter(category__name__icontains=category)
    
    # Apply sorting
    if sort_by == 'best-selling':
        products = products.filter(is_best_selling=True).order_by('-created_at')
    elif sort_by == 'price-low-high':
        products = sorted(products, key=lambda p: p.min_price)
    elif sort_by == 'price-high-low':
        products = sorted(products, key=lambda p: p.max_price, reverse=True)
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'customer-rating':
        products = products.order_by('-avg_rating')
    elif sort_by == 'alphabetical-az':
        products = products.order_by('name')
    elif sort_by == 'alphabetical-za':
        products = products.order_by('-name')
    else:  # featured (default)
        products = products.filter(is_featured=True).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    available_volumes = ProductVariant.objects.filter(
        product__in=products,
        is_active=True
    ).values_list('volume_ml', flat=True).distinct().order_by('volume_ml')
    
    available_fragrance_types = Product.objects.filter(
        id__in=products.values_list('id', flat=True)
    ).exclude(fragrance_type__isnull=True).exclude(fragrance_type='').values_list(
        'fragrance_type', flat=True
    ).distinct()
    
    available_occasions = Product.objects.filter(
        id__in=products.values_list('id', flat=True)
    ).exclude(occasion__isnull=True).exclude(occasion='').values_list(
        'occasion', flat=True
    ).distinct()
    
    from ..models import Category
    available_categories = Category.objects.filter(
        is_active=True,
        is_deleted=False
    )
    
    context = {
        'page_obj': page_obj,
        'products_count': products.count(),
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'available_categories': available_categories,
        'title': 'All Fragrances - Sanjeri'
    }
    return render(request, 'all_products.html', context)