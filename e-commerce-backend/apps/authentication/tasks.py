import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_verification_email_task(self, user_email, user_first_name, otp):
    """
    Send email verification OTP to a newly registered user.
    This task is configured to automatically retry up to 3 times if it fails.
    
    Args:
        self: Task instance
        user_email: Recipient's email address
        user_first_name: User's first name for personalization
        otp: The one-time password code to send

    Returns:
        dict: Status information about the email sending operation
    """

    subject = "Verify Your Email Address - Nexus E-commerce"

    # Use the first name if available, otherwise "Customer"
    greeting_name = user_first_name if user_first_name else "Customer"

    message = f"""
Hello {greeting_name},

Welcome to Nexus E-commerce! Please verify your email address to complete your registration.

Your verification code is: {otp}

This code will expire in 10 minutes.

If you didn't create an account, please ignore this email.

Best regards,
Nexus E-commerce Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )

        logger.info(f"Verification email sent successfully to {user_email}")

        return {
            "status": "success",
            "email": user_email,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(
            f"Failed to send verification email to {user_email}. "
            f"Attempt {self.request.retries + 1} of 3. Error: {str(e)}"
        )

        # Re-raise the exception so Celery can handle the retry logic
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_password_reset_email_task(self, user_email, otp):
    """
    Send password reset OTP to a user who requested to reset their password.

    Args:
        self: Task instance
        user_email: Recipient's email address
        otp: The one-time password code for password reset

    Returns:
        dict: Status information about the email sending operation
    """

    subject = "Password Reset Request - Nexus E-commerce"

    message = f"""
Hello,

You requested to reset your password for your Nexus E-commerce account.

Your password reset code is: {otp}

This code will expire in 10 minutes.

If you didn't request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
Nexus E-commerce Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )

        logger.info(f"Password reset email sent successfully to {user_email}")

        return {
            "status": "success",
            "email": user_email,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(
            f"Failed to send password reset email to {user_email}. "
            f"Attempt {self.request.retries + 1} of 3. Error: {str(e)}"
        )
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_security_alert_email_task(
    self, user_email, user_first_name, claim_type, details
):
    """
    Send security alert email when unusual activity is detected.

    Args:
        self: Task instance
        user_email: Recipient's email address
        user_first_name: User's first name for personalization
        claim_type: Type of security claim (e.g., "unusual_location")
        details: Detailed description of the security event

    Returns:
        dict: Status information about the email sending operation
    """

    subject = "Security Alert - Unusual Activity Detected"

    greeting_name = user_first_name if user_first_name else "Customer"
    current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    message = f"""
Hello {greeting_name},

We detected unusual activity on your Nexus E-commerce account:

Alert Type: {claim_type}
Details: {details}
Time: {current_time}

If this was you, you can safely ignore this email. Otherwise, we recommend:
1. Changing your password immediately
2. Reviewing your recent login history
3. Enabling two-factor authentication (coming soon)

If you need assistance, please contact our support team.

Best regards,
Nexus E-commerce Security Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )

        logger.info(
            f"Security alert email sent successfully to {user_email}. "
            f"Alert type: {claim_type}"
        )

        return {
            "status": "success",
            "email": user_email,
            "alert_type": claim_type,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(
            f"Failed to send security alert to {user_email}. "
            f"Attempt {self.request.retries + 1} of 3. Error: {str(e)}"
        )
        raise


@shared_task(bind=True)
def send_bulk_notification_task(self, email_list, subject, message):
    """
    Send bulk notifications to multiple users.

    This is useful for promotional emails, system announcements, or other
    communications that need to reach multiple users. 

    Args:
        self: Task instance
        email_list: List of email addresses to send to
        subject: Email subject line
        message: Email message body

    Returns:
        dict: Statistics about the bulk send operation
    """
    
    success_count = 0
    failure_count = 0
    failed_emails = []

    logger.info(f"Starting bulk email send to {len(email_list)} recipients")

    for email in email_list:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            success_count += 1

        except Exception as e:
            failure_count += 1
            failed_emails.append(email)
            logger.error(f"Failed to send bulk email to {email}: {str(e)}")

    logger.info(
        f"Bulk email completed. Success: {success_count}, Failed: {failure_count}"
    )

    return {
        "status": "completed",
        "total": len(email_list),
        "success": success_count,
        "failed": failure_count,
        "failed_emails": failed_emails,
        "task_id": self.request.id,
    }
