from rest_framework import status, generics
from rest_framework.views import APIView
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

from .response_utils import (
    success_response,
    error_response,
    validation_error_response,
    authentication_error_response,
    permission_error_response,
    not_found_response,
)

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

            return success_response(
                message="Registration successful. Please check your email for verification code.",
                data={"email": user.email},
                status_code=status.HTTP_201_CREATED,
            )

        return validation_error_response(serializer.errors)


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        if OTPService.verify_otp(email, otp, purpose="verification"):
            try:
                user = User.objects.get(email=email)
                user.is_verified = True
                user.save(update_fields=["is_verified"])

                return success_response(
                    message="Email verified successfully",
                    data={"email": user.email, "is_verified": True},
                )
            
            except User.DoesNotExist:
                return not_found_response("User not found")
        else:
            return error_response(
                error_type="invalid_otp",
                message="Invalid or expired verification code",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)

            if user.is_verified:
                return error_response(
                    error_type="already_verified",
                    message="Email already verified",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            otp = OTPService.create_otp(email, purpose="verification")
            EmailService.send_verification_email(user, otp)

            return success_response(
                message="Verification code sent successfully", data={"email": email}
            )
        
        except User.DoesNotExist:
            return not_found_response("User not found")


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if not serializer.is_valid():
            # Record failed login attempt
            email = request.data.get("email")
            if email:
                try:
                    user = User.objects.get(email=email)

                    LoginTrackingService.record_login_attempt(
                        user,
                        request,
                        success=False,
                        failure_reason="Invalid credentials",
                    )
                except User.DoesNotExist:
                    pass

            return validation_error_response(serializer.errors)

        user = serializer.validated_data["user"]

        # Check if account is locked
        if LoginTrackingService.is_account_locked(user.email):
            return permission_error_response(
                "Account temporarily locked due to multiple failed login attempts. Please try again later."
            )

        # Check if email is verified
        if not user.is_verified:
            return permission_error_response(
                "Please verify your email before logging in"
            )

        # Record successful login
        LoginTrackingService.record_login_attempt(user, request, success=True)

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return success_response(
            message="Login successful",
            data={
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user": UserSerializer(user).data,
            },
        )


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)

                # Blacklist the refresh token
                TokenBlacklistService.blacklist_token(str(token["jti"]), token["exp"])

            return success_response("Logout successful")
        
        except TokenError:
            return error_response(
                error_type="invalid_token",
                message="Invalid token",
                status_code=status.HTTP_400_BAD_REQUEST,
            )



class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            otp = OTPService.create_otp(email, purpose="password_reset")
            EmailService.send_password_reset_email(email, otp)

            return success_response(
                message="Password reset code sent to your email", data={"email": email}
            )
        
        except User.DoesNotExist:
            # Don't reveal if email exists
            return success_response(
                message="If the email exists, a reset code has been sent",
                data={"email": email},
            )



class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        if OTPService.verify_otp(email, otp, purpose="password_reset"):
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()

                return success_response(
                    message="Password reset successful", data={"email": email}
                )
            
            except User.DoesNotExist:
                return not_found_response("User not found")
        else:
            return error_response(
                error_type="invalid_otp",
                message="Invalid or expired reset code",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class CurrentUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            message="User profile retrieved successfully", data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        self.perform_update(serializer)

        return success_response(
            message="User profile updated successfully", data=serializer.data
        )



class LoginHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LoginHistorySerializer

    def get_queryset(self):
        return self.request.user.login_history.all()[:50]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return success_response(
            message="Login history retrieved successfully",
            data={"login_history": serializer.data, "count": queryset.count()},
        )



class SecurityClaimsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SecurityClaimSerializer

    def get_queryset(self):
        return self.request.user.security_claims.filter(resolved=False)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return success_response(
            message="Security claims retrieved successfully",
            data={"security_claims": serializer.data, "count": queryset.count()},
        )


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
            return validation_error_response(serializer.errors)

        id_token_str = serializer.validated_data["id_token"]

        try:
            # Verify the Google token and get user info
            user_info = GoogleAuthProvider.verify_token(id_token_str)

            # Check if email is verified by Google
            if not user_info.get("email_verified", False):
                return error_response(
                    error_type="email_not_verified",
                    message="Email not verified by Google",
                    status_code=status.HTTP_400_BAD_REQUEST,
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

            return success_response(
                message="Google authentication successful",
                data={
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    "user": UserSerializer(user).data,
                    "is_new_user": created,
                },
            )

        except ValueError as e:
            logger.error(f"Google authentication failed: {str(e)}")

            return error_response(
                error_type="google_auth_error",
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
        except Exception as e:
            logger.error(f"Unexpected error in Google authentication: {str(e)}")
            
            return error_response(
                error_type="server_error",
                message="Authentication failed. Please try again.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
