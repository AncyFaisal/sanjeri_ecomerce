# sanjeri_app/views/admin_offer_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from ..models.offer_models import ProductOffer, CategoryOffer
from ..models.product import Product
from ..models.category import Category

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def product_offer_list(request):
    """List all product offers"""
    offers = ProductOffer.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        offers = offers.filter(
            Q(name__icontains=search_query) |
            Q(products__name__icontains=search_query)
        ).distinct()
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        offers = offers.filter(is_active=True)
    elif status_filter == 'inactive':
        offers = offers.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(offers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'offers': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'title': 'Product Offers - Admin'
    }
    return render(request, 'admin/offers/product_offer_list.html', context)

@login_required
@admin_required
def product_offer_create(request):
    """Create a new product offer"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        discount_percentage = request.POST.get('discount_percentage', 0)
        discount_fixed = request.POST.get('discount_fixed', 0)
        min_purchase_amount = request.POST.get('min_purchase_amount', 0)
        max_discount = request.POST.get('max_discount') or None
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        is_active = request.POST.get('is_active') == 'on'
        usage_limit = request.POST.get('usage_limit', 0)
        product_ids = request.POST.getlist('products')
        
        # Validation
        if not name:
            messages.error(request, "Offer name is required.")
            return redirect('product_offer_create')
        
        if not valid_from or not valid_to:
            messages.error(request, "Validity dates are required.")
            return redirect('product_offer_create')
        
        if discount_percentage == '0' and discount_fixed == '0':
            messages.error(request, "Either percentage or fixed discount must be provided.")
            return redirect('product_offer_create')
        
        if discount_percentage != '0' and discount_fixed != '0':
            messages.error(request, "Cannot use both percentage and fixed discount. Choose one.")
            return redirect('product_offer_create')
        
        # Create offer
        offer = ProductOffer.objects.create(
            name=name,
            description=description,
            discount_percentage=discount_percentage,
            discount_fixed=discount_fixed,
            min_purchase_amount=min_purchase_amount,
            max_discount=max_discount,
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=is_active,
            usage_limit=usage_limit,
            apply_to_all_variants=True
        )
        
        # Add products
        if product_ids:
            offer.products.set(product_ids)
        
        messages.success(request, f"Product offer '{name}' created successfully!")
        return redirect('product_offer_list')
    
    products = Product.objects.filter(is_active=True, is_deleted=False)
    context = {
        'products': products,
        'title': 'Create Product Offer'
    }
    return render(request, 'admin/offers/product_offer_form.html', context)

@login_required
@admin_required
def product_offer_edit(request, offer_id):
    """Edit a product offer"""
    offer = get_object_or_404(ProductOffer, id=offer_id)
    
    if request.method == 'POST':
        offer.name = request.POST.get('name')
        offer.description = request.POST.get('description', '')
        offer.discount_percentage = request.POST.get('discount_percentage', 0)
        offer.discount_fixed = request.POST.get('discount_fixed', 0)
        offer.min_purchase_amount = request.POST.get('min_purchase_amount', 0)
        offer.max_discount = request.POST.get('max_discount') or None
        offer.valid_from = request.POST.get('valid_from')
        offer.valid_to = request.POST.get('valid_to')
        offer.is_active = request.POST.get('is_active') == 'on'
        offer.usage_limit = request.POST.get('usage_limit', 0)
        offer.apply_to_all_variants = request.POST.get('apply_to_all_variants') == 'on'
        
        product_ids = request.POST.getlist('products')
        offer.products.set(product_ids)
        
        offer.save()
        messages.success(request, f"Offer '{offer.name}' updated successfully!")
        return redirect('product_offer_list')
    
    products = Product.objects.filter(is_active=True, is_deleted=False)
    selected_products = offer.products.values_list('id', flat=True)
    
    context = {
        'offer': offer,
        'products': products,
        'selected_products': list(selected_products),
        'title': f'Edit {offer.name}'
    }
    return render(request, 'admin/offers/product_offer_form.html', context)

@login_required
@admin_required
def product_offer_delete(request, offer_id):
    """Delete a product offer"""
    offer = get_object_or_404(ProductOffer, id=offer_id)
    
    if request.method == 'POST':
        offer.delete()
        messages.success(request, f"Offer '{offer.name}' deleted successfully!")
    
    return redirect('product_offer_list')

@login_required
@admin_required
def product_offer_toggle_status(request, offer_id):
    """Toggle offer active status"""
    offer = get_object_or_404(ProductOffer, id=offer_id)
    
    if request.method == 'POST':
        offer.is_active = not offer.is_active
        offer.save()
        status = "activated" if offer.is_active else "deactivated"
        messages.success(request, f"Offer '{offer.name}' {status} successfully!")
    
    return redirect('product_offer_list')

# Category Offer Views
@login_required
@admin_required
def category_offer_list(request):
    """List all category offers"""
    offers = CategoryOffer.objects.all().order_by('-created_at')
    
    search_query = request.GET.get('search', '')
    if search_query:
        offers = offers.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        offers = offers.filter(is_active=True)
    elif status_filter == 'inactive':
        offers = offers.filter(is_active=False)
    
    paginator = Paginator(offers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'offers': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'title': 'Category Offers - Admin'
    }
    return render(request, 'admin/offers/category_offer_list.html', context)

@login_required
@admin_required
def category_offer_create(request):
    """Create a new category offer"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category')
        discount_percentage = request.POST.get('discount_percentage', 0)
        discount_fixed = request.POST.get('discount_fixed', 0)
        min_purchase_amount = request.POST.get('min_purchase_amount', 0)
        max_discount = request.POST.get('max_discount') or None
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        is_active = request.POST.get('is_active') == 'on'
        usage_limit = request.POST.get('usage_limit', 0)
        
        # Validation
        if not name:
            messages.error(request, "Offer name is required.")
            return redirect('category_offer_create')
        
        if not category_id:
            messages.error(request, "Please select a category.")
            return redirect('category_offer_create')
        
        if not valid_from or not valid_to:
            messages.error(request, "Validity dates are required.")
            return redirect('category_offer_create')
        
        if discount_percentage == '0' and discount_fixed == '0':
            messages.error(request, "Either percentage or fixed discount must be provided.")
            return redirect('category_offer_create')
        
        if discount_percentage != '0' and discount_fixed != '0':
            messages.error(request, "Cannot use both percentage and fixed discount. Choose one.")
            return redirect('category_offer_create')
        
        category = get_object_or_404(Category, id=category_id)
        
        # Create offer
        offer = CategoryOffer.objects.create(
            name=name,
            description=description,
            category=category,
            discount_percentage=discount_percentage,
            discount_fixed=discount_fixed,
            min_purchase_amount=min_purchase_amount,
            max_discount=max_discount,
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=is_active,
            usage_limit=usage_limit,
            
        )
        
        messages.success(request, f"Category offer '{name}' created successfully!")
        return redirect('category_offer_list')
    
    categories = Category.objects.filter(is_active=True, is_deleted=False)
    context = {
        'categories': categories,
        'title': 'Create Category Offer'
    }
    return render(request, 'admin/offers/category_offer_form.html', context)

