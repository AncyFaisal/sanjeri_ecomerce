# sanjeri_app/views/coupon_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from ..models import Cart, Coupon

@login_required
@require_POST
def apply_coupon(request):
    """Apply coupon to user's cart"""
    try:
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        
        if not coupon_code:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a coupon code'
            })
        
        # Get cart
        cart = Cart.objects.get(user=request.user)
        
        # Check if coupon exists
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
        except Coupon.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid coupon code'
            })
        
        # Check if user has already used this coupon (for single-use coupons)
        if coupon.single_use_per_user:
            # Check if user has already placed orders with this coupon
            from ..models import Order
            used_count = Order.objects.filter(
                user=request.user,
                coupon=coupon,
                status__in=['confirmed', 'shipped', 'delivered', 'out_for_delivery']
            ).count()
            
            if used_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'You have already used coupon "{coupon.code}"'
                })
            
        # Validate coupon
        is_valid, message = coupon.is_valid(
            user=request.user,
            order_amount=cart.subtotal
        )
        
        if not is_valid:
            return JsonResponse({
                'success': False,
                'message': message
            })
        
        # Store coupon in session
        request.session['applied_coupon'] = {
            'code': coupon.code,
            'coupon_id': coupon.id,
            'discount_type': coupon.discount_type,
            'discount_value': str(coupon.discount_value),
            'min_order_amount': str(coupon.min_order_amount),
            'max_discount_amount': str(coupon.max_discount_amount) if coupon.max_discount_amount else None,
        }
        
        # Calculate discount for display
        discount_amount = coupon.calculate_discount(cart.subtotal)
        
        # Calculate totals with coupon
        shipping_charge = Decimal('0') if cart.subtotal > Decimal('500') else Decimal('40')
        tax_amount = (cart.subtotal - discount_amount) * Decimal('0.18')
        total_amount = cart.subtotal + shipping_charge + tax_amount - discount_amount
        
        return JsonResponse({
            'success': True,
            'message': f'Coupon "{coupon.code}" applied successfully!',
            'coupon': {
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': str(coupon.discount_value),
                'discount_amount': str(discount_amount),
            },
            'totals': {
                'subtotal': str(cart.subtotal),
                'discount_amount': str(discount_amount),
                'shipping_charge': str(shipping_charge),
                'tax_amount': str(tax_amount),
                'total_amount': str(total_amount),
            }
        })
        
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error applying coupon: {str(e)}'
        })

@login_required
@require_POST
def remove_coupon(request):
    """Remove applied coupon"""
    try:
        if 'applied_coupon' in request.session:
            coupon_code = request.session['applied_coupon']['code']
            del request.session['applied_coupon']
            
            # Get cart for recalculating totals
            cart = Cart.objects.get(user=request.user)
            
            # Calculate totals without coupon
            shipping_charge = Decimal('0') if cart.subtotal > Decimal('500') else Decimal('40')
            tax_amount = cart.subtotal * Decimal('0.18')
            total_amount = cart.subtotal + shipping_charge + tax_amount
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon "{coupon_code}" removed successfully',
                'totals': {
                    'subtotal': str(cart.subtotal),
                    'discount_amount': '0.00',
                    'shipping_charge': str(shipping_charge),
                    'tax_amount': str(tax_amount),
                    'total_amount': str(total_amount),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No coupon applied'
            })
            
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error removing coupon: {str(e)}'
        })

def get_coupon_display_data(cart, coupon_data):
    """Helper function to get coupon display data"""
    if not coupon_data:
        return None
    
    try:
        coupon = Coupon.objects.get(id=coupon_data['coupon_id'])
        discount_amount = coupon.calculate_discount(cart.subtotal)
        
        return {
            'code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value,
            'discount_amount': discount_amount,
            'display_text': f'{coupon.discount_value}{"%" if coupon.discount_type == "percentage" else "₹"} OFF',
            'description': get_coupon_description(coupon)
        }
    except Coupon.DoesNotExist:
        return None

def get_coupon_description(coupon):
    """Generate coupon description"""
    description = []
    
    if coupon.discount_type == 'percentage':
        description.append(f'{coupon.discount_value}% discount')
    else:
        description.append(f'₹{coupon.discount_value} off')
    
    if coupon.min_order_amount > 0:
        description.append(f'on orders above ₹{coupon.min_order_amount}')
    
    if coupon.max_discount_amount:
        description.append(f'(max ₹{coupon.max_discount_amount})')
    
    return ' '.join(description)