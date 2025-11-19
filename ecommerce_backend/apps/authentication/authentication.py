from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .utility.utils import (
    get_client_ip,
    get_user_agent,
    generate_device_fingerprint,
    is_jti_blacklisted,
    is_user_token_blacklisted,
)
import logging

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates additional security claims.
    Checks token blacklist and optionally validates device fingerprint.
    """

    def authenticate(self, request):
        # Call authentication to get user and token
        result = super().authenticate(request)

        if result is None:
            return None

        user, token = result

        # Extract claims from token
        jti = str(token.get("jti"))
        user_id = token.get("user_id")
        token_ip = token.get("ip")
        token_device = token.get("device")

        # Check if this specific token has been blacklisted
        if is_jti_blacklisted(jti):
            raise AuthenticationFailed("This session has been terminated")

        # Check if all user's tokens have been blacklisted
        if is_user_token_blacklisted(user_id, jti):
            raise AuthenticationFailed("All sessions have been terminated")

        # Get current request information
        current_ip = get_client_ip(request)
        current_user_agent = get_user_agent(request)
        current_device = generate_device_fingerprint(current_ip, current_user_agent)

        # Check for device fingerprint mismatch (logging only, not blocking)
        if token_device != current_device:
            logger.warning(
                f"Device fingerprint mismatch for user {user.email}: "
                f"token_device={token_device}, current_device={current_device}"
            )
            # Note: We log this but don't block the request

        if token_ip != current_ip:
            logger.warning(f"IP address mismatch for user {user.email}")

        return user, token
