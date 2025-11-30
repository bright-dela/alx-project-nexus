from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


import logging

logger = logging.getLogger(__name__)




class GoogleAuthProvider:
    """Handles Google OAuth authentication"""

    @staticmethod
    def verify_token(id_token_str):
        """
        Verify Google OAuth token and return user information.

        Args:
            id_token_str: Google ID token string

        Returns:
            dict: User information including email, first_name, last_name, provider_id

        Raises:
            ValueError: If token is invalid or verification fails
        """

        try:
            # Check if Google OAuth is properly configured
            if (
                not hasattr(settings, "GOOGLE_OAUTH_CLIENT_ID")
                or not settings.GOOGLE_OAUTH_CLIENT_ID
            ):
                raise ValueError("Google OAuth is not properly configured")

            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )

            # Ensure the token is for our application
            if idinfo.get("aud") != settings.GOOGLE_OAUTH_CLIENT_ID:
                raise ValueError("Token audience mismatch")

            # Token is valid, extract user info
            user_info = {
                "email": idinfo.get("email"),
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
                "provider_id": idinfo.get("sub"),  # Google's unique user ID
                "email_verified": idinfo.get("email_verified", False),
            }

            # Validate that we have required fields
            if not user_info["email"]:
                raise ValueError("Email not provided by Google")

            if not user_info["provider_id"]:
                raise ValueError("Provider ID not found in token")

            logger.info(
                f"Successfully verified Google token for email: {user_info['email']}"
            )

            return user_info

        except ValueError as e:
            logger.error(f"Google token verification failed: {str(e)}")
            raise ValueError(f"Invalid Google token: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error during Google token verification: {str(e)}")
            raise ValueError(f"Google authentication failed: {str(e)}")
