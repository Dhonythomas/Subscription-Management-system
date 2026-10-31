from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.mixins import CustomerQuerySetMixin
from apps.accounts.permissions import IsCustomerOwnerOrStaffAdmin, IsStaffOrAdmin
from apps.billing.models import Invoice
from apps.billing.pdf import generate_invoice_pdf
from apps.billing.serializers import InvoiceSerializer
from apps.billing.services import transition_invoice
from apps.platform.exceptions import InvalidTransition


class InvoiceViewSet(CustomerQuerySetMixin, ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = (
        Invoice.objects.select_related("customer__user", "subscription")
        .prefetch_related("lines")
        .order_by("id")
    )

    def get_permissions(self):
        if self.action in {"list", "retrieve", "pdf"}:
            return [IsCustomerOwnerOrStaffAdmin()]
        return [IsStaffOrAdmin()]

    def _transition(self, request, to_status):
        try:
            invoice = transition_invoice(
                self.get_object(), to_status, actor=request.user
            )
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._transition(request, Invoice.Status.CONFIRMED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition(request, Invoice.Status.CANCELLED)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        invoice = self.get_object()
        response = HttpResponse(
            generate_invoice_pdf(invoice), content_type="application/pdf"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{invoice.number}.pdf"'
        )
        return response
