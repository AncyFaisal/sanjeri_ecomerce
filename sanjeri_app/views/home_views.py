from django.shortcuts import render
from django.core.paginator import Paginator
from ..models.home_models import HomeProduct, HomeCategory, HomeBrand, HomeRating
from django.db.models import Avg 


def homeproduct(request):
    products = HomeProduct.objects.filter(is_active=True)
    categories = HomeCategory.objects.all()
    brands = HomeBrand.objects.all()
    fragrance_families = ['Amber', 'Aquatic', 'Aromatic', 'Lavender', 'Vanilla', 'Musk', 
                           'Citrus', 'Floral', 'Fresh', 'Woody', 'Fruity']
    quantities = [50, 100, 200, 250, 300]

    # --- Filters ---
    category_filter = request.GET.getlist('category')
    if category_filter:
        products = products.filter(category_id__in=category_filter)

    brand_filter = request.GET.getlist('brand')
    if brand_filter:
        products = products.filter(brand_id__in=brand_filter)

    family_filter = request.GET.getlist('family')
    if family_filter:
        products = products.filter(fragrance_family__in=family_filter)

    quantity_filter = request.GET.getlist('quantity')
    if quantity_filter:
        products = products.filter(quantity__in=quantity_filter)

    min_price = request.GET.get('min_price')
    if min_price:
        products = products.filter(price__gte=min_price)

    max_price = request.GET.get('max_price')
    if max_price:
        products = products.filter(price__lte=max_price)

    # --- Search ---
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(name__icontains=search_query)

    # --- Sorting ---
    sort_option = request.GET.get('sort')
    if sort_option == 'price_asc':
        products = products.order_by('discount_price')
    elif sort_option == 'price_desc':
        products = products.order_by('-discount_price')
    elif sort_option == 'name_asc':
        products = products.order_by('name')
    elif sort_option == 'name_desc':
        products = products.order_by('-name')
    elif sort_option == 'popularity':
        products = products.order_by('-popularity')
    elif sort_option == 'ratings':
        products = products.annotate(avg_rating=Avg('ratings__rating')).order_by('-avg_rating')
    elif sort_option == 'new_arrival':
        products = products.order_by('-created_at')

    # --- Pagination ---
    paginator = Paginator(products, 5)  # 8 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    selected_categories = request.GET.getlist('category')
    selected_families = request.GET.getlist('family')
    selected_quantities = request.GET.getlist('quantity')
    selected_brands = request.GET.getlist('brand')
    selected_sort = request.GET.get('sort', '')

    context = {
        'products': page_obj,
        'categories': categories,
        'brands': brands,
        'fragrance_families': fragrance_families,
        'quantities': quantities,
        'selected_categories': selected_categories,
        'selected_families': selected_families,
        'selected_quantities': selected_quantities,
        'selected_brands': selected_brands,
        'selected_sort': selected_sort,
    }

    return render(request, 'commonhome.html', context)
