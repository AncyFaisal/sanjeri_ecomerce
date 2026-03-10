# sanjeri_app/views/referral_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from ..models.user_models import CustomUser
from ..models.referral import ReferralCoupon

@login_required
def referral_dashboard(request):
    """Show user's referral stats"""
    user = request.user
    
    # Get users referred by this user
    referrals = CustomUser.objects.filter(referred_by=user).order_by('-date_joined')
    
    # Get coupons earned
    coupons = ReferralCoupon.objects.filter(referrer=user).order_by('-created_at')
    
    # Generate referral link
    referral_link = request.build_absolute_uri(f"/user-signup/?ref={user.referral_code}")
    
    context = {
        'user': user,
        'referrals': referrals,
        'coupons': coupons,
        'referral_count': referrals.count(),
        'referral_link': referral_link,
        'referral_code': user.referral_code,
    }
    return render(request, 'user/referral_dashboard.html', context)

@login_required
def my_referral_coupons(request):
    """Show coupons earned from referrals"""
    user = request.user
    coupons = ReferralCoupon.objects.filter(referrer=user).order_by('-created_at')
    
    # Split into used and unused
    unused_coupons = coupons.filter(is_used=False)
    used_coupons = coupons.filter(is_used=True)
    
    context = {
        'unused_coupons': unused_coupons,
        'used_coupons': used_coupons,
    }
    return render(request, 'user/referral_coupons.html', context)