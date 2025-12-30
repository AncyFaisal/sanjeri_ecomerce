from django.shortcuts import render, redirect, get_object_or_404
from ..models import Product, ProductVariant,Cart,CartItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.db import models 
from django.db.models.functions import Coalesce
from ..models import Wishlist,WishlistItem

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

    # Start with VARIANTS, not products
    variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_deleted=False,
        gender='Male'
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
    
    # Apply filters
    if price_range:
        if price_range == 'under-1000':
            variants = variants.filter(discount_price__lt=1000)
        elif price_range == '1000-3000':
            variants = variants.filter(discount_price__range=(1000, 3000))
        elif price_range == '3000-5000':
            variants = variants.filter(discount_price__range=(3000, 5000))
        elif price_range == '5000-10000':
            variants = variants.filter(discount_price__range=(5000, 10000))
        elif price_range == 'above-10000':
            variants = variants.filter(discount_price__gt=10000)
    
    if fragrance_type:
        variants = variants.filter(product__fragrance_type=fragrance_type)
    
    if occasion:
        variants = variants.filter(product__occasion=occasion)
    
    if volume:
        variants = variants.filter(volume_ml=volume)
    
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
    
    # Pagination
    paginator = Paginator(variants, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    available_volumes = ProductVariant.objects.filter(
        product__is_active=True,
        gender='Male',
        is_active=True
    ).values_list('volume_ml', flat=True).distinct().order_by('volume_ml')
    
    available_fragrance_types = Product.objects.filter(
        variants__gender='Male',
        is_active=True,
        is_deleted=False
    ).exclude(fragrance_type__isnull=True).exclude(fragrance_type='').values_list(
        'fragrance_type', flat=True
    ).distinct()
    
    available_occasions = Product.objects.filter(
        variants__gender='Male',
        is_active=True,
        is_deleted=False
    ).exclude(occasion__isnull=True).exclude(occasion='').values_list(
        'occasion', flat=True
    ).distinct()
    
    for variant in variants:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids

    context = {
        'variants': variants,
        'page_obj': page_obj,  # Now contains variants, not products
        'products_count': variants.count(),
        'search_query': search_query,
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'title': 'Men\'s Fragrances - Sanjeri',
        'cart_item_count': cart_item_count,
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
            wishlist_product_ids = wishlist.products.values_list('id', flat=True)
        except Wishlist.DoesNotExist:
            pass
    # Start with VARIANTS, not products
    variants = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_deleted=False,
        gender='Female'
    ).select_related('product').prefetch_related('product__images')
    
    # Apply search filter if query exists
    if search_query:
        variants = variants.filter(
            Q(product__name__icontains=search_query) |
            Q(product__description__icontains=search_query) |
            Q(product__brand__icontains=search_query) |
            Q(product__fragrance_type__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Apply filters
    if price_range:
        if price_range == 'under-1000':
            variants = variants.filter(discount_price__lt=1000)
        elif price_range == '1000-3000':
            variants = variants.filter(discount_price__range=(1000, 3000))
        elif price_range == '3000-5000':
            variants = variants.filter(discount_price__range=(3000, 5000))
        elif price_range == '5000-10000':
            variants = variants.filter(discount_price__range=(5000, 10000))
        elif price_range == 'above-10000':
            variants = variants.filter(discount_price__gt=10000)
    
    if fragrance_type:
        variants = variants.filter(product__fragrance_type=fragrance_type)
    
    if occasion:
        variants = variants.filter(product__occasion=occasion)
    
    if volume:
        variants = variants.filter(volume_ml=volume)
    
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
    
    # Pagination
    paginator = Paginator(variants, 12)  # Show 12 variants per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    available_volumes = ProductVariant.objects.filter(
        product__is_active=True,
        gender='Female',
        is_active=True
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
    for variant in variants:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids
    
    context = {
        'variants': variants,
        'page_obj': page_obj,  # Now contains variants, not products
        'products_count': variants.count(),
        'search_query': search_query,
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'title': 'Women\'s Fragrances - Sanjeri',
        'cart_item_count': cart_item_count,
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
            wishlist_product_ids = wishlist.products.values_list('id', flat=True)
        except Wishlist.DoesNotExist:
            pass
    
    # CRITICAL FIX: Query VARIANTS, not PRODUCTS
    variants = ProductVariant.objects.filter(
        gender='Unisex',
        is_active=True,
        product__is_active=True,
        product__is_deleted=False
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
    
    # Apply filters - FIXED: Use variant prices directly
    if price_range:
        if price_range == 'under-1000':
            variants = variants.filter(price__lt=1000)
        elif price_range == '1000-3000':
            variants = variants.filter(price__range=(1000, 3000))
        elif price_range == '3000-5000':
            variants = variants.filter(price__range=(3000, 5000))
        elif price_range == '5000-10000':
            variants = variants.filter(price__range=(5000, 10000))
        elif price_range == 'above-10000':
            variants = variants.filter(price__gt=10000)
    
    if fragrance_type:
        variants = variants.filter(product__fragrance_type=fragrance_type)
    
    if occasion:
        variants = variants.filter(product__occasion=occasion)
    
    if volume:
        variants = variants.filter(volume_ml=volume)
    
    # Apply sorting - FIXED: Use variant prices directly
    if sort_by == 'best-selling':
        variants = variants.filter(product__is_best_selling=True).order_by('-product__created_at')
    elif sort_by == 'price-low-high':
        variants = variants.order_by('price')
    elif sort_by == 'price-high-low':
        variants = variants.order_by('-price')
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
    
    # Pagination - FIXED: Paginate variants
    paginator = Paginator(variants, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options - FIXED: Get from variants
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
    for variant in variants:
        variant.product.is_in_wishlist = variant.product.id in wishlist_product_ids

    context = {
        'variants': variants,
        'page_obj': page_obj,  # This contains VARIANTS, not products
        'products_count': variants.count(),
        'search_query': search_query,
        'sort_by': sort_by,
        'available_volumes': available_volumes,
        'available_fragrance_types': available_fragrance_types,
        'available_occasions': available_occasions,
        'title': 'Unisex Fragrances - Sanjeri',
        'cart_item_count': cart_item_count,
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
            Q(variants__sku__icontains=query),
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
    paginator = Paginator(products, 12)
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