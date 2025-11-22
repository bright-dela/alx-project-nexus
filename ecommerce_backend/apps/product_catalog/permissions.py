from rest_framework import permissions


class IsStaffOnly(permissions.BasePermission):
    """
    Permission class that allows access only to staff users.
    Used for admin endpoints.
    """

    def has_permission(self, request, view):
        if not request.user:
            return False

        if not request.user.is_authenticated:
            return False

        is_staff = getattr(request.user, "is_staff", False)

        return bool(is_staff)

    def has_object_permission(self, request, view, obj):
        """
        Object-level permission check.
        Staff users can access all objects.
        """
        return self.has_permission(request, view)
