from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Customer, Role, User
from apps.catalog.models import Product
from apps.platform.models import AuditLog, OutboxEvent
from apps.subscriptions.models import Subscription


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="subscriptions-staff@example.com",
        password="StaffPassword123!",
        role=Role.STAFF,
        is_staff=True,
    )


def subscription_payload(customer, plan, number="SUB-100"):
    return {
        "number": number,
        "customer": customer.pk,
        "plan": plan.pk,
        "start_date": "2026-11-01",
        "expiry_date": "2027-11-01",
        "payment_terms": "Net 30",
        "lines": [
            {
                "product": plan.product.pk,
                "qty": "1.00",
                "unit_price": "500.00",
                "amount": "500.00",
            }
        ],
    }


@pytest.mark.django_db
def test_staff_creates_draft_subscription_with_lines(api_client, staff_user, customer, plan):
    api_client.force_authenticate(staff_user)

    response = api_client.post(
        "/api/subscriptions/",
        subscription_payload(customer, plan),
        format="json",
    )

    assert response.status_code == 201
    subscription = Subscription.objects.get(number="SUB-100")
    assert subscription.status == Subscription.Status.DRAFT
    assert subscription.lines.count() == 1
    assert subscription.lines.get().amount == Decimal("500.00")
    assert response.data["status"] == Subscription.Status.DRAFT


@pytest.mark.django_db
def test_customer_cannot_create_subscription(api_client, customer, plan):
    api_client.force_authenticate(customer.user)

    response = api_client.post(
        "/api/subscriptions/",
        subscription_payload(customer, plan),
        format="json",
    )

    assert response.status_code == 403
    assert not Subscription.objects.exists()


@pytest.mark.django_db
def test_staff_creates_quotation_template(api_client, staff_user, plan):
    api_client.force_authenticate(staff_user)

    response = api_client.post(
        "/api/subscriptions/templates/",
        {"name": "Annual quote", "plan": plan.pk, "validity_days": 30},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["name"] == "Annual quote"


@pytest.mark.django_db
def test_subscription_quote_to_active_flow_writes_audit_and_outbox(
    api_client, staff_user, customer, plan
):
    api_client.force_authenticate(staff_user)
    created = api_client.post(
        "/api/subscriptions/", subscription_payload(customer, plan), format="json"
    )
    subscription_id = created.data["id"]

    quotation = api_client.post(f"/api/subscriptions/{subscription_id}/quotation/", {}, format="json")
    confirmed = api_client.post(f"/api/subscriptions/{subscription_id}/confirm/", {}, format="json")
    active = api_client.post(f"/api/subscriptions/{subscription_id}/activate/", {}, format="json")

    assert quotation.status_code == 200
    assert confirmed.status_code == 200
    assert active.status_code == 200
    assert active.data["status"] == Subscription.Status.ACTIVE
    assert active.data["next_billing_date"] == "2026-11-01"
    assert AuditLog.objects.filter(entity_type="subscriptions.subscription").count() == 3
    assert OutboxEvent.objects.filter(event_type="subscription.status_changed").count() == 3


@pytest.mark.django_db
def test_illegal_subscription_transition_is_rejected(api_client, staff_user, customer, plan):
    api_client.force_authenticate(staff_user)
    created = api_client.post(
        "/api/subscriptions/", subscription_payload(customer, plan), format="json"
    )

    response = api_client.post(
        f"/api/subscriptions/{created.data['id']}/activate/", {}, format="json"
    )

    assert response.status_code == 400
    assert Subscription.objects.get(pk=created.data["id"]).status == Subscription.Status.DRAFT
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_raw_status_patch_does_not_change_state(api_client, staff_user, customer, plan):
    api_client.force_authenticate(staff_user)
    created = api_client.post(
        "/api/subscriptions/", subscription_payload(customer, plan), format="json"
    )

    response = api_client.patch(
        f"/api/subscriptions/{created.data['id']}/",
        {"status": Subscription.Status.ACTIVE},
        format="json",
    )

    assert response.status_code == 200
    assert Subscription.objects.get(pk=created.data["id"]).status == Subscription.Status.DRAFT


@pytest.mark.django_db
def test_customer_sees_only_own_subscriptions(api_client, customer, plan, staff_user):
    api_client.force_authenticate(staff_user)
    own = api_client.post(
        "/api/subscriptions/", subscription_payload(customer, plan), format="json"
    )
    other_user = User.objects.create_user(
        email="other-subscriber@example.com",
        password="CustomerPassword123!",
        role=Role.CUSTOMER,
    )
    other_customer = Customer.objects.create(user=other_user, name="Other Customer")
    other = api_client.post(
        "/api/subscriptions/",
        subscription_payload(other_customer, plan, number="SUB-OTHER"),
        format="json",
    )

    api_client.force_authenticate(customer.user)
    listing = api_client.get("/api/subscriptions/")
    own_detail = api_client.get(f"/api/subscriptions/{own.data['id']}/")
    other_detail = api_client.get(f"/api/subscriptions/{other.data['id']}/")

    assert listing.status_code == 200
    assert [row["id"] for row in listing.data["results"]] == [own.data["id"]]
    assert own_detail.status_code == 200
    assert other_detail.status_code == 404


@pytest.mark.django_db
def test_subscription_validation_rejects_invalid_dates_and_variant_product_mismatch(
    api_client, staff_user, customer, plan
):
    other_product = Product.objects.create(
        name="Other Product",
        type=Product.Type.SERVICE,
        sales_price=Decimal("10.00"),
        cost_price=Decimal("5.00"),
    )
    variant = other_product.variants.create(
        attribute="brand", value="Other", price_delta=Decimal("1.00")
    )
    payload = subscription_payload(customer, plan)
    payload["expiry_date"] = "2025-01-01"
    payload["lines"][0]["variant"] = variant.pk

    api_client.force_authenticate(staff_user)
    response = api_client.post("/api/subscriptions/", payload, format="json")

    assert response.status_code == 400
