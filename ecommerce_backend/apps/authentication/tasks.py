from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

from .utility.passwordless_utils import PASSWORDLESS_CONFIG

logger = logging.getLogger(__name__)



@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_email(self, email, otp_code, first_name=None):
    """
    Send OTP code to user's email address.
    """
    subject = "Your Login Code"

    message = f"""
Hello {first_name},

Your one-time login code is: {otp_code}

This code will expire in {PASSWORDLESS_CONFIG.get('OTP_EXPIRY_MINUTES', 10)} minutes.

If you didn't request this code, please ignore this email.

Best regards,
Your Nexus Team
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(f"OTP email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        raise self.retry(exc=e)



@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_magic_link_email(self, email, magic_link, first_name=None):
    """
    Send magic link to user's email address.
    """
    subject = "Your Login Link"

    message = f"""
Hello {first_name},

Click the link below to log in to your account:

{magic_link}

This link will expire in {PASSWORDLESS_CONFIG.get('MAGIC_LINK_EXPIRY_MINUTES', 15)} minutes 
and can only be used once.

If you didn't request this link, please ignore this email.

Best regards,
Your Nexus Team
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(f"Magic link email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send magic link email to {email}: {str(e)}")
        raise self.retry(exc=e)




@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, email, first_name):
    """
    Send a welcome email when a new user registers.
    """
    subject = "Welcome to Our App!"

    message = f"""
Hello {first_name},

Welcome to our store — we're excited to have you join our shopping community!

You're now set up with passwordless authentication. No passwords needed! 
Simply use your email to log in anytime, and we’ll send you a secure code or magic link.

Feel free to browse our latest products, exclusive deals, and personalized recommendations. 
If you need any help, our support team is always here for you.

Happy shopping!
Your Nexus Team
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(f"Welcome email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        raise self.retry(exc=e)
