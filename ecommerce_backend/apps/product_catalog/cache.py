from django.core.cache import caches
from urllib.parse import quote_plus

product_cache = caches["product_cache"]


# Cache Key Builders

def product_list_key(request):
    """Cache key for paginated product lists."""

    full_path = request.get_full_path()

    encoded = quote_plus(full_path)

    return f"product_list:{encoded}"



def product_detail_key(product_id):
    return f"product:{product_id}"


def category_tree_key():
    return "category_tree:v1"




# Cache Pattern Deletion

def delete_pattern(pattern: str):
    """Delete all keys matching a pattern in product_cache."""

    client = product_cache.client.get_client(write=True)
    
    deleted = 0

    for key in client.scan_iter(match=pattern):
        client.delete(key)
        deleted += 1

    return deleted
