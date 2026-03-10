# sanjeri_app/utils/offer_utils.py
from decimal import Decimal
from django.utils import timezone
from django.db.models import Min
from ..models.offer_models import ProductOffer, CategoryOffer, OfferApplication

def apply_offers_to_cart(cart):
    """
    Calculate best offers for all items in cart
    Returns detailed dict with total discount and per-item offer info
    """
    total_discount = Decimal('0')
    applied_offers = []
    item_offers = {}  # Dictionary with cart_item_id as key
    
    for cart_item in cart.items.select_related('variant__product', 'variant__product__category').all():
        product = cart_item.variant.product
        item_price = cart_item.variant.display_price
        
        # Get best offer for this product
        best_offer = get_best_offer_for_product(
            product=product, 
            cart_subtotal=cart.subtotal,
            item_price=item_price
        )
        
        if best_offer['offer']:
            # Calculate discount for this item (per unit * quantity)
            item_discount = best_offer['discount_per_unit'] * cart_item.quantity
            total_discount += item_discount
            
            # Store for response
            offer_info = {
                'cart_item_id': cart_item.id,
                'product_id': product.id,
                'product_name': product.name,
                'variant': f"{cart_item.variant.volume_ml}ml - {cart_item.variant.gender}",
                'quantity': cart_item.quantity,
                'original_price_per_unit': item_price,
                'discount_per_unit': best_offer['discount_per_unit'],
                'final_price_per_unit': best_offer['discounted_price'],
                'total_original': item_price * cart_item.quantity,
                'total_discount': item_discount,
                'total_final': best_offer['discounted_price'] * cart_item.quantity,
                'offer': best_offer['offer'],
                'offer_type': best_offer['offer_type'],
                'offer_name': best_offer['offer'].name if best_offer['offer'] else None,
                'offer_id': best_offer['offer'].id if best_offer['offer'] else None,
            }
            
            applied_offers.append(offer_info)
            item_offers[cart_item.id] = offer_info
    
    return {
        'total_discount': total_discount,
        'subtotal_after_discount': cart.subtotal - total_discount,
        'applied_offers': applied_offers,
        'item_offers': item_offers,  # Keyed by cart_item_id for easy lookup
    }

def get_best_offer_for_product(product, cart_subtotal, item_price):
    """
    Get the best available offer for a product
    Compares product-specific offers vs category offers
    """
    best_offer = None
    best_discount = Decimal('0')
    best_offer_type = None
    best_offer_obj = None
    
    now = timezone.now()
    
    # ===== 1. CHECK PRODUCT OFFERS =====
    product_offers = ProductOffer.objects.filter(
        products=product,
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now
    ).select_related()
    
    for offer in product_offers:
        # Check minimum purchase requirement
        if cart_subtotal >= offer.min_purchase_amount:
            discount, discounted_price = offer.calculate_discount(item_price)
            
            if discount > best_discount:
                best_discount = discount
                best_offer_obj = offer
                best_offer_type = 'product'
                best_discounted_price = discounted_price
    
    # ===== 2. CHECK CATEGORY OFFERS =====
    if product.category:
        category_offers = CategoryOffer.objects.filter(
            category=product.category,
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).select_related()
        
        for offer in category_offers:
            # Check minimum purchase requirement
            if cart_subtotal >= offer.min_purchase_amount:
                discount, discounted_price = offer.calculate_discount(item_price)
                
                if discount > best_discount:
                    best_discount = discount
                    best_offer_obj = offer
                    best_offer_type = 'category'
                    best_discounted_price = discounted_price
    
    # ===== 3. RETURN RESULTS =====
    if best_offer_obj:
        return {
            'offer': best_offer_obj,
            'offer_type': best_offer_type,
            'offer_id': best_offer_obj.id,
            'offer_name': best_offer_obj.name,
            'discount_per_unit': best_discount,
            'discounted_price': best_discounted_price,
        }
    else:
        return {
            'offer': None,
            'offer_type': None,
            'offer_id': None,
            'offer_name': None,
            'discount_per_unit': Decimal('0'),
            'discounted_price': item_price,
        }

def calculate_seasonal_discount(subtotal):
    """
    Calculate seasonal discounts based on business rules
    Example: 10% off on orders above ₹1000
    """
    seasonal_discount = Decimal('0')
    
    # Example rule: 10% off on orders above ₹1000
    if subtotal > Decimal('1000'):
        seasonal_discount = subtotal * Decimal('0.10')
        # Cap seasonal discount at ₹500
        if seasonal_discount > Decimal('500'):
            seasonal_discount = Decimal('500')
    
    return seasonal_discount