from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


class SocialAuthProvider:
    """Handles social authentication with different providers"""

    @classmethod
    def verify_token(cls, provider, access_token, id_token_str=""):
        """Verify token and get user info based on provider"""

        if provider == "google":
            return cls.verify_google_token(id_token_str or access_token)

        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        

    @staticmethod
    def verify_google_token(token):
        """Verify Google OAuth token"""
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )

            # Token is valid, extract user info
            return {
                "email": idinfo["email"],
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
                "provider_id": idinfo["sub"],
            }
        except Exception as e:
            raise ValueError(f"Invalid Google token: {str(e)}")
