# sanjeri_app/templatetags/coupon_filters.py
from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return int(arg) - int(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def days_left(value):
    """Calculate days left until permanent deletion (30 - days_since_deleted)"""
    try:
        days_since = int(value)
        days_left = 30 - days_since
        return max(days_left, 0)  # Don't show negative days
    except (ValueError, TypeError):
        return 0

@register.filter
def can_delete_in_days(value):
    """Get formatted message for when coupon can be permanently deleted"""
    try:
        days_since = int(value)
        if days_since >= 30:
            return "Can be permanently deleted now"
        else:
            days_left = 30 - days_since
            return f"Can delete in {days_left} day{'s' if days_left != 1 else ''}"
    except (ValueError, TypeError):
        return "Invalid date"