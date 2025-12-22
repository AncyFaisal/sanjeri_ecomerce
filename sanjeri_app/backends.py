# sanjeri_app/backends.py
from django.contrib.auth.backends import ModelBackend
from sanjeri_app.models import CustomUser

class CustomUserBackend(ModelBackend):
    def user_can_authenticate(self, user):
        """
        Override to prevent login if user is blocked.
        """
        is_active = super().user_can_authenticate(user)
        return is_active and not user.is_blocked
