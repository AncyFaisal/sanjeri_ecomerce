# sanjeri_app/management/commands/fix_profile_images.py
from django.core.management.base import BaseCommand
from sanjeri_app.models import CustomUser

class Command(BaseCommand):
    help = 'Fix profile images for all users'
    
    def handle(self, *args, **options):
        users = CustomUser.objects.all()
        fixed_count = 0
        
        for user in users:
            if user.profile_image:
                try:
                    # Try to access URL
                    _ = user.profile_image.url
                except ValueError:
                    # No file associated, set to None
                    user.profile_image = None
                    user.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Fixed user: {user.username}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error with user {user.username}: {e}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {fixed_count} users')
        )