"""
Test settings configuration for running tests in CI/CD and locally.
This file should be used when running tests to avoid email sending
and use in-memory task execution.
"""

from .settings import *


# Test database configuration - use SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use locmem cache backend for testing - better than dummy for actual cache testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default-cache",
    },
    "product_cache": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "product-cache",
    },
    "auth_cache": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "auth-cache",
    },
}

# Celery configuration for testing - execute tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use console email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable password validation for faster tests
AUTH_PASSWORD_VALIDATORS = []

# Use simpler password hasher for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Set dummy Google OAuth credentials for testing
GOOGLE_OAUTH_CLIENT_ID = "test-client-id"
GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"

# Reduce cache timeouts for faster tests
CATEGORY_TREE_CACHE_TIMEOUT = 60
PRODUCT_LIST_CACHE_TIMEOUT = 30
PRODUCT_DETAIL_CACHE_TIMEOUT = 30

# Logging configuration for tests - reduce noise
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


