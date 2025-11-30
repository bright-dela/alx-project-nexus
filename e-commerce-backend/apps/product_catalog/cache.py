from django.core.cache import caches
import hashlib
import logging

logger = logging.getLogger(__name__)

product_cache = caches["product_cache"]


def product_list_key(request):
    """
    Generate a unique cache key for paginated product lists.

    This function creates different cache keys for different query parameters,
    ensuring that filtered, searched, or paginated results don't collide.

    For example:
    - /products/?page=1 gets a different key than /products/?page=2
    - /products/?category=electronics gets a different key than /products/?category=books
    - /products/?search=laptop gets a different key than /products/?search=phone

    Args:
        request: Django request object containing query parameters

    Returns:
        str: A unique cache key for this specific product list request
    """
    query_string = request.META.get("QUERY_STRING", "")
    path = request.path

    # Hash the query string to create a fixed-length identifier
    query_hash = hashlib.md5(query_string.encode()).hexdigest()

    # Include path and query hash to make the key unique per combination
    return f"product_list:{path}:{query_hash}"


def product_detail_key(product_id):
    """
    Generate cache key for individual product detail pages.

    Args:
        product_id: UUID or ID of the product

    Returns:
        str: Cache key for the product detail
    """
    return f"product:{product_id}"


def category_tree_key():
    """
    Generate cache key for the category tree.

    The version suffix allows us to easily invalidate all category caches
    by incrementing the version number if needed.

    Returns:
        str: Cache key for category tree
    """
    return "category_tree:v1"


def brand_list_key():
    """
    Generate cache key for the brand list.

    Returns:
        str: Cache key for brand list
    """
    return "brand_list:v1"


def delete_pattern(pattern: str):
    """
    Delete all cache keys matching a pattern in product_cache.

    This is used for cache invalidation when products or categories change.
    For example, when a product is updated, we delete all product list caches
    since any list page might be displaying that product.

    Args:
        pattern: Redis pattern to match keys (e.g., "product_list:*")

    Returns:
        int: Number of keys deleted
    """
    try:
        # Check if we're using a cache backend that supports pattern deletion
        cache_backend = product_cache.__class__.__name__

        # For locmem or dummy cache (used in tests), manually clear matching keys
        if cache_backend in ["LocMemCache", "DummyCache"]:
            # Can't iterate keys in locmem, so just clear entire cache
            product_cache.clear()
            logger.info(f"Cleared entire product cache (using {cache_backend})")
            return 1

        # For Redis cache, use pattern matching
        client = product_cache.client.get_client(write=True)
        deleted = 0

        # scan_iter is memory-efficient for large keysets
        for key in client.scan_iter(match=pattern):
            client.delete(key)
            deleted += 1

        logger.info(f"Deleted {deleted} cache keys matching pattern: {pattern}")
        return deleted

    except AttributeError:
        # If client doesn't have get_client method, we're probably in tests
        try:
            product_cache.clear()
            logger.info(f"Cleared entire product cache (fallback method)")
            return 1
        except Exception as e:
            logger.warning(f"Could not clear cache pattern {pattern}: {str(e)}")
            return 0

    except Exception as e:
        # If Redis isn't available or there's a connection issue,
        # we don't want to crash the application
        logger.error(f"Failed to delete cache pattern {pattern}: {str(e)}")
        return 0
