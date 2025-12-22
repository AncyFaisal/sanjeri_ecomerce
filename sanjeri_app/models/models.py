from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class UserData(models.Model):
    name=models.CharField(max_length=100)
    email=models.EmailField()
    created_at=models.DateTimeField(auto_now_add=True)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
# class CustomUserAdmin(AbstractUser):
#     is_blocked=models.BooleanField(default=False)


#     def __str__(self):
#         return self.username