import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.discounts.models import Discount


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_admin_manages_discounts(api_client, user, product):
    api_client.force_authenticate(user)

    create = api_client.post(
        "/api/discounts/",
        {
            "name": "Launch 10%",
            "type": Discount.Type.PERCENT,
            "value": "10.00",
            "scope": Discount.Scope.SUBSCRIPTION,
            "start_date": "2026-11-01",
            "end_date": "2027-11-01",
            "usage_limit": 100,
            "products": [],
        },
        format="json",
    )
    listing = api_client.get("/api/discounts/")

    assert create.status_code == 201
    assert listing.status_code == 200
    assert listing.data["count"] == 1
    assert create.data["used_count"] == 0


@pytest.mark.django_db
def test_staff_cannot_manage_discounts(api_client):
    staff = User.objects.create_user(
        email="discount-staff@example.com",
        password="StaffPassword123!",
        role=Role.STAFF,
        is_staff=True,
    )
    api_client.force_authenticate(staff)

    assert api_client.get("/api/discounts/").status_code == 403


@pytest.mark.django_db
def test_discount_validation_rejects_invalid_percentage_and_dates(api_client, user):
    api_client.force_authenticate(user)

    invalid_percentage = api_client.post(
        "/api/discounts/",
        {
            "name": "Too much",
            "type": Discount.Type.PERCENT,
            "value": "101.00",
            "scope": Discount.Scope.SUBSCRIPTION,
            "start_date": "2026-11-01",
            "end_date": "2027-11-01",
        },
        format="json",
    )
    invalid_dates = api_client.post(
        "/api/discounts/",
        {
            "name": "Bad dates",
            "type": Discount.Type.FIXED,
            "value": "10.00",
            "scope": Discount.Scope.SUBSCRIPTION,
            "start_date": "2027-11-01",
            "end_date": "2026-11-01",
        },
        format="json",
    )

    assert invalid_percentage.status_code == 400
    assert invalid_dates.status_code == 400
