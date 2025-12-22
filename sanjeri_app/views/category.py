# views/category.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import Category, Product
from ..forms.category import CategoryForm, ProductFormSet

def admin_required(function):
    """
    Decorator to ensure user is admin/staff
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access admin panel.")
            return redirect('user_login')
        if not request.user.is_staff and not request.user.is_superuser: 
            messages.error(request, "You don't have permission to access this page.")
            return redirect('homepage')
        return function(request, *args, **kwargs)
    return wrapper

@admin_required
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        formset = ProductFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                # Save category first
                category = form.save()
                
                # Now save products
                products = formset.save(commit=False)
                for product in products:
                    product.category = category
                    product.save()
                
                messages.success(request, f"Category '{category.name}' with products added successfully!")
                return redirect('category_manage')
                    
            except Exception as e:
                messages.error(request, f"Error creating category: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
            
    else:
        form = CategoryForm()
        formset = ProductFormSet()
    
    return render(request, 'category_add.html', {
        'form': form,
        'formset': formset
    })
@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        formset = ProductFormSet(request.POST, instance=category)
        
        if form.is_valid() and formset.is_valid():
            try:
                # Save category first
                category = form.save()
                
                # Now save products
                products = formset.save(commit=False)
                for product in products:
                    product.category = category
                    product.save()
                
                # No need to handle deleted_objects since can_delete=False
                
                messages.success(request, f"Category '{category.name}' with products updated successfully!")
                return redirect('category_manage')
                    
            except Exception as e:
                messages.error(request, f"Error updating category: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm(instance=category)
        formset = ProductFormSet(instance=category)
    
    return render(request, 'category_edit.html', {
        'form': form,
        'formset': formset,
        'category': category
    })

@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_deleted = True
    category.save()
    messages.success(request, "Category deleted successfully!")
    return redirect('category_manage')

@admin_required
def category_manage(request):
    categories = Category.objects.filter(is_deleted=False).prefetch_related('products')
    
    # Get filter parameters
    query = request.GET.get('q', '')
    search_by = request.GET.get('search_by', 'all')
    status_filter = request.GET.get('status', '')
    featured_filter = request.GET.get('featured', '')
    sort_by = request.GET.get('sort', 'newest')
    
    # Apply search filter
    if query:
        if search_by == 'name':
            categories = categories.filter(name__icontains=query)
        elif search_by == 'product_name':
            categories = categories.filter(products__name__icontains=query).distinct()
        elif search_by == 'product_sku':
            categories = categories.filter(products__sku__icontains=query).distinct()
        else:  # all fields
            categories = categories.filter(
                Q(name__icontains=query) |
                Q(products__name__icontains=query) |
                Q(products__sku__icontains=query)
            ).distinct()
    
    # Apply status filter
    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)
    
    # Apply featured filter
    if featured_filter == 'yes':
        categories = categories.filter(is_featured=True)
    elif featured_filter == 'no':
        categories = categories.filter(is_featured=False)
    
    # Apply sorting
    if sort_by == 'oldest':
        categories = categories.order_by('id')
    elif sort_by == 'name_asc':
        categories = categories.order_by('name')
    elif sort_by == 'name_desc':
        categories = categories.order_by('-name')
    elif sort_by == 'sort_order':
        categories = categories.order_by('sort_order', 'name')
    else:  # newest first (default)
        categories = categories.order_by('-id')
    
    # Pagination
    paginator = Paginator(categories, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "query": query,
        "search_by": search_by,
        "status_filter": status_filter,
        "featured_filter": featured_filter,
        "sort_by": sort_by
    }
    return render(request, "category_manage.html", context)

# @login_required
@admin_required
def category_filter(request):
    # Placeholder for future expansion
    return render(request, "category_filter.html")

# @login_required
@admin_required
def category_success(request):
    return render(request, 'category_success.html')

