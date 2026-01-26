# apps.py

from django.apps import AppConfig

class SanjeriAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sanjeri_app'
    
    def ready(self):
        try:
            # Import signals if they exist
            import sanjeri_app.signals
        except ImportError:
            # Signals file doesn't exist yet, that's okay
            pass