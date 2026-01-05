import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanjeri_project.settings')
django.setup()

from sanjeri_app.models import Product, ProductVariant, ProductImage

print('=== Checking Current Image Paths ===')
print()

# Check Product main images
products = Product.objects.all()
print('Product Main Images:')
for product in products:
    if product.main_image:
        print(f'  {product.name}: {product.main_image.name}')
print()

# Check ProductVariant images
variants = ProductVariant.objects.all()
print('Product Variant Images:')
for variant in variants:
    if variant.variant_image:
        print(f'  {variant.product.name} - {variant.volume_ml}ml: {variant.variant_image.name}')
print()

# Check ProductImage gallery
gallery = ProductImage.objects.all()
print('Product Gallery Images:')
for img in gallery:
    print(f'  {img.product.name}: {img.image.name}')
print()

# Check what files actually exist in media/
print('Files in media/products/:')
if os.path.exists('media/products/'):
    files = os.listdir('media/products/')[:10]
    for f in files:
        print(f'  {f}')
else:
    print('  media/products/ folder does not exist')
