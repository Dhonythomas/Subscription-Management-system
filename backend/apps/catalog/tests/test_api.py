from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product, Tax, Variant


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="catalog-staff@example.com",
        password="StaffPassword123!",
        role=Role.STAFF,
        is_staff=True,
    )


@pytest.mark.django_db
def test_admin_creates_product_with_decimal_prices(api_client, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/catalog/products/",
        {
            "name": "Brightloop License",
            "type": Product.Type.SERVICE,
            "sales_price": "120.00",
            "cost_price": "40.00",
            "notes": "Annual license",
        },
        format="json",
    )

    assert response.status_code == 201
    product = Product.objects.get(pk=response.data["id"])
    assert product.sales_price == Decimal("120.00")
    assert product.cost_price == Decimal("40.00")
    assert product.is_active is True


@pytest.mark.django_db
def test_staff_can_read_products_but_cannot_write(api_client, staff_user, product):
    api_client.force_authenticate(staff_user)

    listing = api_client.get("/api/catalog/products/")
    update = api_client.patch(
        f"/api/catalog/products/{product.pk}/",
        {"sales_price": "999.00"},
        format="json",
    )

    assert listing.status_code == 200
    assert listing.data["count"] == 1
    assert update.status_code == 403


@pytest.mark.django_db
def test_customer_cannot_access_catalog_or_plans(api_client, customer, plan):
    api_client.force_authenticate(customer.user)

    assert api_client.get("/api/catalog/products/").status_code == 403
    assert api_client.get("/api/plans/").status_code == 403


@pytest.mark.django_db
def test_anonymous_cannot_access_catalog(api_client):
    response = api_client.get("/api/catalog/products/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_admin_creates_variant_and_tax(api_client, user, product):
    api_client.force_authenticate(user)

    variant_response = api_client.post(
        "/api/catalog/variants/",
        {
            "product": product.pk,
            "attribute": "brand",
            "value": "Odoo",
            "price_delta": "560.00",
        },
        format="json",
    )
    tax_response = api_client.post(
        "/api/catalog/taxes/",
        {"name": "VAT", "rate": "18.00"},
        format="json",
    )

    assert variant_response.status_code == 201
    assert tax_response.status_code == 201
    variant = Variant.objects.get(pk=variant_response.data["id"])
    tax = Tax.objects.get(pk=tax_response.data["id"])
    assert variant.product == product
    assert variant.price_delta == Decimal("560.00")
    assert tax.rate == Decimal("18.00")


@pytest.mark.django_db
def test_tax_rate_and_product_price_validation(api_client, user):
    api_client.force_authenticate(user)

    negative_product = api_client.post(
        "/api/catalog/products/",
        {
            "name": "Invalid",
            "type": Product.Type.GOODS,
            "sales_price": "-1.00",
            "cost_price": "0.00",
        },
        format="json",
    )
    invalid_tax = api_client.post(
        "/api/catalog/taxes/",
        {"name": "Invalid", "rate": "100.01"},
        format="json",
    )

    assert negative_product.status_code == 400
    assert invalid_tax.status_code == 400


@pytest.mark.django_db
def test_product_list_does_not_scale_queries(
    api_client, staff_user, django_assert_max_num_queries
):
    Product.objects.bulk_create(
        [
            Product(
                name=f"Product {index}",
                type=Product.Type.SERVICE,
                sales_price=Decimal("10.00"),
                cost_price=Decimal("5.00"),
            )
            for index in range(30)
        ]
    )
    api_client.force_authenticate(staff_user)

    with django_assert_max_num_queries(3):
        response = api_client.get("/api/catalog/products/")

    assert response.status_code == 200
    assert response.data["count"] == 30
    assert len(response.data["results"]) == 25
