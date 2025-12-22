# forms/product.py
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from ..models import Product, ProductVariant, Category
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'slug', 'description', 'main_image',
            'brand', 'fragrance_type', 'occasion',
            'category', 'is_featured', 'is_best_selling', 'is_new_arrival', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product SKU'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter slug'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter description'}),
            'main_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter brand'}),
            'fragrance_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter fragrance type'}),
            'occasion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter occasion'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_best_selling': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_new_arrival': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_main_image(self):
        main_image = self.cleaned_data.get('main_image')
        if main_image:
            # Validate file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(main_image.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Unsupported file format. Please use JPG, JPEG, PNG, or WebP.')
            
            # Validate file size (max 5MB)
            if main_image.size > 5 * 1024 * 1024:
                raise ValidationError('Image file too large ( > 5MB )')
                
        return main_image

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Process main image if provided
        if 'main_image' in self.changed_data and self.cleaned_data['main_image']:
            instance.main_image = self.process_image(
                self.cleaned_data['main_image'], 
                (800, 800),  # Target size for main image
                'main'
            )
        
        if commit:
            instance.save()
        return instance
    
    def process_image(self, image_file, target_size, image_type='main'):
        """Process and optimize uploaded image"""
        try:
            # Open image
            image = Image.open(image_file)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Calculate new dimensions while maintaining aspect ratio
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Create optimized image
            output = BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            # Create new file name
            name = os.path.splitext(image_file.name)[0]
            new_filename = f"{name}_optimized.jpg"
            
            return ContentFile(output.read(), new_filename)
            
        except Exception as e:
            # If processing fails, return original image
            print(f"Image processing error: {e}")
            return image_file


class ProductVariantForm(forms.ModelForm):
    DELETE = forms.BooleanField(
        required=False, 
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input delete-variant'})
    )
    
    class Meta:
        model = ProductVariant
        fields = ['volume_ml', 'gender', 'sku', 'price', 'discount_price', 'stock', 'variant_image', 'is_active']
        widgets = {
            'volume_ml': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Volume in ml',
                'min': '1'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Variant SKU'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price',
                'step': '0.01',
                'min': '0'
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Discount Price',
                'step': '0.01',
                'min': '0'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Stock quantity',
                'min': '0'
            }),
            'variant_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add DELETE field to the form
        if self.instance.pk:
            self.fields['DELETE'].label = f'Delete variant ({self.instance.sku})'

    def clean_variant_image(self):
        variant_image = self.cleaned_data.get('variant_image')
        if variant_image:
            # Validate file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(variant_image.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Unsupported file format. Please use JPG, JPEG, PNG, or WebP.')
            
            # Validate file size (max 5MB)
            if variant_image.size > 5 * 1024 * 1024:
                raise ValidationError('Image file too large ( > 5MB )')
                
        return variant_image

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discount_price = cleaned_data.get('discount_price')
        
        if discount_price and price and discount_price >= price:
            raise forms.ValidationError("Discount price must be less than regular price.")
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Process variant image if provided
        if 'variant_image' in self.changed_data and self.cleaned_data['variant_image']:
            instance.variant_image = self.process_image(
                self.cleaned_data['variant_image'], 
                (600, 600),  # Target size for variant image
                'variant'
            )
        
        if commit:
            instance.save()
        return instance
    
    def process_image(self, image_file, target_size, image_type='variant'):
        """Process and optimize uploaded image"""
        try:
            # Open image
            image = Image.open(image_file)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Calculate new dimensions while maintaining aspect ratio
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Create optimized image
            output = BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            # Create new file name
            name = os.path.splitext(image_file.name)[0]
            new_filename = f"{name}_optimized.jpg"
            
            return ContentFile(output.read(), new_filename)
            
        except Exception as e:
            # If processing fails, return original image
            print(f"Image processing error: {e}")
            return image_file


# Formset for variants
ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    fields=('volume_ml', 'gender', 'sku', 'price', 'discount_price', 'stock', 'variant_image', 'is_active'),
    extra=1,
    can_delete=True
)


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProductImageForm(forms.Form):
    images = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*"}),
        required=True,
        help_text="Upload at least 3 images"
    )

    def clean_images(self):
        images = self.files.getlist("images")
        if len(images) < 3:
            raise forms.ValidationError("Please upload at least 3 images.")
        
        # Validate each image
        for image in images:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(f'Unsupported file format for {image.name}. Please use JPG, JPEG, PNG, or WebP.')
            
            if image.size > 5 * 1024 * 1024:
                raise ValidationError(f'Image {image.name} is too large ( > 5MB )')
        
        return images


class ProductInlineForm(forms.ModelForm):
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2, 
            'class': 'form-control', 
            'placeholder': 'Enter product description (optional)'
        })
    )
    
    brand = forms.CharField(
        required=False,
        initial='Generic',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter brand name (optional)'
        })
    )
    
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'brand']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter product name'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter product SKU'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            if not self.initial.get('brand'):
                self.initial['brand'] = 'Generic'


# Update the Category formset
ProductFormSet = inlineformset_factory(
    Category,
    Product,
    form=ProductInlineForm,
    fields=('name', 'sku', 'description', 'brand'),
    extra=1,
    can_delete=False,
    max_num=1,
    validate_max=True
)