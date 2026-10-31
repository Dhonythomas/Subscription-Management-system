from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.subscriptions.views import QuotationTemplateViewSet, SubscriptionViewSet

router = SimpleRouter()
router.register("", SubscriptionViewSet, basename="subscription")

urlpatterns = [
    path(
        "templates/",
        QuotationTemplateViewSet.as_view({"get": "list", "post": "create"}),
        name="quotation-template-list",
    ),
    path(
        "templates/<int:pk>/",
        QuotationTemplateViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="quotation-template-detail",
    ),
] + router.urls
