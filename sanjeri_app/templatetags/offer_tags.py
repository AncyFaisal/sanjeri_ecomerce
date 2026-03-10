from django import template
from django.utils import timezone
from decimal import Decimal

register = template.Library()

@register.filter
def get_best_offer(product):
    """Get the best offer for a product"""
    best_discount = Decimal('0')
    best_offer = None
    now = timezone.now()
    
    try:
        # Check product offers
        for offer in product.product_offers.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ):
            if offer.discount_percentage > best_discount:
                best_discount = offer.discount_percentage
                best_offer = offer
        
        # Check category offers
        if product.category:
            for offer in product.category.category_offers.filter(
                is_active=True,
                valid_from__lte=now,
                valid_to__gte=now
            ):
                if offer.discount_percentage > best_discount:
                    best_discount = offer.discount_percentage
                    best_offer = offer
    except Exception as e:
        print(f"Error in get_best_offer: {e}")
        return None
    
    return best_offer

@register.filter
def get_offer_discount(price, product):
    """Calculate discount amount for a product"""
    try:
        best_offer = get_best_offer(product)
        if best_offer:
            if best_offer.discount_percentage > 0:
                return (price * best_offer.discount_percentage) / 100
            elif best_offer.discount_fixed > 0:
                return best_offer.discount_fixed
    except Exception as e:
        print(f"Error in get_offer_discount: {e}")
    return 0

@register.filter
def calculate_discount_percentage(discounted_price, original_price):
    """Calculate discount percentage from discounted and original prices"""
    try:
        if original_price and original_price > 0:
            discount = ((original_price - discounted_price) / original_price) * 100
            return round(discount)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return 0

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value
    
@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def floatformat(value, digits=0):
    """Format number to specified decimal places"""
    try:
        return f"{float(value):.{digits}f}"
    except (ValueError, TypeError):
        return value