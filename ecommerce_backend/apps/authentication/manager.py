from django.contrib.auth.models import BaseUserManager


class UserManage(BaseUserManager):
    """Custom user manager for passwordless authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")

        normalized_email = self.normalize_email(email)

        user = self.model(normalized_email, **extra_fields)

        if password:
            # Help create a superuser with a password
            user.set_password(password)

        # For passwordless users, set unusable password
        user.set_unusable_password()

        user.save(using=self._db)

        return user



    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)
