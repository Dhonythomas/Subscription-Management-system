from apps.accounts.models import Role


class CustomerQuerySetMixin:
    customer_user_lookup = "customer__user"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role in {Role.ADMIN, Role.STAFF}:
            return queryset
        if user.role == Role.CUSTOMER:
            return queryset.filter(**{self.customer_user_lookup: user})
        return queryset.none()
