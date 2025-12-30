# sanjay_app/user_models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models import Q, UniqueConstraint
from django.conf import settings 
import os 

class CustomUser(AbstractUser):
    # email = models.EmailField(unique=True)   
    # phone = models.CharField(max_length=15, unique=True, default='0000000000')
    # address = models.TextField(blank=True, null=True)
    # gender = models.CharField(
    #     max_length=10,
    #     choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
    #     blank=True,
    #     null=True
    # )
    # is_blocked = models.BooleanField(default=False)  # block/unblock users

    # def __str__(self):
    #     return self.username

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('blocked', 'Blocked'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    phone = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_joined = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    profile_image = models.ImageField(
        upload_to='profile_images/',
        null=True,
        blank=True,
        default=None  # This is the default
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["username"],
                condition=Q(is_deleted=False),
                name="unique_username_not_deleted"
            ),
            UniqueConstraint(
                fields=["email"],
                condition=Q(is_deleted=False),
                name="unique_email_not_deleted"
            ),
        ]
    def get_profile_image_url(self):
        """
        Always return static default if no custom image uploaded
        """
        if self.profile_image and self.profile_image.name:
            return self.profile_image.url
        return '/static/images/default_profile.png'
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        return self.get_full_name() or self.username

# Add this to your models.py after CustomUser model

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='home')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    landmark = models.CharField(max_length=255, blank=True, null=True, help_text="Nearby landmark for easy location")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.state}"
    
    def save(self, *args, **kwargs):
        # If this address is set as default, unset default for other addresses of the same user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)