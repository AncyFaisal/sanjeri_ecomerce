from django.core.management.base import BaseCommand
from django.utils.text import slugify
from sanjeri_app.models.product import Product  # Replace 'your_app' with your actual app name

class Command(BaseCommand):
    help = 'Generate slugs for existing products that don\'t have slugs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate slugs for all products (even those that already have slugs)',
        )

    def handle(self, *args, **options):
        # Get products based on the option
        if options['all']:
            products = Product.objects.all()
            self.stdout.write(self.style.WARNING('Regenerating slugs for ALL products...'))
        else:
            products = Product.objects.filter(slug__isnull=True) | Product.objects.filter(slug='')
            self.stdout.write('Generating slugs only for products without slugs...')
        
        count = 0
        for product in products:
            # Generate base slug from product name
            base_slug = slugify(product.name)
            
            # If the product already has this slug and we're not regenerating all, skip
            if product.slug == base_slug and not options['all']:
                continue
                
            # Make sure slug is unique
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(id=product.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Update the product
            old_slug = product.slug
            product.slug = slug
            product.save()
            
            count += 1
            if old_slug:
                self.stdout.write(
                    self.style.SUCCESS(f'Updated slug: "{old_slug}" -> "{slug}" for "{product.name}"')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Generated slug: "{slug}" for "{product.name}"')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {count} products!')
        )