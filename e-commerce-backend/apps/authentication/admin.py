from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import User, LoginHistory, SecurityClaim


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model with comprehensive management features.
    """

    list_display = [
        "email",
        "full_name",
        "is_verified",
        "is_active",
        "is_staff",
        "provider_badge",
        "date_joined",
        "last_login_at",
        "login_count",
    ]

    list_filter = [
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "provider",
        "date_joined",
    ]

    search_fields = ["email", "first_name", "last_name"]

    ordering = ["-date_joined"]

    readonly_fields = [
        "id",
        "date_joined",
        "last_login_at",
        "password",
        "login_count",
        "recent_logins",
        "security_claims_count",
    ]

    fieldsets = (
        ("Account Information", {"fields": ("id", "email", "password")}),
        ("Personal Information", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Social Authentication",
            {"fields": ("provider", "provider_id"), "classes": ("collapse",)},
        ),
        ("Important Dates", {"fields": ("date_joined", "last_login_at")}),
        (
            "Statistics",
            {
                "fields": ("login_count", "recent_logins", "security_claims_count"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            "Account Information",
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
        (
            "Personal Information",
            {
                "fields": ("first_name", "last_name"),
            },
        ),
        (
            "Permissions",
            {
                "fields": ("is_staff", "is_superuser", "is_verified"),
            },
        ),
    )

    def full_name(self, obj):
        """Display user's full name or email if name is not set."""
        name = obj.get_full_name()
        return name if name else obj.email

    full_name.short_description = "Name"

    def provider_badge(self, obj):
        """Display a badge for social authentication provider."""
        if obj.provider:
            colors = {
                "google": "#4285F4",
                "facebook": "#1877F2",
                "github": "#333333",
            }
            color = colors.get(obj.provider, "#666666")
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
                color,
                obj.provider.upper(),
            )
        return format_html('<span style="color: #999;">Email</span>')

    provider_badge.short_description = "Auth Method"

    def login_count(self, obj):
        """Display total number of login attempts."""
        count = obj.login_history.filter(login_successful=True).count()
        if count > 0:
            app_label = obj._meta.app_label
            url = (
                reverse(f"admin:{app_label}_loginhistory_changelist")
                + f"?user__id__exact={obj.id}&login_successful__exact=1"
            )
            return format_html('<a href="{}">{} logins</a>', url, count)
        return "0 logins"

    login_count.short_description = "Successful Logins"

    def recent_logins(self, obj):
        """Display recent login locations."""
        recent = obj.login_history.filter(login_successful=True)[:3]
        if not recent:
            return "No login history"

        items = []
        for login in recent:
            location = f"{login.city}, {login.country}" if login.city else login.country
            if not location:
                location = login.ip_address
            items.append(
                f"• {location} ({login.created_at.strftime('%Y-%m-%d %H:%M')})"
            )

        return format_html("<br>".join(items))

    recent_logins.short_description = "Recent Login Locations"

    def security_claims_count(self, obj):
        """Display count of unresolved security claims."""
        unresolved = obj.security_claims.filter(resolved=False).count()
        if unresolved > 0:
            app_label = obj._meta.app_label
            url = (
                reverse(f"admin:{app_label}_securityclaim_changelist")
                + f"?user__id__exact={obj.id}&resolved__exact=0"
            )
            return format_html(
                '<a href="{}" style="color: red; font-weight: bold;">{} unresolved</a>',
                url,
                unresolved,
            )
        return format_html('<span style="color: green;">No issues</span>')

    security_claims_count.short_description = "Security Alerts"


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing login history and tracking user authentication attempts.
    """

    list_display = [
        "user",
        "ip_address",
        "location_display",
        "login_status",
        "created_at",
    ]

    list_filter = [
        "login_successful",
        "country",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "ip_address",
        "country",
        "city",
    ]

    readonly_fields = [
        "id",
        "user",
        "ip_address",
        "user_agent",
        "country",
        "country_code",
        "city",
        "region",
        "latitude",
        "longitude",
        "login_successful",
        "failure_reason",
        "created_at",
    ]

    ordering = ["-created_at"]

    fieldsets = (
        ("User Information", {"fields": ("user", "created_at")}),
        ("Connection Details", {"fields": ("ip_address", "user_agent")}),
        (
            "Location Information",
            {
                "fields": (
                    "country",
                    "country_code",
                    "city",
                    "region",
                    "latitude",
                    "longitude",
                )
            },
        ),
        ("Login Status", {"fields": ("login_successful", "failure_reason")}),
    )

    def has_add_permission(self, request):
        """Prevent manual creation of login history records."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of login history records."""
        return False

    def location_display(self, obj):
        """Display formatted location information."""
        if obj.city and obj.country:
            return f"{obj.city}, {obj.country}"
        elif obj.country:
            return obj.country
        return "Unknown"

    location_display.short_description = "Location"

    def login_status(self, obj):
        """Display login status with color coding."""
        if obj.login_successful:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Success</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Failed</span><br>'
                '<span style="color: #666; font-size: 11px;">{}</span>',
                obj.failure_reason or "Unknown reason",
            )

    login_status.short_description = "Status"


