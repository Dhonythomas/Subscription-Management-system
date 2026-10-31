from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.plans.models import Plan


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="plans-staff@example.com",
        password="StaffPassword123!",
        role=Role.STAFF,
        is_staff=True,
    )


@pytest.mark.django_db
def test_admin_creates_plan_with_flags(api_client, user, product):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/plans/",
        {
            "product": product.pk,
            "price": "500.00",
            "period": Plan.Period.MONTHLY,
            "min_qty": 1,
            "start_date": "2026-11-01",
            "end_date": "2027-11-01",
            "auto_close": False,
            "closable": True,
            "pausable": True,
            "renewable": True,
        },
        format="json",
    )

    assert response.status_code == 201
    plan = Plan.objects.get(pk=response.data["id"])
    assert plan.price == Decimal("500.00")
    assert plan.closable is True
    assert plan.pausable is True
    assert plan.renewable is True


@pytest.mark.django_db
def test_staff_can_read_plans_but_cannot_create(api_client, staff_user, plan):
    api_client.force_authenticate(staff_user)

    listing = api_client.get("/api/plans/")
    create = api_client.post(
        "/api/plans/",
        {
            "product": plan.product.pk,
            "price": "500.00",
            "period": Plan.Period.MONTHLY,
            "start_date": "2026-11-01",
        },
        format="json",
    )

    assert listing.status_code == 200
    assert listing.data["count"] == 1
    assert create.status_code == 403


@pytest.mark.django_db
def test_plan_rejects_end_date_before_start_date(api_client, user, product):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/plans/",
        {
            "product": product.pk,
            "price": "500.00",
            "period": Plan.Period.MONTHLY,
            "start_date": "2027-01-01",
            "end_date": "2026-01-01",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "end_date" in response.data


@pytest.mark.django_db
def test_plan_rejects_invalid_price_and_period(api_client, user, product):
    api_client.force_authenticate(user)

    negative_price = api_client.post(
        "/api/plans/",
        {
            "product": product.pk,
            "price": "-1.00",
            "period": Plan.Period.MONTHLY,
            "start_date": "2026-11-01",
        },
        format="json",
    )
    invalid_period = api_client.post(
        "/api/plans/",
        {
            "product": product.pk,
            "price": "10.00",
            "period": "hourly",
            "start_date": "2026-11-01",
        },
        format="json",
    )

    assert negative_price.status_code == 400
    assert invalid_period.status_code == 400


@pytest.mark.django_db
def test_plan_list_uses_select_related(
    api_client, staff_user, django_assert_max_num_queries
):
    plan = Plan.objects.create(
        product=Product.objects.create(
            name="Plan Product",
            type=Product.Type.SERVICE,
            sales_price=Decimal("10.00"),
            cost_price=Decimal("5.00"),
        ),
        price=Decimal("10.00"),
        period=Plan.Period.MONTHLY,
        start_date="2026-11-01",
    )
    api_client.force_authenticate(staff_user)

    with django_assert_max_num_queries(3):
        response = api_client.get("/api/plans/")

    assert response.status_code == 200
    assert response.data["results"][0]["id"] == plan.pk
