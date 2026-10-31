from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.mixins import CustomerQuerySetMixin
from apps.accounts.permissions import (
    IsCustomerOwnerOrStaffAdmin,
    IsStaffOrAdmin,
)
from apps.platform.exceptions import InvalidTransition
from apps.subscriptions.models import QuotationTemplate, Subscription
from apps.subscriptions.serializers import (
    QuotationTemplateSerializer,
    SubscriptionActionSerializer,
    SubscriptionSerializer,
)
from apps.subscriptions.services import transition_subscription


class QuotationTemplateViewSet(ModelViewSet):
    permission_classes = (IsStaffOrAdmin,)
    serializer_class = QuotationTemplateSerializer
    queryset = QuotationTemplate.objects.select_related("plan", "plan__product").order_by("id")


class SubscriptionViewSet(CustomerQuerySetMixin, ModelViewSet):
    serializer_class = SubscriptionSerializer
    queryset = (
        Subscription.objects.select_related("customer__user", "plan", "plan__product")
        .prefetch_related("lines")
        .order_by("id")
    )

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsCustomerOwnerOrStaffAdmin()]
        return [IsStaffOrAdmin()]

    def _transition(self, request, to_status):
        input_serializer = SubscriptionActionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            subscription = transition_subscription(
                self.get_object(),
                to_status,
                actor=request.user,
                **input_serializer.validated_data,
            )
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"])
    def quotation(self, request, pk=None):
        return self._transition(request, Subscription.Status.QUOTATION)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._transition(request, Subscription.Status.CONFIRMED)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._transition(request, Subscription.Status.ACTIVE)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        return self._transition(request, Subscription.Status.PAUSED)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._transition(request, Subscription.Status.CLOSED)

    @action(detail=True, methods=["post"])
    def renew(self, request, pk=None):
        return self._transition(request, Subscription.Status.ACTIVE)
