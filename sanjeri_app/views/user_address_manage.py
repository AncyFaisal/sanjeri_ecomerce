# views/user_address_manage.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from ..forms import UserProfileForm, EmailChangeForm, PasswordChangeForm
from ..models import CustomUser
import secrets
import time
from ..views import generate_and_send_otp
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import User

from ..models import Address  # Add this import at the top
from ..forms import AddressForm  # Add this import at the top

@login_required
def address_list(request):
    """Display all addresses of the user"""
    addresses = Address.objects.filter(user=request.user)
    context = {
        'addresses': addresses,
        'title': 'My Addresses - Sanjeri'
    }
    return render(request, 'user_address_list.html', context)

@login_required
def add_address(request):
    """Add new address - handles both regular and AJAX requests"""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            
            # If setting as default or first address
            if form.cleaned_data.get('is_default') or not Address.objects.filter(user=request.user).exists():
                # Unset current default if setting new default
                if form.cleaned_data.get('is_default'):
                    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                address.is_default = True
                
            address.save()
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Address added successfully!',
                    'address_id': address.id
                })
            else:
                messages.success(request, 'Address added successfully!')
                next_url = request.GET.get('next', 'user_address_list')
                return redirect(next_url)
        else:
            # Handle AJAX form errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
            else:
                # For non-AJAX, render form with errors
                context = {
                    'form': form,
                    'title': 'Add New Address - Sanjeri'
                }
                return render(request, 'user_address_form.html', context)
    
    else:
        # GET request - show empty form
        form = AddressForm()
    
    # Only render template for non-AJAX GET requests
    context = {
        'form': form,
        'title': 'Add New Address - Sanjeri'
    }
    return render(request, 'user_address_form.html', context)

@login_required
def edit_address(request, address_id):
    """Edit existing address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('user_address_list')
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'address': address,
        'title': 'Edit Address - Sanjeri'
    }
    return render(request, 'user_address_form.html', context)

@login_required
def delete_address(request, address_id):
    """Delete address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        # If deleting default address, set another address as default if available
        if address.is_default:
            other_addresses = Address.objects.filter(user=request.user).exclude(id=address_id)
            if other_addresses.exists():
                new_default = other_addresses.first()
                new_default.is_default = True
                new_default.save()
        
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        return redirect('user_address_list')
    
    context = {
        'address': address,
        'title': 'Delete Address - Sanjeri'
    }
    return render(request, 'user_address_confirm_delete.html', context)

@login_required
def set_default_address(request, address_id):
    """Set address as default"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Unset current default
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    
    # Set new default
    address.is_default = True
    address.save()
    
    messages.success(request, 'Default address updated successfully!')
    return redirect('user_address_list')


@login_required
@require_POST
def add_address_ajax(request):
    """Add new address via AJAX for modal form"""
    form = AddressForm(request.POST)
    
    if form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        
        # If this is the first address or user wants to set as default, set it as default
        if not Address.objects.filter(user=request.user).exists() or form.cleaned_data.get('is_default'):
            # Unset current default if setting new default
            if form.cleaned_data.get('is_default'):
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address.is_default = True
                
        address.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Address added successfully!',
            'address_id': address.id
        })
    else:
        # Return form errors
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })
    
