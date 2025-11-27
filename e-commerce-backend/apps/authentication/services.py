import secrets
import requests
from django.conf import settings
from django.core.cache import caches
from django.utils import timezone
from datetime import timedelta
from .models import User, LoginHistory, SecurityClaim

import logging

logger = logging.getLogger(__name__)

from .tasks import (
    send_verification_email_task,
    send_password_reset_email_task,
    send_security_alert_email_task,
)

# Using auth_cache from settings
auth_cache = caches["auth_cache"]


class OTPService:
    """Service for managing OTP generation and verification using Django cache"""

    OTP_EXPIRY = 600  # 10 minutes in seconds
    OTP_LENGTH = 6

    @staticmethod
    def generate_otp():
        """Generate a cryptographically secure 6-digit OTP"""

        return "".join(
            [str(secrets.randbelow(10)) for _ in range(OTPService.OTP_LENGTH)]
        )

    @classmethod
    def create_otp(cls, email, purpose="verification"):
        """Create and store OTP in cache"""

        otp = cls.generate_otp()
        key = f"otp:{purpose}:{email}"
        auth_cache.set(key, otp, cls.OTP_EXPIRY)

        return otp

    @classmethod
    def verify_otp(cls, email, otp, purpose="verification"):
        """Verify OTP from cache"""

        key = f"otp:{purpose}:{email}"
        stored_otp = auth_cache.get(key)

        if not stored_otp:
            return False

        if stored_otp == otp:
            auth_cache.delete(key)
            return True
        else:
            return False

    @classmethod
    def delete_otp(cls, email, purpose="verification"):
        """Delete OTP from cache"""

        key = f"otp:{purpose}:{email}"
        auth_cache.delete(key)


class EmailService:
    """
    Service for managing email operations through Celery tasks.
    """

    @staticmethod
    def send_verification_email(user, otp):
        """
        Schedule a verification email to be sent asynchronously.

        Args:
            user: User model instance
            otp: One-time password for email verification

        Returns:
            AsyncResult: Celery task result object for tracking the task
        """

        task_result = send_verification_email_task.delay(
            user_email=user.email, user_first_name=user.first_name, otp=otp
        )

        logger.info(
            f"Verification email task queued for {user.email}. "
            f"Task ID: {task_result.id}"
        )

        return task_result


    @staticmethod
    def send_password_reset_email(email, otp):
        """
        Schedule a password reset email to be sent asynchronously.

        Args:
            email: Recipient's email address
            otp: One-time password for password reset

        Returns:
            AsyncResult: Celery task result object for tracking the task
        """

        task_result = send_password_reset_email_task.delay(user_email=email, otp=otp)

        logger.info(
            f"Password reset email task queued for {email}. "
            f"Task ID: {task_result.id}"
        )

        return task_result


    @staticmethod
    def send_security_alert(user, claim_type, details):
        """
        Schedule a security alert email to be sent asynchronously.

        Args:
            user: User model instance
            claim_type: Type of security claim (e.g., "unusual_location")
            details: Detailed description of the security event

        Returns:
            AsyncResult: Celery task result object for tracking the task
        """

        task_result = send_security_alert_email_task.delay(
            user_email=user.email,
            user_first_name=user.first_name,
            claim_type=claim_type,
            details=details,
        )

        logger.info(
            f"Security alert email task queued for {user.email}. "
            f"Alert type: {claim_type}. Task ID: {task_result.id}"
        )

        return task_result


class GeoLocationService:
    """Service for getting geolocation data from IP"""

    @staticmethod
    def get_location_from_ip(ip_address):
        """Get location data from IP address using ip-api.com (free tier)"""

        # Handle local/development IPs
        if ip_address in ["127.0.0.1", "localhost", "::1"]:
            return {
                "country": "Local",
                "country_code": "LC",
                "city": "Development",
                "region": "Local",
                "latitude": None,
                "longitude": None,
            }

        try:
            # Free tier allows 45 requests per minute
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == "success":
                    return {
                        "country": data.get("country", ""),
                        "country_code": data.get("countryCode", ""),
                        "city": data.get("city", ""),
                        "region": data.get("regionName", ""),
                        "latitude": data.get("lat"),
                        "longitude": data.get("lon"),
                    }
        except Exception as e:
        
            logger.error(f"Error fetching geolocation for {ip_address}: {e}")

        # Return empty data on error
        return {
            "country": "",
            "country_code": "",
            "city": "",
            "region": "",
            "latitude": None,
            "longitude": None,
        }


