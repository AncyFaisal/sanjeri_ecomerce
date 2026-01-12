from django.apps import AppConfig


class SanjeriAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sanjeri_app'

    def ready(self):
        # Import signals
        import sanjeri_app.signals