from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import (
    UserRegistrationSerializer,
    PasswordlessLoginSerializer,
    OTPVerificationSerializer,
    UserSerializer,
)
from .services.auth_services import PasswordlessAuthService
from .utility.utils import get_client_ip, get_user_agent
from .utility.token_utils import create_tokens_with_claims


class RegisterView(APIView):
    """
    Register a new user without requiring a password.
    POST /api/auth/register/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Validate input data
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user
        user = PasswordlessAuthService.register_user(serializer.validated_data)

        # Generate tokens for immediate login
        tokens = create_tokens_with_claims(
            user, ip_address, user_agent
        )

        user_data = PasswordlessAuthService.get_user_data(user)

        return Response(
            {
                "user": user_data,
                "tokens": {"refresh": tokens["refresh"], "access": tokens["access"]},
                "message": "Registration successful. Welcome email sent.",
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def get_tokens_for_user(user, ip_address, user_agent):
        """Helper method to generate tokens"""
        from utility.token_utils import create_tokens_with_claims

        return create_tokens_with_claims(user, ip_address, user_agent)


class PasswordlessLoginInitiateView(APIView):
    """
    Initiate passwordless login by sending OTP or magic link.
    POST /api/auth/login/
    Body: {"email": "user@example.com", "method": "otp" or "magic_link"}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Validate input data
        serializer = PasswordlessLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Initiate passwordless login
        result = PasswordlessAuthService.initiate_passwordless_login(
            email=serializer.validated_data["email"],
            method=serializer.validated_data["method"],
            ip_address=ip_address,
            request=request,
        )

        return Response(result, status=status.HTTP_200_OK)


class OTPVerificationView(APIView):
    """
    Verify OTP code and complete login.
    POST /api/auth/verify-otp/
    Body: {"email": "user@example.com", "otp_code": "123456"}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Validate input data
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify OTP and login
        result = PasswordlessAuthService.verify_otp_and_login(
            email=serializer.validated_data["email"],
            otp_code=serializer.validated_data["otp_code"],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        user_data = PasswordlessAuthService.get_user_data(result["user"])

        return Response(
            {
                "user": user_data,
                "tokens": {
                    "refresh": result["tokens"]["refresh"],
                    "access": result["tokens"]["access"],
                },
                "message": result["message"],
            },
            status=status.HTTP_200_OK,
        )


class MagicLinkVerificationView(APIView):
    """
    Verify magic link token and complete login.
    GET /api/auth/verify-magic-link/<token>/
    This endpoint is typically accessed via email link click.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Verify magic link and login
        result = PasswordlessAuthService.verify_magic_link_and_login(
            magic_token=token, ip_address=ip_address, user_agent=user_agent
        )

        user_data = PasswordlessAuthService.get_user_data(result["user"])

        return Response(
            {
                "user": user_data,
                "tokens": {
                    "refresh": result["tokens"]["refresh"],
                    "access": result["tokens"]["access"],
                },
                "message": result["message"],
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Logout user by blacklisting their refresh token.
    POST /api/auth/logout/
    Body: {"refresh_token": "your_refresh_token"}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "refresh_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        PasswordlessAuthService.logout_user(refresh_token)

        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """
    Get current user's profile information.
    GET /api/auth/profile/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_data = PasswordlessAuthService.get_user_data(request.user)
        return Response(user_data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update user profile"""
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Re-issue tokens with updated user info
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        tokens = create_tokens_with_claims(user, ip_address, user_agent)

        return Response(
            {
                "user": serializer.data,
                "tokens": {"refresh": tokens["refresh"], "access": tokens["access"]},
                "message": "Profile updated successfully",
            },
            status=status.HTTP_200_OK,
        )


class TokenInfoView(APIView):
    """
    Get information about the current access token.
    GET /api/auth/token/info/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header.startswith("Bearer "):
            return Response(
                {"error": "No token provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        token = auth_header.split(" ")[1]
        token_info = PasswordlessAuthService.get_token_info(token)

        if not token_info:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(token_info, status=status.HTTP_200_OK)


class RevokeAllTokensView(APIView):
    """
    Revoke all tokens except the current session.
    POST /api/auth/revoke-all/
    Useful for "logout all other devices" functionality.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        current_token = None

        if auth_header.startswith("Bearer "):
            current_token = auth_header.split(" ")[1]

        PasswordlessAuthService.revoke_all_tokens(request.user, current_token)

        return Response(
            {"message": "All other sessions have been terminated"},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """
    Resend verification OTP or magic link.
    POST /api/auth/resend-verification/
    Body: {"email": "user@example.com", "method": "otp" or "magic_link"}
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # This uses the same logic as initial login
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        serializer = PasswordlessLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = PasswordlessAuthService.initiate_passwordless_login(
            email=serializer.validated_data["email"],
            method=serializer.validated_data["method"],
            ip_address=ip_address,
            request=request,
        )

        return Response(
            {
                "message": "Verification code resent successfully",
                "method": result["method"],
            },
            status=status.HTTP_200_OK,
        )

