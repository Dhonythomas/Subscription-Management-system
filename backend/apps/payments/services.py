from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.billing.models import Invoice
from apps.billing.services import transition_invoice
from apps.payments.models import Payment
from apps.platform.money import quantize_money
from apps.platform.services import emit_event


class InvalidPayment(ValueError):
    pass


def record_payment(
    *, invoice, method, amount, paid_on=None, note="", actor=None
):
    amount = quantize_money(amount)
    if amount <= 0:
        raise InvalidPayment("Payment amount must be positive.")

    with transaction.atomic():
        locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if locked_invoice.status != Invoice.Status.CONFIRMED:
            raise InvalidPayment("Payments can only be recorded against confirmed invoices.")

        previous_total = (
            Payment.objects.filter(invoice=locked_invoice).aggregate(total=Sum("amount"))[
                "total"
            ]
            or Decimal("0.00")
        )
        if previous_total + amount > locked_invoice.total:
            raise InvalidPayment("Payment exceeds the invoice balance.")

        payment = Payment.objects.create(
            invoice=locked_invoice,
            method=method,
            amount=amount,
            paid_on=paid_on or timezone.localdate(),
            note=note,
        )
        emit_event(
            event_type="payment.recorded",
            aggregate_type="payments.payment",
            aggregate_id=str(payment.pk),
            payload={
                "payment_id": payment.pk,
                "invoice_id": locked_invoice.pk,
                "amount": str(amount),
                "method": method,
            },
        )

        updated_invoice = locked_invoice
        if previous_total + amount == locked_invoice.total:
            updated_invoice = transition_invoice(
                locked_invoice, Invoice.Status.PAID, actor=actor
            )
        return payment, updated_invoice
