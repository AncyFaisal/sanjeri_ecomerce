# context_processors.py
from django.db.models import Sum
from .models import Cart, Wishlist
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models.offer_models import ProductOffer, CategoryOffer
from .models.wallet import WalletTransaction
User = get_user_model()

def wallet_balance(request):
    """Context processor that auto-creates wallet if missing"""
    if request.user.is_authenticated:
        try:
            # Import inside the function to avoid circular imports
            from sanjeri_app.models.wallet import Wallet
            
            # ========== FIX: Auto-create wallet if it doesn't exist ==========
            wallet, created = Wallet.objects.get_or_create(
                user=request.user, 
                defaults={'balance': 0}
            )
            
            if created:
                print(f"✅ Auto-created wallet for user {request.user.id} via context processor")
            
            return {'wallet_balance': wallet.balance}
            # ========== END FIX ==========
            
        except Exception as e:
            # Log the error for debugging
            print(f"Wallet context processor error: {e}")
            return {'wallet_balance': 0}
    
    return {'wallet_balance': 0}


def cart_and_wishlist_context(request):
    """
    Consolidated context processor for both cart and wishlist
    """
    context = {}
    
    if request.user.is_authenticated:
        # Import inside function
        from sanjeri_app.models.cart import Cart
        from sanjeri_app.models.wishlist import Wishlist
        
        # Cart count
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_item_count'] = cart.total_items
            context['cart_items_count'] = cart.total_items
        except Cart.DoesNotExist:
            context['cart_item_count'] = 0
            context['cart_items_count'] = 0
        
        # Wishlist count
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            context['wishlist_count'] = wishlist.total_items
            context['wishlist_items_count'] = wishlist.total_items
        except Wishlist.DoesNotExist:
            context['wishlist_count'] = 0
            context['wishlist_items_count'] = 0
    else:
        context['cart_item_count'] = 0
        context['cart_items_count'] = 0
        context['wishlist_count'] = 0
        context['wishlist_items_count'] = 0
    
    return context

def offer_context(request):
    """Add offer information to all templates"""
    now = timezone.now()
    
    # Get active offers
    active_product_offers = ProductOffer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now
    ).prefetch_related('products')
    
    active_category_offers = CategoryOffer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now
    ).select_related('category')
    
    return {
        'now': now,
        'active_product_offers': active_product_offers,
        'active_category_offers': active_category_offers,
    }

    # In your admin_views.py or create a context processor
def admin_context(request):
    if request.user.is_staff:
        pending_refunds_count = WalletTransaction.objects.filter(
            transaction_type='REFUND',
            status='PENDING'
        ).count()
        return {'pending_refunds_count': pending_refunds_count}
    return {}