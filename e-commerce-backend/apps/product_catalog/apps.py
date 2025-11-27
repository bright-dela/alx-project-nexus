from django.apps import AppConfig


class ProductCatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.product_catalog"


    def ready(self):
        import apps.product_catalog.signals
        