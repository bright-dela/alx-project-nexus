from django.core.cache import cache
from django.conf import settings
import hashlib
import secrets
import string
from datetime import datetime


def get_client_ip(request):
    """Extract and returns the real client IP address from the request"""

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_user_agent(request):
    """Extract user agent string from request and limit length"""
    return request.META.get("HTTP_USER_AGENT", "")[:200]


def generate_device_fingerprint(ip_address, user_agent):
    """
    Create a unique fingerprint for this device based on IP and user agent.
    This helps detect if a token is being used from a different device.
    """

    data = f"{ip_address}:{user_agent}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def generate_otp_code(length=6):
    """Generate a random numeric OTP code"""

    digits = string.digits
    choose = secrets.choice
    return "".join(choose(digits) for _ in range(length))


def generate_magic_token():
    """
    Generate a cryptographically secure random token for magic links.
    Returns a URL-safe token string.
    """
    return secrets.token_urlsafe(32)


def cache_blacklist_jti(jti, user_id, ttl=None):
    """
    Store a blacklisted token JTI in cache.
    This prevents the token from being used even though it hasn't expired.
    """
    cache_key = f"blacklist:jti:{jti}"
    cache_data = {"user_id": user_id, "blacklisted_at": datetime.now().isoformat()}

    # If TTL not provided, use refresh token lifetime from settings
    if ttl is None:
        # Get the timedelta object and convert to seconds
        refresh_lifetime = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME")
        ttl = int(refresh_lifetime.total_seconds())

    cache.set(cache_key, cache_data, ttl)
    return True


def is_jti_blacklisted(jti):
    """Check if a specific token JTI has been blacklisted"""

    cache_key = f"blacklist:jti:{jti}"

    if cache.get(cache_key):
        return True
    return False


def blacklist_user_tokens(user_id, except_jti=None):
    """
    Blacklist all tokens for a user, optionally excluding one token.
    Useful for "logout all devices except this one" functionality.
    """
    cache_key = f"blacklist:user:{user_id}"
    cache.set(
        cache_key,
        {"except_jti": except_jti, "blacklisted_at": datetime.now().isoformat()},
        604800,
    )


def is_user_token_blacklisted(user_id, jti):
    """
    Check if all of a user's tokens have been blacklisted.
    Returns False if the current JTI is the exception.
    """
    cache_key = f"blacklist:user:{user_id}"
    data = cache.get(cache_key)

    if data:
        # If this JTI is the exception, allow it
        if data.get("except_jti") == jti:
            return False
        return True

    return False


def check_rate_limit(identifier, max_attempts, window_minutes):
    """
    Generic rate limiting function using Redis cache.
    Returns True if rate limit is exceeded, False otherwise.
    """
    cache_key = f"rate_limit:{identifier}"
    attempts = cache.get(cache_key, 0)

    if attempts >= max_attempts:
        return True

    # Increment attempts
    cache.set(cache_key, attempts + 1, window_minutes * 60)
    return False
