from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Product, Category
from .tasks import invalidate_product_cache, invalidate_category_cache


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def _invalidate_product(sender, instance, **kwargs):
    invalidate_product_cache.delay(str(instance.id))


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def _invalidate_category(sender, instance, **kwargs):
    invalidate_category_cache.delay()