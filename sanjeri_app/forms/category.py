# forms/category.py
from django import forms
from django.forms import inlineformset_factory
from ..models import Category, Product

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'thumbnail', 'is_active', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

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
    
    # REMOVED volume_ml, gender, price, stock fields
    
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'brand']  # REMOVED price, stock, volume_ml, gender
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter product name'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter SKU'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for required fields
        if not self.instance.pk:  # Only for new products
            # Set default brand if not provided
            if not self.initial.get('brand'):
                self.initial['brand'] = 'Generic'

# Create formset with only ONE product form
ProductFormSet = inlineformset_factory(
    Category,
    Product,
    form=ProductInlineForm,
    fields=('name', 'sku', 'description', 'brand'),  # REMOVED price, stock, volume_ml, gender
    extra=1,  # Only one extra form
    can_delete=False,
    max_num=1,  # Maximum one product allowed
    validate_max=True
)

