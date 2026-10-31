from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Customer, Role, User
from apps.billing.models import Invoice
from apps.billing.services import transition_invoice
from apps.payments.models import Payment
from apps.platform.models import AuditLog, OutboxEvent


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="payments-staff@example.com",
        password="StaffPassword123!",
        role=Role.STAFF,
        is_staff=True,
    )


@pytest.fixture
def confirmed_invoice(invoice, user):
    return transition_invoice(invoice, Invoice.Status.CONFIRMED, actor=user)


def payment_payload(invoice, amount="100.00"):
    return {
        "invoice": invoice.pk,
        "method": Payment.Method.BANK,
        "amount": amount,
        "paid_on": "2026-11-01",
        "note": "Bank transfer",
    }


@pytest.mark.django_db
def test_partial_payment_keeps_invoice_confirmed(
    api_client, staff_user, confirmed_invoice
):
    api_client.force_authenticate(staff_user)

    response = api_client.post(
        "/api/payments/", payment_payload(confirmed_invoice, "100.00"), format="json"
    )

    assert response.status_code == 201
    confirmed_invoice.refresh_from_db()
    assert confirmed_invoice.status == Invoice.Status.CONFIRMED
    assert Payment.objects.get(pk=response.data["id"]).amount == Decimal("100.00")


@pytest.mark.django_db
def test_full_payment_marks_invoice_paid(
    api_client, staff_user, confirmed_invoice, customer
):
    api_client.force_authenticate(staff_user)
    first = api_client.post(
        "/api/payments/", payment_payload(confirmed_invoice, "100.00"), format="json"
    )
    second = api_client.post(
        "/api/payments/", payment_payload(confirmed_invoice, "490.00"), format="json"
    )

    confirmed_invoice.refresh_from_db()
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.data["invoice_status"] == Invoice.Status.PAID
    assert confirmed_invoice.status == Invoice.Status.PAID
    assert Payment.objects.filter(invoice=confirmed_invoice).count() == 2
    assert AuditLog.objects.filter(
        entity_type="billing.invoice", to_status=Invoice.Status.PAID
    ).count() == 1
    assert OutboxEvent.objects.filter(event_type="payment.recorded").count() == 2


@pytest.mark.django_db
def test_overpayment_is_rejected(api_client, staff_user, confirmed_invoice):
    api_client.force_authenticate(staff_user)

    response = api_client.post(
        "/api/payments/", payment_payload(confirmed_invoice, "591.00"), format="json"
    )

    assert response.status_code == 400
    assert not Payment.objects.exists()
    confirmed_invoice.refresh_from_db()
    assert confirmed_invoice.status == Invoice.Status.CONFIRMED


@pytest.mark.django_db
def test_payment_requires_confirmed_invoice(api_client, staff_user, invoice):
    api_client.force_authenticate(staff_user)

    response = api_client.post(
        "/api/payments/", payment_payload(invoice, "100.00"), format="json"
    )

    assert response.status_code == 400
    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_customer_cannot_record_payment(api_client, customer, confirmed_invoice):
    api_client.force_authenticate(customer.user)

    response = api_client.post(
        "/api/payments/", payment_payload(confirmed_invoice, "100.00"), format="json"
    )

    assert response.status_code == 403
    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_staff_can_confirm_and_cancel_invoices(api_client, staff_user, invoice):
    api_client.force_authenticate(staff_user)

    confirm = api_client.post(f"/api/billing/invoices/{invoice.pk}/confirm/", {}, format="json")
    cancel = api_client.post(f"/api/billing/invoices/{invoice.pk}/cancel/", {}, format="json")

    assert confirm.status_code == 200
    assert cancel.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.CANCELLED


@pytest.mark.django_db
def test_illegal_invoice_action_is_rejected(api_client, staff_user, confirmed_invoice):
    api_client.force_authenticate(staff_user)
    api_client.post(
        "/api/payments/", payment_payload(confirmed_invoice, "590.00"), format="json"
    )

    response = api_client.post(
        f"/api/billing/invoices/{confirmed_invoice.pk}/cancel/", {}, format="json"
    )

    assert response.status_code == 400
    confirmed_invoice.refresh_from_db()
    assert confirmed_invoice.status == Invoice.Status.PAID


@pytest.mark.django_db
def test_customer_sees_only_own_invoices(api_client, staff_user, confirmed_invoice, plan):
    api_client.force_authenticate(staff_user)
    other_user = User.objects.create_user(
        email="other-invoice-customer@example.com",
        password="CustomerPassword123!",
        role=Role.CUSTOMER,
    )
    other_customer = Customer.objects.create(user=other_user, name="Other Customer")
    other_invoice = Invoice.objects.create(
        number="INV-OTHER",
        subscription=confirmed_invoice.subscription,
        customer=other_customer,
        period_start=date(2026, 12, 1),
        period_end=date(2026, 12, 31),
        subtotal=Decimal("10.00"),
        tax=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("10.00"),
        due_date=date(2027, 1, 30),
        status=Invoice.Status.CONFIRMED,
    )

    api_client.force_authenticate(confirmed_invoice.customer.user)
    listing = api_client.get("/api/billing/invoices/")
    own = api_client.get(f"/api/billing/invoices/{confirmed_invoice.pk}/")
    other = api_client.get(f"/api/billing/invoices/{other_invoice.pk}/")

    assert listing.status_code == 200
    assert [row["id"] for row in listing.data["results"]] == [confirmed_invoice.pk]
    assert own.status_code == 200
    assert other.status_code == 404
