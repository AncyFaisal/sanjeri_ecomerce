# # sanjay_app/views.py

# sanjay_app/views.py

from datetime import timedelta
import secrets
import time

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import render, redirect
# from google.oauth2 import id_token
# from google.auth.transport import requests as grequests
from django.utils import timezone
from django.contrib.auth.models import User
from ..models import CustomUser



# GOOGLE_CLIENT_ID = "77221304374-rpe32gue5hchc7tl1bda2ajh0j9bied6.apps.googleusercontent.com"
# GOOGLE_CLIENT_SECRET = "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"
# REDIRECT_URI = "http://127.0.0.1:8000/google/callback/"
# SCOPE = "openid email profile"


# def google_login(request):
#     """Redirect user to Google OAuth login page"""
#     auth_url = (
#         "https://accounts.google.com/o/oauth2/v2/auth?"
#         f"client_id={"77221304374-rpe32gue5hchc7tl1bda2ajh0j9bied6.apps.googleusercontent.com"}&"
#         f"redirect_uri={"http://127.0.0.1:8000/google/callback/"}&"
#         f"response_type=code&"
#         f"scope={SCOPE}"
#     )
#     return redirect(auth_url)

# def google_callback(request):
#     """Handle Google OAuth callback"""
#     code = request.GET.get("code")
#     if not code:
#         messages.error(request, "Google login failed.")
#         return redirect("user_login")

#     # Exchange code for token
#     token_url = "https://oauth2.googleapis.com/token"
#     data = {
#         "code": code,
#         "client_id": "77221304374-rpe32gue5hchc7tl1bda2ajh0j9bied6.apps.googleusercontent.com",
#         "client_secret":"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",
#         "redirect_uri":"http://127.0.0.1:8000/google/callback/",
#         "grant_type": "authorization_code",
#     }
#     r = requests.post(token_url, data=data)
#     token_data = r.json()
#     idinfo = id_token.verify_oauth2_token(token_data['id_token'], grequests.Request(), GOOGLE_CLIENT_ID)

#     email = idinfo.get("email")
#     name = idinfo.get("name")

#     # Check if user exists or create
#     user_model = User  # or CustomUser
#     user, created = user_model.objects.get_or_create(username=email, defaults={"email": email, "first_name": name})

#     login(request, user)
#     messages.success(request, "Logged in successfully with Google.")
#     return redirect("homepage")
# ---------------------------------------------------------------------------
User = get_user_model()

# ----------------------------
# OTP Helpers (shared)
# ----------------------------

def _otp_key(purpose: str, email: str) -> str:
    """Build a namespaced cache key so signup/forgot OTPs never clash."""
    return f"otp:{purpose}:{email}"

def generate_and_send_otp(email: str, username: str, purpose: str, ttl_seconds: int = 120) -> int:

# def generate_and_send_otp(email: str, purpose: str, ttl_seconds: int = 120) -> int:
    """
    Generates a 6-digit OTP, stores it in cache for `ttl_seconds`, and emails it.
    purpose: "signup" | "forgot" | "email_change" | "password_change"
    """
    otp = secrets.randbelow(900000) + 100000  # 100000..999999
    key = _otp_key(purpose, email)
    cache.set(key, {"otp": otp, "issued_at": int(time.time())}, ttl_seconds)

    if purpose == "signup":
        subject = "Verify Your Email - SANJERI"
        body = (f"Hi {username},\n\n"
        "Thank you for signing up with Sanjeri Perfumes!\n\n"
        f"Your One-Time Password (OTP) is: {otp}\n\n"
        f"This OTP is valid for {ttl_seconds // 60} minutes. "
        "Please do not share it with anyone.\n\n"
        "If you did not request this OTP, please ignore this email "
        "or contact our support team.\n\n"
        "We’re excited to have you join our community!\n\n"
        "Warm regards,\n"
        "The Sanjeri Perfumes Team")
        # Your signup OTP is {otp}. It will expire in {ttl_seconds // 60} minutes."
    elif purpose == "email_change":
        subject = "Verify Email Change - SANJERI"
        body = (
    f"Hi {username},\n\n"
    "You requested to change your registered email address.\n"
    f"Your verification OTP is {otp} and is valid for {ttl_seconds // 60} minutes.\n\n"
    "If this wasn’t you, please contact our support team.\n\n"
    "Warm regards,\n"
    "The Sanjeri Perfumes Team"
)
    elif purpose == "password_change":
        subject = "Verify Password Change - SANJERI"
        body = (f"Hi {username},\n\n"
    "You requested to change your password.\n"
    f"Your verification OTP is {otp}. It will expire in {ttl_seconds // 60} minutes.\n\n"
    "If this wasn’t you, please secure your account immediately.\n\n"
    "Warm regards,\n"
    "The Sanjeri Perfumes Team")
    else:  # forgot password
        subject = "Password Reset OTP - SANJERI"
        body = (
    f"Hi {username},\n\n"
    "We received a request to reset your password.\n"
    f"Use this OTP to continue: {otp}. It is valid for {ttl_seconds // 60} minutes.\n\n"
    "If you didn’t request this, you can safely ignore this email.\n\n"
    "Warm regards,\n"
    "The Sanjeri Perfumes Team"
)

    send_mail(subject, body, settings.EMAIL_HOST_USER, [email])
    return otp