@login_required
@admin_required
def category_offer_edit(request, offer_id):
    """Edit a category offer"""
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    
    if request.method == 'POST':
        offer.name = request.POST.get('name')
        offer.description = request.POST.get('description', '')
        category_id = request.POST.get('category')
        offer.category = get_object_or_404(Category, id=category_id)
        offer.discount_percentage = request.POST.get('discount_percentage', 0)
        offer.discount_fixed = request.POST.get('discount_fixed', 0)
        offer.min_purchase_amount = request.POST.get('min_purchase_amount', 0)
        offer.max_discount = request.POST.get('max_discount') or None
        offer.valid_from = request.POST.get('valid_from')
        offer.valid_to = request.POST.get('valid_to')
        offer.is_active = request.POST.get('is_active') == 'on'
        offer.usage_limit = request.POST.get('usage_limit', 0)
        

        offer.save()
        messages.success(request, f"Offer '{offer.name}' updated successfully!")
        return redirect('category_offer_list')
    
    categories = Category.objects.filter(is_active=True, is_deleted=False)
    context = {
        'offer': offer,
        'categories': categories,
        'title': f'Edit {offer.name}'
    }
    return render(request, 'admin/offers/category_offer_form.html', context)

@login_required
@admin_required
def category_offer_delete(request, offer_id):
    """Delete a category offer"""
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    
    if request.method == 'POST':
        offer.delete()
        messages.success(request, f"Offer '{offer.name}' deleted successfully!")
    
    return redirect('category_offer_list')

@login_required
@admin_required
def category_offer_toggle_status(request, offer_id):
    """Toggle category offer active status"""
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    
    if request.method == 'POST':
        offer.is_active = not offer.is_active
        offer.save()
        status = "activated" if offer.is_active else "deactivated"
        messages.success(request, f"Offer '{offer.name}' {status} successfully!")
    
    return redirect('category_offer_list')