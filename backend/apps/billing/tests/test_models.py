import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.utils import timezone

from apps.billing.models import Invoice, InvoiceLine
from apps.platform.models import AuditLog, OutboxEvent


@pytest.mark.django_db
def test_invoice_money_fields():
    subtotal = Invoice._meta.get_field("subtotal")
    tax = Invoice._meta.get_field("tax")
    discount = Invoice._meta.get_field("discount")
    total = Invoice._meta.get_field("total")
    for field in [subtotal, tax, discount, total]:
        assert field.max_digits == 12
        assert field.decimal_places == 2


@pytest.mark.django_db
def test_invoice_line_snapshot_fields(invoice):
    line = InvoiceLine.objects.create(
        invoice=invoice,
        description="License",
        quantity=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        tax_rate=Decimal("18.00"),
        discount=Decimal("0.00"),
        amount=Decimal("590.00"),
    )
    assert line.description == "License"
    assert line.quantity == Decimal("1.00")
    assert line.unit_price == Decimal("500.00")
    assert line.tax_rate == Decimal("18.00")
    assert line.discount == Decimal("0.00")
    assert line.amount == Decimal("590.00")
    assert InvoiceLine._meta.get_field("quantity").decimal_places == 2
    assert InvoiceLine._meta.get_field("unit_price").decimal_places == 2


@pytest.mark.django_db
def test_invoice_unique_subscription_period(invoice):
    with pytest.raises(IntegrityError):
        Invoice.objects.create(
            number="INV-002",
            subscription=invoice.subscription,
            customer=invoice.customer,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            subtotal=Decimal("500.00"),
            tax=Decimal("90.00"),
            discount=Decimal("0.00"),
            total=Decimal("590.00"),
            due_date=timezone.now().date(),
            status=Invoice.Status.DRAFT,
        )


@pytest.mark.django_db
def test_invoice_indexes():
    indexes = {index.name: index.fields for index in Invoice._meta.indexes}
    constraints = {constraint.name: constraint for constraint in Invoice._meta.constraints}
    assert indexes["invoice_status_due_idx"] == ["status", "due_date"]
    assert indexes["invoice_customer_idx"] == ["customer"]
    assert "uniq_invoice_subscription_period" in constraints
    assert Invoice._meta.db_table == "invoices"
    assert InvoiceLine._meta.db_table == "invoice_lines"
