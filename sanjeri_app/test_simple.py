# test_keys.py
import os

# Test the keys from your .env file
key_id = "rzp_test_S2X7LdXgRrfZBx"
key_secret = "GMZ3fiMnAyB5xHXJELTdZKq4"

print("Current Key Analysis:")
print(f"Key ID: {key_id}")
print(f"  Length: {len(key_id)}")
print(f"  Starts with 'rzp_test_': {key_id.startswith('rzp_test_')}")
print(f"  Format looks OK: {len(key_id) >= 20 and key_id.startswith('rzp_test_')}")

print(f"\nKey Secret: {key_secret}")
print(f"  Length: {len(key_secret)}")
print(f"  Should be 32 chars: {len(key_secret) == 32}")
print(f"  Current is 24 chars - TOO SHORT!")

print("\n" + "="*50)
print("VALIDATION:")
if len(key_secret) != 32:
    print("❌ INVALID: Key Secret must be exactly 32 characters")
    print(f"   Your secret is {len(key_secret)} characters")
else:
    print("✅ Key Secret length is correct")

if not key_id.startswith('rzp_test_'):
    print("❌ INVALID: Key ID must start with 'rzp_test_' for test mode")
else:
    print("✅ Key ID format is correct")