# def generate_and_send_otp(email: str, purpose: str, ttl_seconds: int = 120) -> int:
#     """
#     Generates a 6-digit OTP, stores it in cache for `ttl_seconds`, and emails it.
#     purpose: "signup" | "forgot"
#     """
#     otp = secrets.randbelow(900000) + 100000  # 100000..999999
#     key = _otp_key(purpose, email)
#     cache.set(key, {"otp": otp, "issued_at": int(time.time())}, ttl_seconds)

#     if purpose == "signup":
#         subject = "Verify Your Email - SANJERI"
#         body = f"Your signup OTP is {otp}. It will expire in {ttl_seconds // 60} minutes."
#     else:
#         subject = "Password Reset OTP - SANJERI"
#         body = f"Your password reset OTP is {otp}. It will expire in {ttl_seconds // 60} minutes."

#     send_mail(subject, body, settings.EMAIL_HOST_USER, [email])
#     return otp

def get_otp_record(email: str, purpose: str):
    return cache.get(_otp_key(purpose, email))

def clear_otp(email: str, purpose: str):
    cache.delete(_otp_key(purpose, email))


# ----------------------------
# SIGNUP (with OTP verify + resend)
# ----------------------------

def user_signup(request):
    """
    Step 1: Collect details + password. Do NOT create user yet.
    Send OTP and store form data in session as 'pending_user'.
    """
    if request.method == "POST":
        # fname = request.POST.get("firstName")
        # lname = request.POST.get("lastName")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirmPassword")
        phone = request.POST.get("phone")
        # address = request.POST.get("address")
        # gender = request.POST.get("gender")
        agree = request.POST.get("agree")

        # Validations
        if not agree:
            messages.error(request, "You must agree to terms and conditions.")
            return redirect("user_signup")

        if password != confirm:
            messages.error(request, "Password and confirmation do not match.")
            return redirect("user_signup")

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("user_signup")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("user_signup")

        # Save data temporarily in session (server-side)
        request.session["pending_user"] = {
            # "first_name": fname,
            # "last_name": lname,
            "username": username,
            "email": email,
            "password": password,  # Will be hashed only after OTP verification
            "phone": phone,
            # "address": address,
            # "gender": gender,
            "status": "active",  # ADD THIS LINE - New users are active by default
            "wallet_balance": 0.00,  # ADD THIS LINE - Start with zero balance
        }
        request.session["otp_email"] = email  # for signup OTP flow

        # Send OTP
        generate_and_send_otp(email,username ,purpose="signup", ttl_seconds=120)
        messages.success(request, "OTP sent to your email. Please verify.")
        return redirect("verify_signup_otp")

    return render(request, "user_signup.html")


def verify_signup_otp(request):
    """
    Step 2: Verify OTP for signup.
    On success: create user using the data from 'pending_user'.
    """
    email = request.session.get("otp_email")
    if not email or not request.session.get("pending_user"):
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("user_signup")

    record = get_otp_record(email, "signup")
    expiry_time = None
    if record:
        # Provide expiry timestamp to the template (UNIX seconds)
        expiry_time = record["issued_at"] + 120

    if request.method == "POST":
        otp_entered = (request.POST.get("otp") or "").strip()
        record = get_otp_record(email, "signup")

        if not record:
            messages.error(request, "OTP expired or not found. Please resend and try again.")
            return redirect("verify_signup_otp")

        saved_otp = str(record["otp"])
        if str(otp_entered) != saved_otp:
            messages.error(request, "Invalid OTP.")
            return redirect("verify_signup_otp")

        # Create the user now with ALL fields including status
        data = request.session.get("pending_user")
        try:
            user = CustomUser.objects.create(
                # first_name=data["first_name"],
                # last_name=data["last_name"],
                username=data["username"],
                email=data["email"],
                phone=data.get("phone"),
                # address=data.get("address"),
                # gender=data.get("gender"),
                status=data.get("status", "active"),  # ADD THIS - status field
                wallet_balance=data.get("wallet_balance", 0.00),  # ADD THIS - wallet field
                password=make_password(data["password"]),
            )
        except Exception as e:
            messages.error(request, f"Could not create user: {e}")
            return redirect("user_signup")

        # Cleanup
        clear_otp(email, "signup")
        request.session.pop("pending_user", None)
        request.session.pop("otp_email", None)

        messages.success(request, "Signup successful! You can now log in.")
        return redirect("user_login")

    return render(request, "verify_signup_otp.html", {"expiry_time": expiry_time})


