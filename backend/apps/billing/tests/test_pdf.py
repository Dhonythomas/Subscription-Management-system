import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Customer, Role, User
from apps.billing.models import Invoice
from apps.billing.services import transition_invoice


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def confirmed_invoice(invoice, user):
    return transition_invoice(invoice, Invoice.Status.CONFIRMED, actor=user)


@pytest.mark.django_db
def test_staff_can_download_invoice_pdf(api_client, user, confirmed_invoice):
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/billing/invoices/{confirmed_invoice.pk}/pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert confirmed_invoice.number in response["Content-Disposition"]
    assert response.content.startswith(b"%PDF-")


@pytest.mark.django_db
def test_customer_can_download_only_own_invoice_pdf(api_client, confirmed_invoice):
    other_user = User.objects.create_user(
        email="pdf-other@example.com",
        password="CustomerPassword123!",
        role=Role.CUSTOMER,
    )
    Customer.objects.create(user=other_user, name="Other Customer")

    api_client.force_authenticate(confirmed_invoice.customer.user)
    own = api_client.get(f"/api/billing/invoices/{confirmed_invoice.pk}/pdf/")
    api_client.force_authenticate(other_user)
    other = api_client.get(f"/api/billing/invoices/{confirmed_invoice.pk}/pdf/")

    assert own.status_code == 200
    assert own.content.startswith(b"%PDF-")
    assert other.status_code == 404
