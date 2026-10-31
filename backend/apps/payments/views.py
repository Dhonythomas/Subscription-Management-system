from rest_framework import status
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.permissions import IsStaffOrAdmin
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer
from apps.payments.services import InvalidPayment, record_payment


class PaymentViewSet(
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet
):
    permission_classes = (IsStaffOrAdmin,)
    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related("invoice").order_by("id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, invoice = record_payment(
                **serializer.validated_data, actor=request.user
            )
        except InvalidPayment as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response_data = self.get_serializer(payment).data
        response_data["invoice_status"] = invoice.status
        return Response(response_data, status=status.HTTP_201_CREATED)
