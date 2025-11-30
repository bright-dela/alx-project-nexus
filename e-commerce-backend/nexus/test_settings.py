"""
Test settings configuration for running tests in CI/CD and locally.
This file should be used when running tests to avoid email sending
and use in-memory task execution.
"""

from nexus.settings import *

# Test database configuration - use SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # In-memory database for speed
    }
}

# Use dummy cache backend for testing to avoid Redis client issues
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
    "product_cache": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
    "auth_cache": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
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

# Logging configuration for tests - suppress cache warnings
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",  # Only show errors, suppress warnings
    },
    "loggers": {
        "apps.product_catalog": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
