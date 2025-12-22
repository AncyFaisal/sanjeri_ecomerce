# views.py/user_userprofile_manage.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from ..forms import UserProfileForm, EmailChangeForm, PasswordChangeForm
from ..models import CustomUser,Order,OrderItem
import secrets
import time
from ..views import generate_and_send_otp,get_otp_record,clear_otp
from datetime import timedelta
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import User


@login_required
def user_profile(request):
    """Display user profile details"""
    user = request.user
    context = {
        'user': user,
        'title': 'My Profile - Sanjeri'
    }
    return render(request, 'user_profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile (without email)"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            # Handle profile image upload
            if 'profile_image' in request.FILES:
                profile_image = request.FILES['profile_image']
                fs = FileSystemStorage(location='media/profile_images/')
                filename = fs.save(f"user_{user.id}_{profile_image.name}", profile_image)
                user.profile_image = f'profile_images/{filename}'
            
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
        'title': 'Edit Profile - Sanjeri'
    }
    return render(request, 'user_edit_profile.html', context)

@login_required
def change_email(request):
    """Change email with OTP verification"""
    user = request.user
    
    if request.method == 'POST':
        form = EmailChangeForm(request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']
            current_password = form.cleaned_data['current_password']
            
            # Verify current password
            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('user_change_email')
            
            # Check if email already exists
            if CustomUser.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, 'This email is already registered.')
                return redirect('user_change_email')
            
            # Store email change request in session
            request.session['pending_email'] = new_email
            request.session['email_change_user_id'] = user.id
            
            # Send OTP for email verification
            generate_and_send_otp(new_email, purpose="email_change", ttl_seconds=120)
            messages.success(request, 'OTP sent to your new email. Please verify.')
            return redirect('verify_email_change')
    else:
        form = EmailChangeForm()
    
    context = {
        'form': form,
        'title': 'Change Email - Sanjeri'
    }
    return render(request, 'user_change_email.html', context)

@login_required
def verify_email_change(request):
    """Verify OTP for email change"""
    pending_email = request.session.get('pending_email')
    user_id = request.session.get('email_change_user_id')
    
    if not pending_email or not user_id:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('change_email')
    
    # Get OTP record
    record = get_otp_record(pending_email, "email_change")
    expiry_time = None
    if record:
        expiry_time = record["issued_at"] + 120
    
    if request.method == 'POST':
        otp_entered = (request.POST.get("otp") or "").strip()
        record = get_otp_record(pending_email, "email_change")

        if not record:
            messages.error(request, "OTP expired or not found. Please resend and try again.")
            return redirect('verify_email_change')

        if str(otp_entered) != str(record["otp"]):
            messages.error(request, "Invalid OTP.")
            return redirect('verify_email_change')

        # Update user email
        try:
            user = CustomUser.objects.get(id=user_id)
            user.email = pending_email
            user.save()
            
            # Cleanup
            clear_otp(pending_email, "email_change")
            request.session.pop('pending_email', None)
            request.session.pop('email_change_user_id', None)
            
            messages.success(request, 'Email updated successfully!')
            return redirect('user_profile')
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('change_email')
    
    context = {
        'expiry_time': expiry_time,
        'email': pending_email,
        'title': 'Verify Email Change - Sanjeri'
    }
    return render(request, 'user_verify_email_change.html', context)

@login_required
def resend_email_change_otp(request):
    """Resend OTP for email change"""
    pending_email = request.session.get('pending_email')
    if not pending_email:
        messages.error(request, "Session expired. Please try again.")
        return redirect('change_email')

    generate_and_send_otp(pending_email, purpose="email_change", ttl_seconds=120)
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_email_change')

@login_required
def change_password(request):
    """Change password with OTP verification"""
    user = request.user
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            
            # Verify current password
            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('change_password')
            
            # Store password change request in session
            request.session['pending_password'] = new_password
            request.session['password_change_user_id'] = user.id
            
            # Send OTP for verification
            generate_and_send_otp(user.email, purpose="password_change", ttl_seconds=120)
            messages.success(request, 'OTP sent to your email. Please verify to change password.')
            return redirect('verify_password_change')
    else:
        form = PasswordChangeForm()
    
    context = {
        'form': form,
        'title': 'Change Password - Sanjeri'
    }
    return render(request, 'user_change_password.html', context)

@login_required
def verify_password_change(request):
    """Verify OTP for password change"""
    pending_password = request.session.get('pending_password')
    user_id = request.session.get('password_change_user_id')
    
    if not pending_password or not user_id:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('change_password')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get OTP record
    record = get_otp_record(user.email, "password_change")
    expiry_time = None
    if record:
        expiry_time = record["issued_at"] + 120
    
    if request.method == 'POST':
        otp_entered = (request.POST.get("otp") or "").strip()
        record = get_otp_record(user.email, "password_change")

        if not record:
            messages.error(request, "OTP expired or not found. Please resend and try again.")
            return redirect('verify_password_change')

        if str(otp_entered) != str(record["otp"]):
            messages.error(request, "Invalid OTP.")
            return redirect('verify_password_change')

        # Update user password
        try:
            user.set_password(pending_password)
            user.save()
            
            # Update session auth hash
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            # Cleanup
            clear_otp(user.email, "password_change")
            request.session.pop('pending_password', None)
            request.session.pop('password_change_user_id', None)
            
            messages.success(request, 'Password changed successfully!')
            return redirect('user_profile')
            
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')
            return redirect('change_password')
    
    context = {
        'expiry_time': expiry_time,
        'email': user.email,
        'title': 'Verify Password Change - Sanjeri'
    }
    return render(request, 'user_verify_password_change.html', context)

@login_required
def resend_password_change_otp(request):
    """Resend OTP for password change"""
    user_id = request.session.get('password_change_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect('change_password')
    
    user = get_object_or_404(CustomUser, id=user_id)
    generate_and_send_otp(user.email, purpose="password_change", ttl_seconds=120)
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_password_change')

@login_required
def order_history(request):
    """Display user's order history using the new Order model"""
    try:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        context = {
            'orders': orders,
            'title': 'Order History - Sanjeri'
        }
        return render(request, 'user_order_history.html', context)
        
    except Exception as e:
        # Fallback if there's any error
        messages.error(request, 'There was an error loading your orders. Please try again.')
        print(f"Order history error: {e}")  # For debugging
        return render(request, 'user_order_history.html', {'orders': [], 'title': 'Order History - Sanjeri'})

@login_required
def cancel_order(request, order_id):
    """Cancel order - redirect to new cancel order system"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        if order.can_be_cancelled:
            # For now, just mark as cancelled
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Order #{order.order_number} has been cancelled.')
        else:
            messages.error(request, 'This order cannot be cancelled.')
            
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
    
    return redirect('order_history')