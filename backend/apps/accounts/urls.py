from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    CustomerViewSet,
    MeView,
    StaffCreateView,
)

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("staff/", StaffCreateView.as_view(), name="staff-create"),
    path("", include(router.urls)),
]
