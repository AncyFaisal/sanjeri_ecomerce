"""
Django settings for sanjeri_project project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv  

# Load environment variables from .env file
load_dotenv()  

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure--^v2*dd7n=%tr0g%=s46wfv4!t3sl%u)p=9j4cq(wf!zr7h%3&')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# HTTPS settings for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False  
CSRF_COOKIE_SECURE = False
SECURE_PROXY_SSL_HEADER = None

# Allow all origins for testing
CORS_ALLOW_ALL_ORIGINS = True  # If you have django-cors-headers
# For localhost HTTPS
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '56.228.28.4']
# CSRF_TRUSTED_ORIGINS = [
#     'http://localhost:8000',
#     'https://localhost:8000',
#     'http://127.0.0.1:8000',
#     'https://127.0.0.1:8000',
# ]



# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize', 
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'sslserver', 
    'mathfilters',
    'sanjeri_app',
]
    # In settings.py, after INSTALLED_APPS
print("DEBUG: INSTALLED_APPS =", INSTALLED_APPS)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sanjeri_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'sanjeri_app.context_processors.cart_and_wishlist_context',
                'sanjeri_app.context_processors.wallet_balance',
                'sanjeri_app.context_processors.offer_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'sanjeri_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'sanjeri_db'),
        'USER': os.getenv('DB_USER', 'sanjeri_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'mypassword'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

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
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'sanjeri_app.CustomUser'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Email configuration - FROM .env
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@sanjeri.com')

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
            'client_id': os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY'),
            'secret': os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', ''),
            'key': ''
            
        }
    }
}

# For HTTPS
# SECURE_PROXY_SSL_HEADER = None
# SECURE_SSL_REDIRECT = False  # Set to True in production
SESSION_COOKIE_SECURE = False  # Set to True in production
CSRF_COOKIE_SECURE = False  # Set to True in production

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://localhost:8000',
    'https://127.0.0.1:8000',
    'http://209.38.123.149'
]


# Razorpay Configuration - Load from .env file
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

# Debug: Print keys (remove in production)
print(f"\n=== RAZORPAY CONFIGURATION ===")
print(f"Key ID loaded: {'YES' if RAZORPAY_KEY_ID else 'NO'}")
print(f"Key Secret loaded: {'YES' if RAZORPAY_KEY_SECRET else 'NO'}")
if RAZORPAY_KEY_ID:
    print(f"Key ID preview: {RAZORPAY_KEY_ID[:15]}...")


print(f"RAZORPAY_KEY_ID exists: {bool(RAZORPAY_KEY_ID)}")
print(f"RAZORPAY_KEY_SECRET exists: {bool(RAZORPAY_KEY_SECRET)}")


# Razorpay Test Cards for Development
RAZORPAY_TEST_CARDS = {
    'success': {
        'card_number': '4111111111111111',
        'card_holder': 'Test User',
        'expiry': '12/34',
        'cvv': '123'
    },
    'failure': {
        'card_number': '4000400040004000',
        'card_holder': 'Test User',
        'expiry': '12/34',
        'cvv': '123'
    }
}

# Test UPI ID
RAZORPAY_TEST_UPI = 'success@razorpay'