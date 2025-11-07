from django.apps import AppConfig


class ScansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scans'

    def ready(self)-> None:
        import scans.signales.handlers

