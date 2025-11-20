from django.core.cache import cache
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Get passwordless settings with defaults
PASSWORDLESS_CONFIG = getattr(settings, "PASSWORDLESS_AUTH", {})
OTP_LENGTH = PASSWORDLESS_CONFIG.get("OTP_LENGTH", 6)
OTP_EXPIRY_MINUTES = PASSWORDLESS_CONFIG.get("OTP_EXPIRY_MINUTES", 10)
MAGIC_LINK_EXPIRY_MINUTES = PASSWORDLESS_CONFIG.get("MAGIC_LINK_EXPIRY_MINUTES", 15)
MAX_OTP_ATTEMPTS = PASSWORDLESS_CONFIG.get("MAX_OTP_ATTEMPTS", 3)
RATE_LIMIT_REQUESTS = PASSWORDLESS_CONFIG.get("RATE_LIMIT_REQUESTS", 3)
RATE_LIMIT_WINDOW = PASSWORDLESS_CONFIG.get("RATE_LIMIT_WINDOW_MINUTES", 15)


def store_otp_code(email, otp_code):
    """
    Store OTP code in cache with expiry time.
    Also stores the creation timestamp for verification.
    """
    cache_key = f"otp:{email}"
    cache_data = {
        "code": otp_code,
        "created_at": datetime.now().isoformat(),
        "attempts": 0,
    }

    # Store with expiry time in seconds
    cache.set(cache_key, cache_data, OTP_EXPIRY_MINUTES * 60)

    logger.info(f"OTP stored for {email}, expires in {OTP_EXPIRY_MINUTES} minutes")

    return True


def verify_otp_code(email, submitted_code):
    """
    Verify if the submitted OTP code matches the stored one.
    Also checks if the code has expired or max attempts exceeded.
    """
    cache_key = f"otp:{email}"
    cached_data = cache.get(cache_key)

    if not cached_data:
        logger.warning(f"OTP verification failed for {email}: No code found or expired")

        return (False, "OTP code has expired or does not exist")

    # Check if max attempts exceeded
    if cached_data["attempts"] >= MAX_OTP_ATTEMPTS:
        cache.delete(cache_key)

        logger.warning(f"OTP verification failed for {email}: Max attempts exceeded")

        return (False, "Maximum verification attempts exceeded")

    # Increment attempt counter
    cached_data["attempts"] += 1
    cache.set(cache_key, cached_data, OTP_EXPIRY_MINUTES * 60)

    # Verify the code
    if cached_data["code"] == submitted_code:
        # Code is correct, delete it so it can't be reused
        cache.delete(cache_key)
        logger.info(f"OTP verification successful for {email}")

        return (True, "OTP verified successfully")

    logger.warning(f"OTP verification failed for {email}: Invalid code")

    return (
        False,
        f"Invalid OTP code. {MAX_OTP_ATTEMPTS - cached_data['attempts']} attempts remaining",
    )


def store_magic_token(email, magic_token):
    """
    Store magic link token in cache with expiry time.
    This token will be used to verify the magic link.
    """
    cache_key = f"magic_token:{magic_token}"
    cache_data = {"email": email, "created_at": datetime.now().isoformat()}

    # Store with expiry time in seconds
    cache.set(cache_key, cache_data, MAGIC_LINK_EXPIRY_MINUTES * 60)

    logger.info(
        f"Magic token stored for {email}, expires in {MAGIC_LINK_EXPIRY_MINUTES} minutes"
    )

    return True


def verify_magic_token(magic_token):
    """
    Verify if the magic token is valid and return associated email.
    Token is deleted after successful verification (one-time use).
    """
    cache_key = f"magic_token:{magic_token}"
    cached_data = cache.get(cache_key)

    if not cached_data:
        logger.warning(f"Magic token verification failed: Token not found or expired")

        return (None, "Magic link has expired or is invalid")

    email = cached_data["email"]

    # Delete token so it can't be reused
    cache.delete(cache_key)

    logger.info(f"Magic token verification successful for {email}")

    return (email, "Magic link verified successfully")


def check_passwordless_rate_limit(email):
    """
    Check if user has exceeded rate limit for passwordless login requests.
    This prevents spam and abuse.
    """
    from .utils import check_rate_limit

    identifier = f"passwordless:{email}"

    return check_rate_limit(identifier, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)


def cleanup_expired_otp(email):
    """
    Manually cleanup expired OTP for an email.
    Usually Redis handles this automatically, but this can be called explicitly.
    """
    cache_key = f"otp:{email}"
    cache.delete(cache_key)

    logger.info(f"OTP cleaned up for {email}")
