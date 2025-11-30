from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.services import OTPService, LoginTrackingService
from apps.authentication.models import LoginHistory, SecurityClaim

User = get_user_model()


class UserRegistrationTestCase(TestCase):
    """Tests for user registration functionality"""

    def setUp(self):
        self.client = APIClient()
        self.registration_url = "/api/auth/register/"
        self.valid_user_data = {
            "email": "testuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_user_registration_success(self):
        """Test successful user registration with valid data"""
        response = self.client.post(self.registration_url, self.valid_user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertTrue(
            User.objects.filter(email=self.valid_user_data["email"]).exists()
        )

        user = User.objects.get(email=self.valid_user_data["email"])
        self.assertFalse(user.is_verified)
        self.assertTrue(user.is_active)

    def test_registration_password_mismatch(self):
        """Test registration fails when passwords do not match"""
        invalid_data = self.valid_user_data.copy()
        invalid_data["password_confirm"] = "DifferentPassword123!"

        response = self.client.post(self.registration_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email=invalid_data["email"]).exists())

    def test_registration_duplicate_email(self):
        """Test registration fails with duplicate email address"""
        User.objects.create_user(
            email=self.valid_user_data["email"],
            password=self.valid_user_data["password"],
        )

        response = self.client.post(self.registration_url, self.valid_user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_weak_password(self):
        """Test registration fails with weak password"""
        weak_data = self.valid_user_data.copy()
        weak_data["password"] = "123"
        weak_data["password_confirm"] = "123"

        response = self.client.post(self.registration_url, weak_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailVerificationTestCase(TestCase):
    """Tests for email verification functionality"""

    def setUp(self):
        self.client = APIClient()
        self.verify_url = "/api/auth/verify-email/"
        self.user = User.objects.create_user(
            email="verify@example.com", password="SecurePass123!", is_verified=False
        )

    def test_email_verification_success(self):
        """Test successful email verification with valid OTP"""
        otp = OTPService.create_otp(self.user.email, purpose="verification")

        response = self.client.post(
            self.verify_url, {"email": self.user.email, "otp": otp}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_verification_invalid_otp(self):
        """Test verification fails with invalid OTP"""
        OTPService.create_otp(self.user.email, purpose="verification")

        response = self.client.post(
            self.verify_url, {"email": self.user.email, "otp": "000000"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_verification_nonexistent_user(self):
        """Test verification fails for non-existent user"""
        otp = OTPService.create_otp("nonexistent@example.com", purpose="verification")

        response = self.client.post(
            self.verify_url, {"email": "nonexistent@example.com", "otp": otp}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UserLoginTestCase(TestCase):
    """Tests for user login functionality"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = "/api/auth/login/"
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            email="loginuser@example.com", password=self.password, is_verified=True
        )

    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": self.password}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertIn("user", response.data)

    def test_login_unverified_user(self):
        """Test login fails for unverified user"""
        unverified_user = User.objects.create_user(
            email="unverified@example.com", password=self.password, is_verified=False
        )

        response = self.client.post(
            self.login_url, {"email": unverified_user.email, "password": self.password}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_invalid_credentials(self):
        """Test login fails with invalid password"""
        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": "WrongPassword123!"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_creates_history_record(self):
        """Test that successful login creates login history record"""
        initial_count = LoginHistory.objects.filter(user=self.user).count()

        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": self.password}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            LoginHistory.objects.filter(user=self.user).count(), initial_count + 1
        )


class PasswordResetTestCase(TestCase):
    """Tests for password reset functionality"""

    def setUp(self):
        self.client = APIClient()
        self.reset_request_url = "/api/auth/password-reset/"
        self.reset_confirm_url = "/api/auth/password-reset/confirm/"
        self.user = User.objects.create_user(
            email="resetuser@example.com", password="OldPassword123!", is_verified=True
        )

    def test_password_reset_request_success(self):
        """Test successful password reset request"""
        response = self.client.post(self.reset_request_url, {"email": self.user.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_confirm_success(self):
        """Test successful password reset with valid OTP"""
        otp = OTPService.create_otp(self.user.email, purpose="password_reset")
        new_password = "NewSecurePass123!"

        response = self.client.post(
            self.reset_confirm_url,
            {
                "email": self.user.email,
                "otp": otp,
                "new_password": new_password,
                "new_password_confirm": new_password,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_password_reset_invalid_otp(self):
        """Test password reset fails with invalid OTP"""
        OTPService.create_otp(self.user.email, purpose="password_reset")

        response = self.client.post(
            self.reset_confirm_url,
            {
                "email": self.user.email,
                "otp": "000000",
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "NewSecurePass123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OTPServiceTestCase(TestCase):
    """Tests for OTP service functionality"""

    def test_otp_generation(self):
        """Test OTP generation creates valid code"""
        otp = OTPService.generate_otp()

        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_otp_verification_success(self):
        """Test OTP verification with valid code"""
        email = "test@example.com"
        otp = OTPService.create_otp(email)

        result = OTPService.verify_otp(email, otp)

        self.assertTrue(result)

    def test_otp_verification_fails_wrong_code(self):
        """Test OTP verification fails with wrong code"""
        email = "test@example.com"
        OTPService.create_otp(email)

        result = OTPService.verify_otp(email, "000000")

        self.assertFalse(result)

    def test_otp_single_use(self):
        """Test OTP can only be used once"""
        email = "test@example.com"
        otp = OTPService.create_otp(email)

        first_attempt = OTPService.verify_otp(email, otp)
        second_attempt = OTPService.verify_otp(email, otp)

        self.assertTrue(first_attempt)
        self.assertFalse(second_attempt)
