# test_exact.py
print("EXACT 32-CHARACTER TEST")
print("="*50)

# The EXACT 32-character secret
exact_secret = "thisisnotarealsecretbut32charok"

print(f"Secret: {exact_secret}")
print(f"Length: {len(exact_secret)}")

# Count each character
print("\nCharacter-by-character count:")
for i, char in enumerate(exact_secret, 1):
    print(f"  {i:2d}: '{char}'")

print(f"\nTotal characters: {len(exact_secret)}")
if len(exact_secret) == 32:
    print("✅ PERFECT! Exactly 32 characters")
    print("   This is the CORRECT length for Razorpay")
else:
    print(f"❌ WRONG: {len(exact_secret)} characters (should be 32)")