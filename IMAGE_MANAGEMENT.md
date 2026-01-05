@"
# Image Management Guide - Sanjeri Perfumes

## 🎯 RULES FOR IMAGE STORAGE

### 1. Static Images (Website Assets)
**Location:** `static/images/` and `static/css/images/`
**Purpose:** Logos, icons, backgrounds, website design elements
**Examples:**
- Logo files
- Background patterns
- Icons (shopping cart, user, etc.)
- Banner/slider images
- UI elements

### 2. Media Images (User Uploaded Content)
**Location:** `media/` folder
**Purpose:** Product images, user uploads, dynamic content
**Examples:**
- Product main images → `media/products/main/`
- Product variant images → `media/products/variants/`
- Product gallery images → `media/products/gallery/`
- User profile images → `media/profile_pics/`
- Category images → `media/categories/`

## 🚨 IMPORTANT RULES

### DO NOT:
- Put product images in `static/` folder ❌
- Commit product images to git ❌
- Store user uploads in static folder ❌

### DO:
- Upload product images via Django Admin ✅
- Keep website assets in static folder ✅
- Use .gitignore for media folder ✅
- Organize media with subfolders ✅

## 🔧 SETUP INSTRUCTIONS

### For Developers:
1. Clone repository
2. Create `media/` folder (already in .gitignore)
3. Run server: Images will be saved to `media/`

### For Admin Users:
1. Login to Django Admin
2. Add products via admin interface
3. Upload images through file browser
4. Images auto-save to `media/products/`

### For Deployment:
1. Ensure `media/` folder has write permissions
2. Configure web server to serve media files
3. Setup CDN for media files if needed

## 📁 CURRENT STRUCTURE

### Correct Structure:
