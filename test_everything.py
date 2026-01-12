# test_everything.py
import os
from dotenv import load_dotenv

print("="*60)
print("COMPLETE TEST")
print("="*60)

# 1. Test .env file
print("\n1. Testing .env file...")
load_dotenv()

key_id = os.getenv('RAZORPAY_KEY_ID')
key_secret = os.getenv('RAZORPAY_KEY_SECRET')

print(f"   RAZORPAY_KEY_ID from .env: {key_id}")
print(f"   Should be: rzp_test_S2X7LdXgRrfZBx")
print(f"   Match: {key_id == 'rzp_test_S2X7LdXgRrfZBx'}")

# 2. Test Django settings
print("\n2. Testing Django settings...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanjeri_project.settings')

import django
django.setup()

from django.conf import settings

print(f"   settings.RAZORPAY_KEY_ID: {settings.RAZORPAY_KEY_ID}")
print(f"   Matches .env: {settings.RAZORPAY_KEY_ID == key_id}")

# 3. Test Razorpay API
print("\n3. Testing Razorpay API...")
try:
    import razorpay
    client = razorpay.Client(auth=(key_id, key_secret))
    
    order = client.order.create({
        'amount': 100,  # ₹1
        'currency': 'INR',
        'payment_capture': 1,
        'receipt': 'test_001'
    })
    
    print(f"   ✅ SUCCESS! Razorpay is working!")
    print(f"   Order ID: {order['id']}")
    print(f"   Amount: ₹{order['amount']/100}")
    
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print(f"   Using key: {key_id}")

print("\n" + "="*60)
print("SUMMARY:")
if key_id == 'rzp_test_S2X7LdXgRrfZBx' and settings.RAZORPAY_KEY_ID == key_id:
    print("✅ Everything is CORRECT!")
    print("   Your payment gateway is ready!")
else:
    print("❌ Something is wrong.")
    print("   Check .env file and settings.py")
print("="*60)