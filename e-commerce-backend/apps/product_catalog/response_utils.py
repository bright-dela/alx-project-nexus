"""
Standardized API response utilities for product catalog endpoints.
Imports from authentication response_utils to maintain consistency across the application.
"""

from apps.authentication.response_utils import (
    success_response,
    error_response,
    validation_error_response,
    authentication_error_response,
    permission_error_response,
    not_found_response,
)

__all__ = [
    "success_response",
    "error_response",
    "validation_error_response",
    "authentication_error_response",
    "permission_error_response",
    "not_found_response",
]
