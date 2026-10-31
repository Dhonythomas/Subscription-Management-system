import pytest
from decimal import Decimal
from django.utils import timezone

from apps.payments.models import Payment


@pytest.mark.django_db
def test_payment_money_and_index(invoice):
    amount = Payment._meta.get_field("amount")
    assert amount.max_digits == 12
    assert amount.decimal_places == 2
    payment = Payment.objects.create(
        invoice=invoice,
        method=Payment.Method.BANK,
        amount=Decimal("590.00"),
        paid_on=timezone.now().date(),
        note="Paid",
    )
    indexes = {index.name: index.fields for index in Payment._meta.indexes}
    assert indexes["payment_invoice_paid_idx"] == ["invoice", "paid_on"]
    assert str(payment) == f"Payment {payment.pk} - 590.00"
    assert Payment._meta.db_table == "payments"
