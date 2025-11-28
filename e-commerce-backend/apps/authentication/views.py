from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    EmailVerificationSerializer,
    ResendOTPSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserSerializer,
    LoginHistorySerializer,
    SecurityClaimSerializer,
    GoogleAuthSerializer,
)
from .services import (
    OTPService,
    EmailService,
    LoginTrackingService,
    TokenBlacklistService,
)
from .social_auth import GoogleAuthProvider

import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Generate and send OTP
            otp = OTPService.create_otp(user.email, purpose="verification")
            EmailService.send_verification_email(user, otp)

            return Response(
                {
                    "message": "Registration successful. Please check your email for verification code.",
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]
            otp = serializer.validated_data["otp"]

            if OTPService.verify_otp(email, otp, purpose="verification"):
                try:
                    user = User.objects.get(email=email)
                    user.is_verified = True
                    user.save(update_fields=["is_verified"])

                    return Response(
                        {"message": "Email verified successfully"},
                        status=status.HTTP_200_OK,
                    )
                except User.DoesNotExist:
                    return Response(
                        {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {"error": "Invalid or expired OTP"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]

            try:
                user = User.objects.get(email=email)

                if user.is_verified:
                    return Response(
                        {"message": "Email already verified"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                otp = OTPService.create_otp(email, purpose="verification")
                EmailService.send_verification_email(user, otp)

                return Response(
                    {"message": "OTP sent successfully"}, status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Check if account is locked
            if LoginTrackingService.is_account_locked(user.email):
                return Response(
                    {
                        "error": "Account temporarily locked due to multiple failed login attempts. Try again later."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if email is verified
            if not user.is_verified:
                return Response(
                    {"error": "Please verify your email before logging in"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Record successful login
            LoginTrackingService.record_login_attempt(user, request, success=True)

            # Generate tokens
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "message": "Login successful",
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )

        # Record failed login attempt
        email = request.data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                LoginTrackingService.record_login_attempt(
                    user, request, success=False, failure_reason="Invalid credentials"
                )
            except User.DoesNotExist:
                pass

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)

                # Blacklist the refresh token
                TokenBlacklistService.blacklist_token(str(token["jti"]), token["exp"])

            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except TokenError:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            try:
                user = User.objects.get(email=email)
                otp = OTPService.create_otp(email, purpose="password_reset")
                EmailService.send_password_reset_email(email, otp)

                return Response(
                    {"message": "Password reset code sent to your email"},
                    status=status.HTTP_200_OK,
                )
            except User.DoesNotExist:
                # Don't reveal if email exists
                return Response(
                    {"message": "If the email exists, a reset code has been sent"},
                    status=status.HTTP_200_OK,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]
            otp = serializer.validated_data["otp"]
            new_password = serializer.validated_data["new_password"]

            if OTPService.verify_otp(email, otp, purpose="password_reset"):
                try:
                    user = User.objects.get(email=email)
                    user.set_password(new_password)
                    user.save()

                    return Response(
                        {"message": "Password reset successful"},
                        status=status.HTTP_200_OK,
                    )
                except User.DoesNotExist:
                    return Response(
                        {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {"error": "Invalid or expired OTP"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class LoginHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LoginHistorySerializer

    def get_queryset(self):
        return self.request.user.login_history.all()[:50]


class SecurityClaimsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SecurityClaimSerializer

    def get_queryset(self):
        return self.request.user.security_claims.filter(resolved=False)


class GoogleAuthView(APIView):
    """
    Endpoint for Google OAuth authentication.

    POST /api/auth/google/
    Body: {
        "id_token": "google_id_token_string"
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        id_token_str = serializer.validated_data["id_token"]

        try:
            # Verify the Google token and get user info
            user_info = GoogleAuthProvider.verify_token(id_token_str)

            # Check if email is verified by Google
            if not user_info.get("email_verified", False):
                return Response(
                    {"error": "Email not verified by Google"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get or create user
            user, created = User.objects.get_or_create(
                email=user_info["email"],
                defaults={
                    "first_name": user_info.get("first_name", ""),
                    "last_name": user_info.get("last_name", ""),
                    "is_verified": True,  # Google verified the email
                    "provider": "google",
                    "provider_id": user_info["provider_id"],
                },
            )

            # Update provider info if user already exists but didn't have it
            if not created:
                updated = False
                if not user.provider:
                    user.provider = "google"
                    updated = True
                if not user.provider_id:
                    user.provider_id = user_info["provider_id"]
                    updated = True
                if not user.is_verified:
                    user.is_verified = True
                    updated = True

                if updated:
                    user.save()

            # Record login
            LoginTrackingService.record_login_attempt(user, request, success=True)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            logger.info(f"Google authentication successful for user: {user.email}")

            return Response(
                {
                    "message": "Google authentication successful",
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    "user": UserSerializer(user).data,
                    "is_new_user": created,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            logger.error(f"Google authentication failed: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Unexpected error in Google authentication: {str(e)}")
            return Response(
                {"error": "Authentication failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
