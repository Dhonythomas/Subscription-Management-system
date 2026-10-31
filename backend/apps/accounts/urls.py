from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    CustomerViewSet,
    ManagedUserViewSet,
    MeView,
)

router = DefaultRouter()
router.register("users", ManagedUserViewSet, basename="managed-user")
router.register("customers", CustomerViewSet, basename="customer")

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
