from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from ..utility.utils import (
    cache_blacklist_jti,
    blacklist_user_tokens,
    generate_otp_code,
    generate_magic_token,
)

from ..utility.passwordless_utils import (
    store_otp_code,
    verify_otp_code,
    store_magic_token,
    verify_magic_token,
    check_passwordless_rate_limit,
)

from .email_services import send_otp_email, send_magic_link_email, send_welcome_email
from ..utility.token_utils import create_tokens_with_claims, decode_token_claims
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordlessAuthService:
    """
    Service class for handling passwordless authentication operations.
    All business logic is centralized here for better maintainability.
    """

    @staticmethod
    def register_user(validated_data):
        """
        Register a new user without requiring a password.
        User can log in later using passwordless methods.
        """
        email = validated_data.get("email").lower().strip()
        first_name = validated_data.get("first_name").lower().strip()
        last_name = validated_data.get("last_name").lower().strip()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError({"email": "User with this email already exists"})

        # Create user without password
        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=False,
        )

        logger.info(f"New user registered: {email}")

        # Send welcome email
        send_welcome_email(email, user.first_name)

        return user

    @staticmethod
    def initiate_passwordless_login(email, method, ip_address, request):
        """
        Start the passwordless login process by sending OTP or magic link.
        Returns success status and message.
        """
        email = email.lower().strip()

        # Check rate limiting to prevent abuse
        if check_passwordless_rate_limit(email):
            raise ValidationError(
                {"detail": "Too many login attempts. Please try again later."}
            )

        # Get user
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            raise ValidationError({"email": "No account found with this email"})

        if method == "otp":
            # Generate and store OTP code
            otp_code = generate_otp_code()
            store_otp_code(email, otp_code)

            # Send OTP via email
            success = send_otp_email(email, otp_code, user.first_name)

            if not success:
                raise ValidationError(
                    {"detail": "Failed to send verification code. Please try again."}
                )

            logger.info(f"OTP sent to {email}")

            return {
                "success": True,
                "message": "Verification code sent to your email",
                "method": "otp",
            }

        elif method == "magic_link":
            # Generate and store magic token
            magic_token = generate_magic_token()
            store_magic_token(email, magic_token)

            # Build magic link URL
            # You should replace this with your actual frontend URL

            base_url = request.build_absolute_uri("/")[:-1]
            magic_link = f"{base_url}/api/auth/verify-magic-link/{magic_token}/"

            # Send magic link via email
            success = send_magic_link_email(email, magic_link, user.first_name)

            if not success:
                raise ValidationError(
                    {"detail": "Failed to send login link. Please try again."}
                )

            logger.info(f"Magic link sent to {email}")
            return {
                "success": True,
                "message": "Login link sent to your email",
                "method": "magic_link",
            }

        raise ValidationError({"method": "Invalid authentication method"})

    @staticmethod
    def verify_otp_and_login(email, otp_code, ip_address, user_agent):
        """
        Verify OTP code and issue JWT tokens if valid.
        """
        email = email.lower().strip()

        # Verify the OTP code
        is_valid, message = verify_otp_code(email, otp_code)

        if not is_valid:
            raise ValidationError({"otp_code": message})

        # Get user
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            raise ValidationError({"email": "User not found"})

        # Mark email as verified if not already
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Generate JWT tokens
        tokens = create_tokens_with_claims(user, ip_address, user_agent)

        logger.info(f"User logged in successfully via OTP: {email}")

        return {"user": user, "tokens": tokens, "message": "Login successful"}

    @staticmethod
    def verify_magic_link_and_login(magic_token, ip_address, user_agent):
        """
        Verify magic link token and issue JWT tokens if valid.
        """
        # Verify the magic token
        email, message = verify_magic_token(magic_token)

        if email is None:
            raise ValidationError({"token": message})

        # Get user
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            raise ValidationError({"email": "User not found"})

        # Mark email as verified if not already
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Generate JWT tokens
        tokens = create_tokens_with_claims(user, ip_address, user_agent)

        logger.info(f"User logged in successfully via magic link: {email}")

        return {"user": user, "tokens": tokens, "message": "Login successful"}

    @staticmethod
    def logout_user(refresh_token_string):
        """
        Logout user by blacklisting their refresh token.
        """
        try:
            # Decode token to get JTI and user_id
            token = RefreshToken(refresh_token_string)
            jti = str(token["jti"])
            user_id = token["user_id"]

            # Blacklist this specific token
            cache_blacklist_jti(jti, user_id)

            # Also use simplejwt's built-in blacklist
            token.blacklist()

            logger.info(f"User logged out successfully: user_id={user_id}")

            return True
        
        except Exception as e:
            raise ValidationError({"detail": f"Invalid token: {str(e)}"})

    @staticmethod
    def revoke_all_tokens(user, current_access_token=None):
        """
        Revoke all tokens for a user except optionally the current session.
        """
        current_jti = None

        # Get current access token's JTI to exclude it
        if current_access_token:
            claims = decode_token_claims(current_access_token)
            if claims:
                current_jti = claims.get("jti")

        # Blacklist all user tokens except current one
        blacklist_user_tokens(user.id, except_jti=current_jti)

        logger.info(f"All tokens revoked for user: {user.email}")

        return True

    @staticmethod
    def get_user_data(user):
        """
        Return formatted user data for API responses.
        """
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.username,
            "last_name": user.last_name,
            "is_email_verified": user.is_email_verified,
            "date_joined": user.date_joined.isoformat(),
        }

    @staticmethod
    def get_token_info(token_string):
        """
        Extract and return information from token claims.
        """
        claims = decode_token_claims(token_string)

        if not claims:
            return None

        return {
            "jti": claims.get("jti"),
            "user_id": claims.get("user_id"),
            "email": claims.get("email"),
            "first_name": claims.get("first_name"),
            "last_name": claims.get("last_name"),
            "ip": claims.get("ip"),
            "device": claims.get("device"),
            "issued_at": claims.get("issued_at"),
            "expires_at": claims.get("exp"),
        }
