# fix_settings_now.py
print("FIXING settings.py...")

settings_path = 'sanjeri_project/settings.py'

# Read current settings
with open(settings_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track changes
changes_made = []

# 1. Add dotenv import at top
if 'from dotenv import load_dotenv' not in ''.join(lines):
    for i, line in enumerate(lines):
        if 'import os' in line:
            lines.insert(i + 1, 'from dotenv import load_dotenv\n')
            changes_made.append("Added 'from dotenv import load_dotenv'")
            break

# 2. Add load_dotenv() after imports
if 'load_dotenv()' not in ''.join(lines):
    for i, line in enumerate(lines):
        if 'BASE_DIR = Path(__file__).resolve().parent.parent' in line:
            lines.insert(i - 1, 'load_dotenv()  # Load environment variables from .env file\n')
            changes_made.append("Added 'load_dotenv()'")
            break

# 3. Replace hardcoded Razorpay keys
for i, line in enumerate(lines):
    if "RAZORPAY_KEY_ID = 'rzp_test_1DP5mmOlF5G5ag'" in line:
        lines[i] = "RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')\n"
        changes_made.append("Fixed RAZORPAY_KEY_ID to read from .env")
    
    if "RAZORPAY_KEY_SECRET = 'wFYmNv4Wt5ZbM7fE8qH3rK6pL9'" in line:
        lines[i] = "RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')\n"
        changes_made.append("Fixed RAZORPAY_KEY_SECRET to read from .env")

# Write back
with open(settings_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ settings.py fixed!")
if changes_made:
    for change in changes_made:
        print(f"   • {change}")
else:
    print("   No changes needed - already fixed")