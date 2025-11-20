from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Custom user manager for passwordless authentication with email as the identifier"""

    def create_user(self, email, password=None, **extra_fields):
        """Create users with only email"""

        if not email:
            raise ValueError("Users must have an email address")

        normalize_email = self.normalize_email(email)

        user = self.model(email=normalize_email, **extra_fields)

        if password:
            # Help create superusers with password
            user.set_password(password)

        user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create superusers with email and password"""

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        user = self.create_user(email, password, **extra_fields)

        return user
