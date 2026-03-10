# sanjeri_app/models/payment.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from .order import *
from decimal import Decimal

class PaymentTransaction(models.Model):
    """Separate model for payment transactions"""
    PAYMENT_STATUS_CHOICES = [
        ('created', 'Created'),
        ('attempted', 'Attempted'),
        ('pending', 'Pending'),
        ('captured', 'Captured'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('cod', 'Cash on Delivery'),
    ]
    
    # Relationships
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Razorpay identifiers
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='created')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_attempted_at = models.DateTimeField(null=True, blank=True)
    payment_captured_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    gateway_response = models.JSONField(default=dict, blank=True)  # Store full Razorpay response
    notes = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
    
    def __str__(self):
        return f"Payment {self.razorpay_order_id} - {self.status} - ₹{self.amount}"
    
    def mark_as_attempted(self, payment_method=None):
        """Mark payment as attempted"""
        self.status = 'attempted'
        self.payment_attempted_at = timezone.now()
        if payment_method:
            self.payment_method = payment_method
        self.save()
    
    def mark_as_captured(self, razorpay_payment_id, razorpay_signature=None, gateway_response=None):
        """Mark payment as captured/successful"""
        self.status = 'captured'
        self.razorpay_payment_id = razorpay_payment_id
        self.razorpay_signature = razorpay_signature
        self.payment_captured_at = timezone.now()
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
    
    def mark_as_failed(self, error_message=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.save()
    
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == 'captured'
    
    def can_retry(self):
        """Check if payment can be retried"""
        return self.status in ['failed', 'cancelled']