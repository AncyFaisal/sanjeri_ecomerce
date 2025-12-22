# views/product.py - COMPLETE UPDATE

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models.product import Product, ProductVariant, ProductImage, Category
from ..forms.product import ProductForm, ProductVariantFormSet, ProductVariantForm  # Fixed import
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.http import Http404


def product_list(request):
    query = request.GET.get("q", "")
    search_by = request.GET.get("search_by", "all")
    
    # Get all filter parameters
    category_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")
    gender_filter = request.GET.get("gender", "")
    featured_filter = request.GET.get("featured", "")
    best_selling_filter = request.GET.get("best_selling", "")
    new_arrival_filter = request.GET.get("new_arrival", "")
    stock_filter = request.GET.get("stock", "")
    sort_by = request.GET.get("sort", "newest")
    
    # Use the manager to automatically filter out deleted products
    products = Product.objects.all().select_related('category')
    categories = Category.objects.filter(is_active=True, is_deleted=False)

    # Apply search filter
    if query:
        if search_by == "name":
            products = products.filter(name__icontains=query)
        elif search_by == "id":
            if query.isdigit():
                products = products.filter(id=int(query))
            else:
                products = products.none()
        elif search_by == "sku":
            products = products.filter(sku__icontains=query)
        elif search_by == "category":
            products = products.filter(category__name__icontains=query)
        elif search_by == "brand":
            products = products.filter(brand__icontains=query)
        else:  # search all fields
            products = products.filter(
                Q(id__iexact=query) |
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(brand__icontains=query) |
                Q(category__name__icontains=query)
            )
    
    # Apply category filter
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Apply status filter
    if status_filter == "active":
        products = products.filter(is_active=True)
    elif status_filter == "inactive":
        products = products.filter(is_active=False)
    
    # Apply gender filter
    if gender_filter:
        products = products.filter(variants__gender=gender_filter, variants__is_active=True).distinct()
    
    # Apply featured filter
    if featured_filter == "yes":
        products = products.filter(is_featured=True)
    elif featured_filter == "no":
        products = products.filter(is_featured=False)
    
    # Apply best selling filter
    if best_selling_filter == "yes":
        products = products.filter(is_best_selling=True)
    elif best_selling_filter == "no":
        products = products.filter(is_best_selling=False)
    
    # Apply new arrival filter
    if new_arrival_filter == "yes":
        products = products.filter(is_new_arrival=True)
    elif new_arrival_filter == "no":
        products = products.filter(is_new_arrival=False)
    
    # Apply stock filter
    if stock_filter == "in_stock":
        products = products.filter(variants__stock__gt=0, variants__is_active=True).distinct()
    elif stock_filter == "low_stock":
        products = products.filter(variants__stock__gt=0, variants__stock__lte=10, variants__is_active=True).distinct()
    elif stock_filter == "out_of_stock":
        products = products.filter(variants__stock=0, variants__is_active=True).distinct()
    
    # Apply sorting
    if sort_by == "oldest":
        products = products.order_by("created_at")
    elif sort_by == "name_asc":
        products = products.order_by("name")
    elif sort_by == "name_desc":
        products = products.order_by("-name")
    elif sort_by == "price_high":
        products = sorted(products, key=lambda p: p.max_price, reverse=True)
    elif sort_by == "price_low":
        products = sorted(products, key=lambda p: p.min_price)
    elif sort_by == "stock_high":
        products = sorted(products, key=lambda p: p.total_stock, reverse=True)
    elif sort_by == "stock_low":
        products = sorted(products, key=lambda p: p.total_stock)
    else:  # newest first (default)
        products = products.order_by("-created_at")

    # Get count of deleted products for the trash badge
    deleted_products_count = Product.objects.deleted().count()

    paginator = Paginator(products, 5)
    page = request.GET.get('page')

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    context = {
        "page_obj": products_page,
        "categories": categories,
        "query": query,
        "search_by": search_by,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "gender_filter": gender_filter,
        "featured_filter": featured_filter,
        "best_selling_filter": best_selling_filter,
        "new_arrival_filter": new_arrival_filter,
        "stock_filter": stock_filter,
        "sort_by": sort_by,
        "deleted_products_count": deleted_products_count,
    }
    return render(request, "product_list.html", context)


