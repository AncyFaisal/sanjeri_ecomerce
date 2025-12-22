# sanjay_app/user_forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from ..models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    agree = forms.BooleanField(required=True, label="I agree to the terms")

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username", "email", "phone", "address", "gender", "password1", "password2"]

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")
    password = forms.CharField(widget=forms.PasswordInput())


class UserSearchForm(forms.Form):
    search_query = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, phone or ID...'
        })
    )

class UserFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('active', 'Active'),
        ('blocked', 'Blocked'),
    ]
    
    ORDERS_CHOICES = [
        ('', 'All'),
        ('10+', 'More than 10'),
        ('5-10', '5 to 10'),
        ('1-5', '1 to 5'),
        ('0', '0'),
    ]
    
    SPENT_CHOICES = [
        ('', 'All'),
        ('5000+', 'Above ₹5000'),
        ('1000-5000', '₹1000 to ₹5000'),
        ('0-1000', 'Below ₹1000'),
    ]
    
    PAYMENT_CHOICES = [
        ('', 'All Methods'),
        ('UPI', 'UPI'),
        ('COD', 'Cash on Delivery'),
        ('Card', 'Credit/Debit Card'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    registration_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    registration_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    total_orders = forms.ChoiceField(
        choices=ORDERS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    total_spent = forms.ChoiceField(
        choices=SPENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )