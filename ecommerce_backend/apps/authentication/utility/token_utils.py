from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .utils import generate_device_fingerprint


def create_tokens_with_claims(user, ip_address, user_agent):
    """
    Create JWT tokens with enhanced security claims.
    All user and device information is embedded in the token.
    """
    refresh = RefreshToken.for_user(user)

    # Create device fingerprint for binding token to device
    device_fingerprint = generate_device_fingerprint(ip_address, user_agent)

    # Add custom claims to refresh token
    refresh["email"] = user.email
    refresh["first_name"] = user.first_name
    refresh["last_name"] = user.last_name
    refresh["is_email_verified"] = user.is_email_verified
    refresh["ip"] = ip_address
    refresh["device"] = device_fingerprint
    refresh["issued_at"] = timezone.now().isoformat()

    # Get access token from refresh token
    access = refresh.access_token

    # Add same custom claims to access token
    access["email"] = user.email
    access["first_name"] = user.first_name
    access["last_name"] = user.last_name
    access["is_email_verified"] = user.is_email_verified
    access["ip"] = ip_address
    access["device"] = device_fingerprint

    return {
        "refresh": str(refresh),
        "access": str(access),
        "refresh_jti": str(refresh["jti"]),
        "access_jti": str(access["jti"]),
    }


def decode_token_claims(token_string):
    """
    Decode a token and extract all claims without validation.
    Useful for reading token information.
    """
    try:
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken(token_string)
        return dict(token.payload)

    except Exception:
        return None
