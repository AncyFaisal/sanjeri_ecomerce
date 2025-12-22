from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth import get_user_model

# class CustomAccountAdapter(DefaultAccountAdapter):
#     def save_user(self, request, user, form, commit=True):
#         user = super().save_user(request, user, form, commit=False)
#         user_data = form.cleaned_data
        
#         # Add custom fields
#         if 'phone' in user_data:
#             user.phone = user_data['phone']
#         if 'gender' in user_data:
#             user.gender = user_data['gender']
#         if 'address' in user_data:
#             user.address = user_data['address']
        
#         if commit:
#             user.save()
#         return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Called just before a social user is logged in.
        Auto-create user without showing the signup form.
        """
        # If the social account doesn't have a user yet, create one
        if not sociallogin.is_existing:
            # Extract data from social account
            email = sociallogin.account.extra_data.get('email')
            first_name = sociallogin.account.extra_data.get('given_name', '')
            last_name = sociallogin.account.extra_data.get('family_name', '')
            
            # Get the CustomUser model
            CustomUser = get_user_model()
            
            # Check if a user with this email already exists
            try:
                existing_user = CustomUser.objects.get(email=email)
                # If user exists, connect the social account to it
                sociallogin.connect(request, existing_user)
            except CustomUser.DoesNotExist:
                # Create new user
                username = email.split('@')[0]  # Use part of email as username
                # Ensure username is unique
                base_username = username
                counter = 1
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = CustomUser(
                    email=email,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                user.set_unusable_password()  # Social users don't need password
                user.save()
                sociallogin.user = user

    def is_auto_signup_allowed(self, request, sociallogin):
        """Always allow auto signup without form"""
        return True