from django.shortcuts import render, redirect, get_object_or_404
from ..models import Product, ProductVariant,Cart,CartItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.db import models 
from django.db.models.functions import Coalesce

def home(request):
    """Home page view"""
    # Get featured products with variants
    featured_products = Product.objects.filter(
        is_featured=True,
        is_active=True, 
        is_deleted=False,
        variants__is_active=True
    ).distinct()[:8]  # Limit to 8 featured products
    
    # Get best selling products
    best_selling_products = Product.objects.filter(
        is_best_selling=True,
        is_active=True,
        is_deleted=False,
        variants__is_active=True
    ).distinct()[:8]
    
    # Get new arrival products
    new_arrival_products = Product.objects.filter(
        is_new_arrival=True,
        is_active=True,
        is_deleted=False,
        variants__is_active=True
    ).distinct()[:8]
    
    context = {
        'title': 'Home - Sanjeri',
        'featured_products': featured_products,
        'best_selling_products': best_selling_products,
        'new_arrival_products': new_arrival_products
    }
    return render(request, 'home.html', context)

def men_products(request):
    """Men's products view with search, sorting, filtering and pagination"""
    # Get all parameters including search
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')

    cart_item_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    
    # Debug print to check if search is working
    print(f"Search query in men_products: {search_query}")
    
    # Start with base queryset - only active, non-deleted products with men's variants
    products = Product.objects.filter(
        is_active=True,
        is_deleted=False,
        variants__gender='Male',
        variants__is_active=True
    ).distinct()
    
    # Apply search filter if query exists
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(fragrance_type__icontains=search_query) |
            Q(variants__sku__icontains=search_query)
        )
        print(f"Products after search filter: {products.count()}")
    
    # Apply filters - FIXED PRICE RANGES
    if price_range:
        if price_range == 'under-1000':
            products = products.filter(variants__discount_price__lt=1000)
        elif price_range == '1000-3000':
            products = products.filter(variants__discount_price__range=(1000, 3000))
        elif price_range == '3000-5000':
            products = products.filter(variants__discount_price__range=(3000, 5000))
        elif price_range == '5000-10000':
            products = products.filter(variants__discount_price__range=(5000, 10000))
        elif price_range == 'above-10000':
            products = products.filter(variants__discount_price__gt=10000)
    
    if fragrance_type:
        products = products.filter(fragrance_type=fragrance_type)
    
    if occasion:
        products = products.filter(occasion=occasion)
    
    if volume:
        products = products.filter(variants__volume_ml=volume)
    
    # Apply sorting - FIXED: Use database ordering instead of Python sorted()
    if sort_by == 'best-selling':
        products = products.filter(is_best_selling=True).order_by('-created_at')
    elif sort_by == 'price-low-high':
        products = products.annotate(
            final_min_price=Coalesce(
                models.Min('variants__discount_price'),
                models.Min('variants__price')
            )
        ).order_by('final_min_price')
    elif sort_by == 'price-high-low':
        products = products.annotate(
            final_max_price=Coalesce(
                models.Max('variants__discount_price'),
                models.Max('variants__price')
            )
        ).order_by('-final_max_price')
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
        gender='Male',
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
    
    context = {
        'page_obj': page_obj,
        'products_count': products.count(),
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
    """Women's products view with search, sorting, filtering and pagination"""
    # Get all parameters including search
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')
    
    
    cart_item_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item_count = cart.total_items
        except Cart.DoesNotExist:
            pass

    # Start with base queryset - only active, non-deleted products with women's variants
    products = Product.objects.filter(
        is_active=True,
        is_deleted=False,
        variants__gender='Female',
        variants__is_active=True
    ).distinct()
    
    # Apply search filter if query exists
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(fragrance_type__icontains=search_query) |
            Q(variants__sku__icontains=search_query)
        )
    
    # Apply filters - FIXED PRICE RANGES
    if price_range:
        if price_range == 'under-1000':
            products = products.filter(variants__discount_price__lt=1000)
        elif price_range == '1000-3000':
            products = products.filter(variants__discount_price__range=(1000, 3000))
        elif price_range == '3000-5000':
            products = products.filter(variants__discount_price__range=(3000, 5000))
        elif price_range == '5000-10000':
            products = products.filter(variants__discount_price__range=(5000, 10000))
        elif price_range == 'above-10000':
            products = products.filter(variants__discount_price__gt=10000)
    
    if fragrance_type:
        products = products.filter(fragrance_type=fragrance_type)
    
    if occasion:
        products = products.filter(occasion=occasion)
    
    if volume:
        products = products.filter(variants__volume_ml=volume)
    
    # Apply sorting - FIXED: Use database ordering
    if sort_by == 'best-selling':
        products = products.filter(is_best_selling=True).order_by('-created_at')
    elif sort_by == 'price-low-high':
        products = products.annotate(
            final_min_price=Coalesce(
                models.Min('variants__discount_price'),
                models.Min('variants__price')
            )
        ).order_by('final_min_price')
    elif sort_by == 'price-high-low':
        products = products.annotate(
            final_max_price=Coalesce(
                models.Max('variants__discount_price'),
                models.Max('variants__price')
            )
        ).order_by('-final_max_price')
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
        gender='Female',
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
    
    context = {
        'page_obj': page_obj,
        'products_count': products.count(),
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
    """Unisex products view with search, sorting, filtering and pagination"""
    # Get all parameters including search
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'featured')
    price_range = request.GET.get('price_range', '')
    fragrance_type = request.GET.get('fragrance_type', '')
    occasion = request.GET.get('occasion', '')
    volume = request.GET.get('volume', '')
    gender = request.GET.get('gender', '')

    
    cart_item_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    # Start with base queryset - only active, non-deleted products with unisex variants
    products = Product.objects.filter(
        is_active=True,
        is_deleted=False,
        variants__gender='Unisex',
        variants__is_active=True
    ).distinct()
    
    # Apply search filter if query exists
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(fragrance_type__icontains=search_query) |
            Q(variants__sku__icontains=search_query)
        )
    
    # Apply filters - FIXED PRICE RANGES
    if price_range:
        if price_range == 'under-1000':
            products = products.filter(variants__discount_price__lt=1000)
        elif price_range == '1000-3000':
            products = products.filter(variants__discount_price__range=(1000, 3000))
        elif price_range == '3000-5000':
            products = products.filter(variants__discount_price__range=(3000, 5000))
        elif price_range == '5000-10000':
            products = products.filter(variants__discount_price__range=(5000, 10000))
        elif price_range == 'above-10000':
            products = products.filter(variants__discount_price__gt=10000)
    
    if fragrance_type:
        products = products.filter(fragrance_type=fragrance_type)
    
    if occasion:
        products = products.filter(occasion=occasion)
    
    if volume:
        products = products.filter(variants__volume_ml=volume)
    
    # Gender filter for unisex page
    if gender:
        products = products.filter(variants__gender=gender)
    
    # Apply sorting - FIXED: Use database ordering
    if sort_by == 'best-selling':
        products = products.filter(is_best_selling=True).order_by('-created_at')
    elif sort_by == 'price-low-high':
        products = products.annotate(
            final_min_price=Coalesce(
                models.Min('variants__discount_price'),
                models.Min('variants__price')
            )
        ).order_by('final_min_price')
    elif sort_by == 'price-high-low':
        products = products.annotate(
            final_max_price=Coalesce(
                models.Max('variants__discount_price'),
                models.Max('variants__price')
            )
        ).order_by('-final_max_price')
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
    
    context = {
        'page_obj': page_obj,
        'products_count': products.count(),
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