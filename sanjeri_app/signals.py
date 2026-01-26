# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models.wallet import Wallet

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create wallet for new users"""
    if created:
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_wallet(sender, instance, **kwargs):
    """Save wallet when user is saved"""
    instance.wallet.save()