# sanjeri_app/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract arg from value"""
    try:
        result = float(value) - float(arg)
        # Return as integer if it's a whole number
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError):
        try:
            # Try integer subtraction as fallback
            return int(value) - int(arg)
        except (ValueError, TypeError):
            return value

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        result = float(value) * float(arg)
        # Return as integer if it's a whole number
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError):
        try:
            # Try integer multiplication as fallback
            return int(value) * int(arg)
        except (ValueError, TypeError):
            return value

@register.filter
def divide(value, arg):
    """Divide value by arg (for percentages)"""
    try:
        if float(arg) == 0:
            return 0
        result = float(value) / float(arg)
        # Return as integer if it's a whole number
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def div(value, arg):
    """Alias for divide - for compatibility"""
    return divide(value, arg)

@register.filter
def percentage(value, arg):
    """Calculate percentage: value is the total, arg is the percentage"""
    try:
        result = (float(value) * float(arg)) / 100
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError):
        return value