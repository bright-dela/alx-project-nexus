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
        result = super().authenticate(request)

        if result is None:
            return None

        user, token = result

        # Extract claims
        jti = str(token.get("jti"))
        user_id = token.get("user_id")
        token_device = token.get("device")

        # Check blacklists
        if is_jti_blacklisted(jti):
            raise AuthenticationFailed("This session has been terminated")

        if is_user_token_blacklisted(user_id, jti):
            raise AuthenticationFailed("All sessions have been terminated")

        # Get current device
        current_ip = get_client_ip(request)
        current_user_agent = get_user_agent(request)
        current_device = generate_device_fingerprint(current_ip, current_user_agent)

        # OPTIONAL: Enforce device matching (strict mode)
        # if token_device != current_device:
        #     logger.warning(f'Device mismatch blocked for {user.email}')
        #     raise AuthenticationFailed('Token not valid for this device')

        # We just log, don't block
        if token_device != current_device:
            logger.warning(
                f"Device fingerprint mismatch for user {user.email}: "
                f"token_device={token_device}, current_device={current_device}"
            )

        return user, token
