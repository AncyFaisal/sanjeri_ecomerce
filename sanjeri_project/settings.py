"""
Django settings for sanjeri_project project.
"""

from pathlib import Path
import os
import dj_database_url
from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== SECURITY SETTINGS ====================
# Get SECRET_KEY from environment or generate
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure--^v2*dd7n=%tr0g%=s46wfv4!t3sl%u)p=9j4cq(wf!zr7h%3&')

# Debug from environment or default to False for production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ALLOWED_HOSTS - IMPORTANT FOR RENDER
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'ancyfaisal.pythonanywhere.com']

# ============== RENDER.COM PRODUCTION SETTINGS ==============
# Check if running on Render
if 'RENDER' in os.environ:
    # Security settings for production
    DEBUG = False
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Allowed hosts for Render
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if RENDER_EXTERNAL_HOSTNAME:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    ALLOWED_HOSTS.append('.onrender.com')
    
    # PostgreSQL database from Render
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600
        )
    }
    
    # Static files with Whitenoise
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    
    # Add Whitenoise to middleware (right after SecurityMiddleware)
    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'whitenoise.middleware.WhiteNoiseMiddleware',  # ADD THIS LINE
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'allauth.account.middleware.AccountMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'sanjeri_app',
    'newapp',
]

SITE_ID = 1  # UNCOMMENT THIS - IMPORTANT FOR ALLAUTH

# LOCAL DATABASE (only used when not on Render)
if 'RENDER' not in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'sanjeri_db',
            'USER': 'sanjeri_user',
            'PASSWORD': 'mypassword',   
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# ==================== REST OF YOUR SETTINGS ====================
# ... keep all your other settings below ...

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'sanjeri_app.context_processors.cart_and_wishlist_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'sanjeri_project.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (for local development)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Only for local development (Render uses STATIC_ROOT from above)
if 'RENDER' not in os.environ:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'sanjeri_app.CustomUser'

# Email configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "ancyfaisal54@gmail.com"
EMAIL_HOST_PASSWORD = "sxbk zcwq rjel hcki"

# Authentication backends
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True

# Social account settings
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = True

# Custom adapter
SOCIALACCOUNT_ADAPTER = 'sanjeri_app.adapters.CustomSocialAccountAdapter'

# Login/Logout URLs
LOGIN_REDIRECT_URL = 'homepage'
LOGOUT_REDIRECT_URL = 'user_login'
LOGIN_URL = '/user_login/'

# Social Account Providers
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': '77221304374-rpe32gue5hchc7tl1bda2ajh0j9bied6.apps.googleusercontent.com',
            'secret': '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',
            'key': ''
        }
    }
}

# Razorpay Configuration
# These will be overridden by environment variables on Render
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_1DP5mmOlF5G5ag')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'wFYmNv4Wt5ZbM7fE8qH3rK6pL9')

# Print Razorpay config check (only in development)
if DEBUG:
    print("=" * 50)
    print("RAZORPAY CONFIG CHECK:")
    print(f"Key ID: {RAZORPAY_KEY_ID}")
    print(f"Key Secret Length: {len(RAZORPAY_KEY_SECRET) if RAZORPAY_KEY_SECRET else 'Not set'}")
    print("=" * 50)

# PayPal Settings
PAYPAL_CLIENT_ID = 'YOUR_PAYPAL_CLIENT_ID'
PAYPAL_CLIENT_SECRET = 'YOUR_PAYPAL_SECRET'
PAYPAL_MODE = 'sandbox'