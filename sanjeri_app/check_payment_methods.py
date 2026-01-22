# check_payment_methods.py
import razorpay
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

def check_account_status():
    """Check what payment methods are available via API"""
    
    # Method 1: Try to fetch account details
    url = "https://api.razorpay.com/v1/accounts/me"
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET), headers=headers)
    
    if response.status_code == 200:
        account = response.json()
        print("✅ Account details retrieved")
        print(f"Account ID: {account.get('id')}")
        print(f"Status: {account.get('status')}")
        print(f"KYC: {account.get('kyc_status')}")
        
        # Check for payment methods in response
        if 'payment_methods' in account:
            print(f"\nPayment Methods: {account['payment_methods']}")
        else:
            print("\n⚠️ Payment methods not in response")
            
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
    
    # Method 2: Create a test payment link to see available methods
    print("\n" + "="*50)
    print("Testing payment link creation...")
    
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    
    try:
        payment_link = client.payment_link.create({
            "amount": 100,
            "currency": "INR",
            "accept_partial": False,
            "description": "Test Payment Methods",
            "customer": {
                "name": "Test User",
                "email": "test@example.com",
                "contact": "+919999999999"
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {"test": "true"},
            "callback_url": "http://localhost:8000/",
            "callback_method": "get"
        })
        
        print(f"✅ Payment link created: {payment_link['short_url']}")
        print("\nVisit this link to see available payment methods")
        
    except Exception as e:
        print(f"❌ Error creating payment link: {e}")

if __name__ == "__main__":
    print(f"Checking account with key: {RAZORPAY_KEY_ID[:10]}...")
    check_account_status()