from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from datetime import datetime
import uuid


from .managers import UserManager

# Create your models here.


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(unique=True, max_length=20, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = email
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"
        verbose_name = "User"
        verbose_name_plural = "Users"

        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        if self.email:
            return self.email


class MagicLinkToken(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="MagicLinkToken"
    )
    token = models.CharField(unique=True)
    ip_address = models.IPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "magic_link_token"
        verbose_name = "Magic Link Token"
        verbose_name_plural = "Magic Link Tokens"

    def is_valid(self):
        """Check if the token is valid (not used and not expired)"""
        current_time = datetime.now()
        return not self.is_used and current_time < self.expires_at

    def mark_as_used(self):
        """Mark the token as used"""
        self.is_used = True
        self.save()

    def __str__(self):
        return f"MagicLinkToken token[{self.token}] for {self.user.email}"


class JWTTokenRegistry(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="JWTTokenRegistry"
    )
    # JWT ID for identifying and tracking the token
    token_jti = models.CharField(unique=True, max_length=32)
    # Token type: access or refresh
    token_type = models.CharField(max_length=10)
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    device_info = models.TextField(blank=True)
    ip_address = models.IPAddressField(null=True, blank=True)
    is_blacklisted = models.BooleanField(default=False)
    blacklisted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["token_jti"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"JWTTokenRegistry token_jti[{self.token_jti}] for {self.user.email}"


class AuthenticationAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="AuthenticationAuditLog"
    )
    action = models.CharField(max_length=255)
    sucess = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.IPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    token_jti = models.CharField(max_length=32, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "authentication_audit_log"
        verbose_name = "Authentication Audit Log"
        verbose_name_plural = "Authentication Audit Logs"

        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return (f"AuditLog action...({"SUCESS" if self.sucess else 'FAILED'})...{self.action} for {self.user.email}  at {self.timestamp}")
