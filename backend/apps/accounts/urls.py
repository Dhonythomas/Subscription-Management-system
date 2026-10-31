from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    CustomerViewSet,
    LoginView,
    ManagedUserViewSet,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)

router = DefaultRouter()
router.register("users", ManagedUserViewSet, basename="managed-user")
router.register("customers", CustomerViewSet, basename="customer")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
