from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsAdminRole(BasePermission):
    message = "Only admin users may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsAdminOrStaffRole(BasePermission):
    message = "Only admin or staff users may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {Role.ADMIN, Role.STAFF}
        )
