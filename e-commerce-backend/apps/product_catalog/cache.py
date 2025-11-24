from django.core.cache import caches

import hashlib


product_cache = caches["product_cache"]



def product_list_key(request):
    """Cache key for paginated product lists"""

    query_string = request.META.get("QUERY_STRING", "")
    path = request.path
    
    # Hash to avoid URlL encoding issues
    query_hash = hashlib.md5(query_string.encode()).hexdigest()
    
    return f"product_list: {path}:{query_hash}"


def product_detail_key(product_id):
    return f"product:{product_id}"


def category_tree_key():
    return "category_tree:v1"


def brand_list_key():
    return "brand_list:v1"


def delete_pattern(pattern: str):
    """Delete all keys matching a pattern in product_cache."""

    client = product_cache.client.get_client(write=True)
    deleted = 0

    for key in client.scan_iter(match=pattern):
        client.delete(key)
        deleted += 1

    return deleted