class LoginTrackingService:
    """Service for tracking login attempts and security"""

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 1800  # 30 minutes in seconds

    @classmethod
    def record_login_attempt(cls, user, request, success=True, failure_reason=""):
        """Record login attempt with IP and geolocation"""

        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        location_data = GeoLocationService.get_location_from_ip(ip_address)

        login_history = LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            login_successful=success,
            failure_reason=failure_reason,
            **location_data,
        )

        if success:
            user.last_login_at = timezone.now()
            user.save(update_fields=["last_login_at"])
            cls.reset_failed_attempts(user.email)
            cls.check_unusual_location(user, location_data, ip_address)
        else:
            cls.track_failed_attempt(user.email, ip_address)

        return login_history


    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
        return ip


    @classmethod
    def track_failed_attempt(cls, email, ip_address):
        """Track failed login attempts"""
        key = f"failed_login:{email}"

        # Get current count
        current_count = auth_cache.get(key, 0)
        failed_count = int(current_count) + 1

        # Set new count with expiry
        auth_cache.set(key, failed_count, cls.LOCKOUT_DURATION)

        if failed_count >= cls.MAX_FAILED_ATTEMPTS:
            cls.lock_account(email)
            try:
                user = User.objects.get(email=email)
                SecurityClaim.objects.create(
                    user=user,
                    claim_type="multiple_failed_attempts",
                    description=f"Account locked due to {failed_count} failed login attempts",
                    ip_address=ip_address,
                )
                # Send security alert asynchronously
                EmailService.send_security_alert(
                    user,
                    "Account Locked",
                    f"Your account has been temporarily locked due to {failed_count} failed login attempts from IP: {ip_address}",
                )
            except User.DoesNotExist:
                pass

    @classmethod
    def reset_failed_attempts(cls, email):
        """Reset failed login attempts counter"""
        key = f"failed_login:{email}"
        auth_cache.delete(key)
        cls.unlock_account(email)

    @classmethod
    def is_account_locked(cls, email):
        """Check if account is locked"""
        key = f"account_locked:{email}"
        return auth_cache.get(key) is not None

    @classmethod
    def lock_account(cls, email):
        """Lock account temporarily"""
        key = f"account_locked:{email}"
        auth_cache.set(key, "1", cls.LOCKOUT_DURATION)

    @classmethod
    def unlock_account(cls, email):
        """Unlock account"""
        key = f"account_locked:{email}"
        auth_cache.delete(key)

    @classmethod
    def check_unusual_location(cls, user, location_data, ip_address):
        """Check for unusual login location"""
        # Get recent successful logins (last 30 days)
        recent_logins = (
            LoginHistory.objects.filter(
                user=user,
                login_successful=True,
                created_at__gte=timezone.now() - timedelta(days=30),
            )
            .exclude(country="")
            .values_list("country", "city")
        )

        if recent_logins.exists():
            known_locations = set(recent_logins)
            current_location = (location_data["country"], location_data["city"])

            # Alert if login from completely new location
            if current_location not in known_locations and current_location != ("", ""):
                SecurityClaim.objects.create(
                    user=user,
                    claim_type="unusual_location",
                    description=f'Login from new location: {location_data["city"]}, {location_data["country"]}',
                    ip_address=ip_address,
                )
                # Send security alert asynchronously
                EmailService.send_security_alert(
                    user,
                    "Login from New Location",
                    f'We detected a login from {location_data["city"]}, {location_data["country"]} (IP: {ip_address})',
                )


class TokenBlacklistService:
    """Service for managing JWT token blacklisting"""

    @staticmethod
    def blacklist_token(jti, exp):
        """Add token to blacklist"""
        key = f"blacklist:{jti}"
        ttl = int(exp - timezone.now().timestamp())
        if ttl > 0:
            auth_cache.set(key, "1", ttl)

    @staticmethod
    def is_token_blacklisted(jti):
        """Check if token is blacklisted"""
        key = f"blacklist:{jti}"
        return auth_cache.get(key) is not None
