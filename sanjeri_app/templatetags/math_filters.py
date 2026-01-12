from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value"""
    try:
        result = float(value) - float(arg)
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError):
        try:
            return int(value) - int(arg)
        except (ValueError, TypeError):
            return value

@register.filter
def mul(value, arg):
    """Multiply value by arg"""
    try:
        result = float(value) * float(arg)
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        if float(arg) == 0:
            return 0
        result = float(value) / float(arg)
        if result.is_integer():
            return int(result)
        return round(result, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        return value
