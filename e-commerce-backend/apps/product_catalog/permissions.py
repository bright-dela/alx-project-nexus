from rest_framework import permissions


class IsStaffOrReadOnly(permissions.BasePermission):
    """Allow read-only access for anyone, write only for staff users"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        is_staff = getattr(request.user, "is_staff", False)
        
        if request.user and request.user.is_authenticated and is_staff:
            return True