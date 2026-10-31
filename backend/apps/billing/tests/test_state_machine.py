import pytest
from django.utils import timezone

from apps.billing.models import Invoice
from apps.billing.services import transition_invoice
from apps.platform.exceptions import InvalidTransition
from apps.platform.models import AuditLog, OutboxEvent


@pytest.mark.django_db
def test_invoice_happy_path(user, invoice):
    transition_invoice(invoice, Invoice.Status.CONFIRMED, actor=user)
    transition_invoice(invoice, Invoice.Status.PAID, actor=user)
    assert invoice.status == Invoice.Status.PAID
    assert AuditLog.objects.filter(entity_type="billing.invoice").count() == 2
    assert OutboxEvent.objects.filter(event_type="invoice.status_changed").count() == 2


@pytest.mark.django_db
def test_invoice_cancel_from_draft(user, invoice):
    transition_invoice(invoice, Invoice.Status.CANCELLED, actor=user)
    assert invoice.status == Invoice.Status.CANCELLED


@pytest.mark.django_db
def test_invoice_cancel_from_confirmed(user, invoice):
    transition_invoice(invoice, Invoice.Status.CONFIRMED, actor=user)
    transition_invoice(invoice, Invoice.Status.CANCELLED, actor=user)
    assert invoice.status == Invoice.Status.CANCELLED


@pytest.mark.django_db
def test_illegal_paid_to_cancelled(user, invoice):
    transition_invoice(invoice, Invoice.Status.CONFIRMED, actor=user)
    transition_invoice(invoice, Invoice.Status.PAID, actor=user)
    with pytest.raises(InvalidTransition):
        transition_invoice(invoice, Invoice.Status.CANCELLED, actor=user)
    assert AuditLog.objects.filter(entity_type="billing.invoice").count() == 2
    assert OutboxEvent.objects.filter(event_type="invoice.status_changed").count() == 2
