from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    EmailVerificationView,
    ResendOTPView,
    UserLoginView,
    UserLogoutView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    CurrentUserView,
    LoginHistoryView,
    SecurityClaimsView,
    SocialAuthView,
)

app_name = "authentication"

urlpatterns = [
    # Registration and verification
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),

    # Authentication
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Password reset
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    # User profile
    path("me/", CurrentUserView.as_view(), name="current-user"),

    # Security features
    path("login-history/", LoginHistoryView.as_view(), name="login-history"),
    path("security-claims/", SecurityClaimsView.as_view(), name="security-claims"),
    
    # Social authentication
    path("social/", SocialAuthView.as_view(), name="social-auth"),
]
