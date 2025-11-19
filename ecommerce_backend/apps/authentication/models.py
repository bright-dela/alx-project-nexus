from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
import uuid


from .managers import UserManager

# Create your models here.


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as the primary identifier"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email


class MagicLinkToken(models.Model):
    """Token for passwordless magic link authentication"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='magic_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'magic_link_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f'Magic link for {self.user.email}'
    
    def is_valid(self):
        """Check if token is still valid and unused"""
        return not self.is_used and self.expires_at > timezone.now()


class JWTTokenRegistry(models.Model):
    """Registry for tracking active JWT tokens"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jwt_tokens')
    token_jti = models.CharField(max_length=255, unique=True, db_index=True)
    token_type = models.CharField(max_length=10, choices=[('access', 'Access'), ('refresh', 'Refresh')])
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    device_fingerprint = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_blacklisted = models.BooleanField(default=False)
    blacklisted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'jwt_token_registry'
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['token_jti', 'is_blacklisted']),
            models.Index(fields=['user', 'token_type']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f'{self.token_type} token for {self.user.email}'


class AuthenticationAuditLog(models.Model):
    """Comprehensive audit log for authentication events"""
    
    ACTION_CHOICES = [
        ('magic_link_requested', 'Magic Link Requested'),
        ('magic_link_validated', 'Magic Link Validated'),
        ('token_refreshed', 'Token Refreshed'),
        ('logout', 'Logout'),
        ('failed_validation', 'Failed Validation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    token_jti = models.CharField(max_length=255, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'authentication_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'Unknown'
        return f'{self.action} by {user_email} at {self.timestamp}'
