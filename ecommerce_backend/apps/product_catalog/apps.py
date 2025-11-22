from django.apps import AppConfig


class ProductCatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.product_catalog"


    def ready(self):
        """
        Import signals when the app is ready.
        This ensures signal handlers are registered when Django starts.
        """
        from . import signals
