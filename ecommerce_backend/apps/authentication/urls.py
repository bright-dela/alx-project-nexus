from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    PasswordlessLoginInitiateView,
    OTPVerificationView,
    MagicLinkVerificationView,
    LogoutView,
    UserProfileView,
    TokenInfoView,
    RevokeAllTokensView,
    ResendVerificationView,
)

urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="register"),

    # Passwordless Login
    path("login/", PasswordlessLoginInitiateView.as_view(), name="login"),
    path("verify-otp/", OTPVerificationView.as_view(), name="verify_otp"),
    path("verify-magic-link/<str:token>/", MagicLinkVerificationView.as_view(), name="verify_magic_link"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend_verification"),

    # Token Management
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/info/", TokenInfoView.as_view(), name="token_info"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("revoke-all/", RevokeAllTokensView.as_view(), name="revoke_all"),
    
    # User Profile
    path("profile/", UserProfileView.as_view(), name="profile"),
]