@admin.register(SecurityClaim)
class SecurityClaimAdmin(admin.ModelAdmin):
    """
    Admin interface for managing security claims and monitoring suspicious activity.
    """

    list_display = [
        "user",
        "claim_type_badge",
        "description_preview",
        "ip_address",
        "resolution_status",
        "created_at",
    ]

    list_filter = [
        "claim_type",
        "resolved",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "description",
        "ip_address",
    ]

    readonly_fields = [
        "id",
        "user",
        "claim_type",
        "description",
        "ip_address",
        "created_at",
    ]

    ordering = ["-created_at"]

    fieldsets = (
        (
            "Claim Information",
            {
                "fields": (
                    "id",
                    "user",
                    "claim_type",
                    "description",
                    "ip_address",
                    "created_at",
                )
            },
        ),
        ("Resolution", {"fields": ("resolved", "resolved_at")}),
    )

    actions = ["mark_as_resolved", "mark_as_unresolved"]

    def claim_type_badge(self, obj):
        """Display claim type with color-coded badge."""
        colors = {
            "suspicious_login": "#FF6B6B",
            "multiple_failed_attempts": "#FFA500",
            "unusual_location": "#4ECDC4",
            "account_locked": "#E74C3C",
        }
        color = colors.get(obj.claim_type, "#95A5A6")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            "border-radius: 4px; font-size: 11px; font-weight: bold; "
            'text-transform: uppercase;">{}</span>',
            color,
            obj.get_claim_type_display(),
        )

    claim_type_badge.short_description = "Type"

    def description_preview(self, obj):
        """Display truncated description."""
        max_length = 60
        if len(obj.description) > max_length:
            return obj.description[:max_length] + "..."
        return obj.description

    description_preview.short_description = "Description"

    def resolution_status(self, obj):
        """Display resolution status with visual indicator."""
        if obj.resolved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Resolved</span><br>'
                '<span style="color: #666; font-size: 11px;">{}</span>',
                obj.resolved_at.strftime("%Y-%m-%d %H:%M") if obj.resolved_at else "",
            )
        else:
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠ Pending</span>'
            )

    resolution_status.short_description = "Status"

    def mark_as_resolved(self, request, queryset):
        """Mark selected claims as resolved."""
        from django.utils import timezone

        updated = queryset.update(resolved=True, resolved_at=timezone.now())
        self.message_user(request, f"{updated} security claim(s) marked as resolved.")

    mark_as_resolved.short_description = "Mark selected claims as resolved"

    def mark_as_unresolved(self, request, queryset):
        """Mark selected claims as unresolved."""
        updated = queryset.update(resolved=False, resolved_at=None)
        self.message_user(request, f"{updated} security claim(s) marked as unresolved.")

    mark_as_unresolved.short_description = "Mark selected claims as unresolved"
