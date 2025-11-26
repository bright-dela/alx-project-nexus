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
    SocialAuthSerializer,
)
from .services import (
    OTPService,
    EmailService,
    LoginTrackingService,
    TokenBlacklistService,
)
from .social_auth import SocialAuthProvider

# Create your views here.

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
                        {"error": "User not found"}, 
                        status=status.HTTP_404_NOT_FOUND
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
                    {"message": "OTP sent successfully"}, 
                    status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
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
                    user, 
                    request, 
                    success=False, 
                    failure_reason="Invalid credentials"
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
                        {"error": "User not found"}, 
                        status=status.HTTP_404_NOT_FOUND
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


class SocialAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        
        if serializer.is_valid():
            provider = serializer.validated_data["provider"]
            access_token = serializer.validated_data["access_token"]
            id_token = serializer.validated_data.get("id_token", "")

            try:
                user_info = SocialAuthProvider.verify_token(
                    provider, access_token, id_token
                )

                # Get or create user
                user, created = User.objects.get_or_create(
                    email=user_info["email"],
                    defaults={
                        "first_name": user_info.get("first_name", ""),
                        "last_name": user_info.get("last_name", ""),
                        "is_verified": True,
                        "provider": provider,
                        "provider_id": user_info["provider_id"],
                    },
                )

                # Update provider info if user already exists
                if not created and not user.provider:
                    user.provider = provider
                    user.provider_id = user_info["provider_id"]
                    user.is_verified = True
                    user.save()

                # Record login
                LoginTrackingService.record_login_attempt(user, request, success=True)

                # Generate tokens
                refresh = RefreshToken.for_user(user)

                return Response(
                    {
                        "message": "Social authentication successful",
                        "tokens": {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                        },
                        "user": UserSerializer(user).data,
                        "is_new_user": created,
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                return Response(
                    {"error": f"Social authentication failed: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
