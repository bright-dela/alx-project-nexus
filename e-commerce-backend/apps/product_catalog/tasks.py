import logging
from celery import shared_task

from .cache import (
    product_cache,
    product_detail_key,
    delete_pattern,
    category_tree_key,
    brand_list_key
)


logger = logging.getLogger(__name__)


@shared_task
def invalidate_product_cache(product_id):
    """
    Deletes all product list pages + the product detail cache.
    """

    try:
        # delete detail cache
        product_cache.delete(product_detail_key(product_id))

        # delete all list pages
        delete_pattern("product_list:*")

        logger.info(f"Product cache invalidated for product: {product_id}")


        return True
    
    except Exception as e:
        logger.error(f"Failed to invalidate product cache for {product_id}: {str(e)}")
        raise


@shared_task
def invalidate_category_cache():
    """
    Deletes category tree + brand list + all product lists.
    """

    try:
        product_cache.delete(category_tree_key())
        product_cache.delete(brand_list_key())

        # clear all product list pages
        delete_pattern("product_list:*")

        logger.info("Category cache invalidated successfully")

        return True
    

    except Exception as e:
        logger.error(f"Failed to invalidate category cache: {str(e)}")
        raise
    
    