def resend_signup_otp(request):
    email = request.session.get("otp_email")
    pending_user = request.session.get("pending_user")

    if not email or not pending_user:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("user_signup")

    username = pending_user.get("username")

    generate_and_send_otp(email,username, purpose="signup", ttl_seconds=120)
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("verify_signup_otp")


# ----------------------------
# LOGIN / LOGOUT
# ----------------------------

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            # CHECK IF USER IS BLOCKED - CRITICAL SECURITY
            if user.status == 'blocked' or not user.is_active:
                messages.error(request, 'Your account has been blocked. Please contact administrator.')
                return redirect("user_login")
            
            login(request, user)
            
            # REDIRECT BASED ON USER TYPE
            if user.is_staff or user.is_superuser:
                # Admin users go to admin dashboard
                messages.success(request, f'Welcome back, Admin {user.first_name}!')
                return redirect("admin_dashboard")  # Make sure this URL exists
            else:
                # Regular users go to homepage
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect("homepage")
                
        messages.error(request, "Invalid credentials.")
        return redirect("user_login")

    return render(request, "user_login.html")


def user_logout(request):
    logout(request)
    # Clear old messages before adding new one
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    messages.success(request, "Successfully logged out.")
    return redirect("user_login")


# ----------------------------
# FORGOT PASSWORD (OTP + Resend + Reset)
# ----------------------------

def forgot_password(request):
    """
    Step 1: Ask for email. If exists, send OTP for 'forgot' purpose.
    """
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        try:
            user=User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email not registered.")
            return redirect("forgot_password")

        request.session["reset_email"] = email
        generate_and_send_otp(email,user.username,purpose="forgot", ttl_seconds=120)
        messages.success(request, "OTP sent to your email. Please verify.")
        return redirect("verify_otp")

    return render(request, "forgot_password.html")


def verify_reset_otp(request):
    """
    Step 2: Verify OTP for password reset.
    On success: redirect to reset_password page.
    
    """
    print("DEBUG: verify_reset_otp view called")
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect("forgot_password")

    record = get_otp_record(email, "forgot")
    expiry_time = None
    remaining_seconds = 0
    if record:
        expiry_time = record["issued_at"] + 120
        remaining_seconds = max(0, expiry_time - int(time.time()))
    
    if request.method == "POST":
        otp_entered = (request.POST.get("otp") or "").strip()
        record = get_otp_record(email, "forgot")

        if not record:
            messages.error(request, "OTP expired or not found. Please resend and try again.")
            return redirect("verify_reset_otp")

        if str(otp_entered) != str(record["otp"]):
            messages.error(request, "Invalid OTP.")
            return redirect("verify_otp")

        # Mark verified and proceed to reset form
        request.session["reset_verified"] = True
        clear_otp(email, "forgot")
        messages.success(request, "OTP verified. You can now reset your password.")
        return redirect("reset_password")

    return render(request, "verify_otp.html", {"expiry_time": expiry_time,"remaining_seconds": remaining_seconds,},)  # You can reuse the same template


def resend_reset_otp(request):
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect("forgot_password")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("forgot_password")

    generate_and_send_otp(email,user.username ,purpose="forgot", ttl_seconds=120)
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("verify_otp")


def reset_password(request):
    """
    Step 3: Reset password after OTP verification.
    Requires: session['reset_email'] and session['reset_verified'] == True
    """
    email = request.session.get("reset_email")
    verified = request.session.get("reset_verified", False)

    if not email or not verified:
        messages.error(request, "Unauthorized or expired session.")
        return redirect("forgot_password")

    if request.method == "POST":
        new_password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("forgot_password")

        # Cleanup session flags
        request.session.pop("reset_email", None)
        request.session.pop("reset_verified", None)

        messages.success(request, "Password reset successfully. Please log in.")
        return redirect("user_login")

    return render(request, "reset_password.html")