def product_add(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        variant_formset = ProductVariantFormSet(request.POST, request.FILES)
        
        if form.is_valid() and variant_formset.is_valid():
            try:
                product = form.save(commit=False)
                product.is_deleted = False
                product.is_active = True
                product.save()
                
                # Save variants
                variants = variant_formset.save(commit=False)
                for variant in variants:
                    variant.product = product
                    variant.is_active = True
                    variant.is_deleted = False
                    variant.save()

                # Handle additional images with processing
                images = request.FILES.getlist('images')
                if len(images) < 3:
                    messages.error(request, "Please upload at least 3 images.")
                    return render(request, 'product_add.html', {
                        'form': form, 
                        'variant_formset': variant_formset
                    })

                for img in images:
                    try:
                        # Process each additional image
                        image = Image.open(img)
                        image = image.convert("RGB")
                        
                        # Resize to optimal size
                        image.thumbnail((600, 600), Image.Resampling.LANCZOS)
                        
                        # Optimize and save
                        buffer = BytesIO()
                        image.save(buffer, format="JPEG", quality=85, optimize=True)
                        buffer.seek(0)
                        
                        product_image = ProductImage(
                            product=product,
                            image=ContentFile(buffer.read(), f"optimized_{img.name}")
                        )
                        if not product.images.exists():
                            product_image.is_default = True
                        product_image.save()
                        
                    except Exception as e:
                        print(f"Error processing image {img.name}: {e}")
                        messages.warning(request, f"Could not process image {img.name}")
                        continue

                messages.success(request, "Product added successfully!")
                return redirect("product_list")
                
            except Exception as e:
                print(f"DEBUG: Error creating product - {e}")
                messages.error(request, f"Error creating product: {e}")
        else:
            print("DEBUG: Form errors:", form.errors)
            print("DEBUG: Variant formset errors:", variant_formset.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
        variant_formset = ProductVariantFormSet()

    return render(request, 'product_add.html', {
        'form': form,
        'variant_formset': variant_formset
    })

# views/product.py
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        variant_formset = ProductVariantFormSet(request.POST, request.FILES, instance=product)
        
        if form.is_valid() and variant_formset.is_valid():
            try:
                # Save the main product
                product = form.save()
                
                # Handle variants with soft delete
                instances = variant_formset.save(commit=False)
                
                for instance in instances:
                    # Check if this instance should be soft deleted
                    if variant_formset._should_delete_form(form) if hasattr(variant_formset, '_should_delete_form') else False:
                        # Soft delete the variant
                        instance.is_deleted = True
                        instance.is_active = False
                    else:
                        # Ensure new variants are not marked as deleted
                        if not instance.pk:
                            instance.is_deleted = False
                    
                    instance.product = product
                    instance.save()
                
                # Handle additional images
                images = request.FILES.getlist('images')
                for img in images:
                    try:
                        image = Image.open(img)
                        image = image.convert("RGB")
                        image = image.resize((600, 600))
                        buffer = BytesIO()
                        image.save(buffer, format="JPEG", quality=85)
                        buffer.seek(0)
                        
                        product_image = ProductImage(
                            product=product,
                            image=ContentFile(buffer.read(), img.name)
                        )
                        if not product.images.exists():
                            product_image.is_default = True
                        product_image.save()
                        
                    except Exception as e:
                        print(f"Error processing image {img.name}: {e}")
                        continue

                messages.success(request, "Product updated successfully!")
                return redirect('product_list')
                
            except Exception as e:
                print(f"DEBUG: Error updating product - {e}")
                messages.error(request, f"Error updating product: {e}")
        else:
            print("DEBUG: Form errors:", form.errors)
            print("DEBUG: Variant formset errors:", variant_formset.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=product)
        # Only show non-deleted variants in the formset
        variant_formset = ProductVariantFormSet(
            instance=product, 
            queryset=product.variants.filter(is_deleted=False)
        )
    
    return render(request, 'product_edit.html', {
        'form': form, 
        'product': product,
        'variant_formset': variant_formset
    })

def product_soft_delete(request, pk):
    """Soft delete a product"""
    product = get_object_or_404(Product, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        product.is_deleted = True
        product.is_active = False
        product.save()
        
        # Also soft delete all variants
        product.variants.update(is_deleted=True, is_active=False)
        
        messages.success(request, f"Product '{product.name}' has been moved to trash.")
        return redirect('product_list')
    
    return render(request, 'product_confirm_delete.html', {'product': product})


def product_restore(request, pk):
    """Restore a soft-deleted product"""
    product = get_object_or_404(Product.objects.with_deleted(), pk=pk, is_deleted=True)
    
    product.is_deleted = False
    product.save()
    
    # Also restore all variants
    product.variants.update(is_deleted=False)
    
    messages.success(request, f"Product '{product.name}' has been restored.")
    return redirect('product_trash')


def product_permanent_delete(request, pk):
    """Permanently delete a product"""
    product = get_object_or_404(Product.objects.with_deleted(), pk=pk, is_deleted=True)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' has been permanently deleted.")
        return redirect('product_trash')
    
    return render(request, 'product_permanent_delete.html', {'product': product})


def product_trash(request):
    """View for deleted products"""
    deleted_products = Product.objects.deleted().select_related('category')
    
    # Add search functionality for trash
    query = request.GET.get("q", "")
    if query:
        deleted_products = deleted_products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(brand__icontains=query)
        )
    
    context = {
        'deleted_products': deleted_products,
        'query': query
    }
    return render(request, 'product_trash.html', context)


def product_detail(request, product_id):
    """
    Product detail page - shows all product information
    """
    try:
        product = get_object_or_404(
            Product, 
            id=product_id,
            is_active=True, 
            is_deleted=False
        )
        
        variants = product.variants.filter(is_active=True)
        product_images = product.images.all()
        
        primary_image = product_images.filter(is_default=True).first()
        if not primary_image and product_images:
            primary_image = product_images.first()
        
        related_products = Product.objects.filter(
            category=product.category,
            is_active=True,
            is_deleted=False
        ).exclude(id=product.id)[:4]
        
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': product.category.name, 'url': '#'},
            {'name': product.name, 'url': '#'}
        ]
        
        discount_percentage = 0
        if variants.exists():
            variant = variants.first()
            if variant.discount_price and variant.price:
                discount_percentage = int(((variant.price - variant.discount_price) / variant.price) * 100)
        
        context = {
            'product': product,
            'variants': variants,
            'product_images': product_images,
            'primary_image': primary_image,
            'related_products': related_products,
            'breadcrumbs': breadcrumbs,
            'discount_percentage': discount_percentage,
            'title': f'{product.name} - Sanjeri'
        }
        
        return render(request, 'product_detail.html', context)
        
    except Exception as e:
        print(f"Error in product_detail: {e}")
        return render(request, '404.html', status=404)
    
    # views/product.py
def variant_soft_delete(request, product_pk, variant_pk):
    """Soft delete an individual variant"""
    variant = get_object_or_404(ProductVariant, pk=variant_pk, product_id=product_pk, is_deleted=False)
    
    if request.method == 'POST':
        variant.is_deleted = True
        variant.is_active = False
        variant.save()
        
        messages.success(request, f"Variant {variant.sku} has been moved to trash.")
        return redirect('product_edit', pk=product_pk)
    
    return render(request, 'variant_confirm_delete.html', {'variant': variant})


def variant_restore(request, product_pk, variant_pk):
    """Restore a soft-deleted variant"""
    variant = get_object_or_404(ProductVariant.objects.with_deleted(), pk=variant_pk, product_id=product_pk, is_deleted=True)
    
    variant.is_deleted = False
    variant.save()
    
    messages.success(request, f"Variant {variant.sku} has been restored.")
    return redirect('product_edit', pk=product_pk)


def variant_edit(request, product_pk, variant_pk):
    """Edit an individual variant"""
    product = get_object_or_404(Product, pk=product_pk, is_deleted=False)
    variant = get_object_or_404(ProductVariant, pk=variant_pk, product=product, is_deleted=False)
    
    if request.method == 'POST':
        form = ProductVariantForm(request.POST, request.FILES, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, "Variant updated successfully!")
            return redirect('product_edit', pk=product_pk)
    else:
        form = ProductVariantForm(instance=variant)
    
    return render(request, 'variant_edit.html', {
        'form': form,
        'product': product,
        'variant': variant
    })