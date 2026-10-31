from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Role


class IsAdmin(BasePermission):
    message = "Only admin users may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsStaff(BasePermission):
    message = "Only staff users may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.STAFF
        )


class IsCustomer(BasePermission):
    message = "Only customer users may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.CUSTOMER
        )


class IsStaffOrAdmin(BasePermission):
    message = "Only admin or staff users may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {Role.ADMIN, Role.STAFF}
        )


class IsAdminOrStaffReadOnly(BasePermission):
    message = "Only admin or staff users may view this resource; only admin may change it."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return request.user.role in {Role.ADMIN, Role.STAFF}
        return request.user.role == Role.ADMIN


class IsCustomerOwnerOrStaffAdmin(BasePermission):
    message = "You do not have permission to access this customer."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {Role.ADMIN, Role.STAFF, Role.CUSTOMER}
        )

    def has_object_permission(self, request, view, obj):
        if request.user.role in {Role.ADMIN, Role.STAFF}:
            return True
        if request.user.role != Role.CUSTOMER:
            return False
        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner.pk == request.user.pk
        customer = getattr(obj, "customer", None)
        return customer is not None and customer.user_id == request.user.pk
