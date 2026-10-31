import pytest
from decimal import Decimal

from apps.catalog.models import Product, Tax, Variant


@pytest.mark.django_db
def test_product_money_fields_are_decimal_with_two_places():
    sales_price = Product._meta.get_field("sales_price")
    cost_price = Product._meta.get_field("cost_price")
    assert sales_price.max_digits == 12
    assert sales_price.decimal_places == 2
    assert cost_price.max_digits == 12
    assert cost_price.decimal_places == 2


@pytest.mark.django_db
def test_create_product_and_tax_and_variant():
    product = Product.objects.create(
        name="Brightloop License",
        type=Product.Type.SERVICE,
        sales_price=Decimal("120.00"),
        cost_price=Decimal("40.00"),
        notes="Annual license",
    )
    tax = Tax.objects.create(name="VAT", rate=Decimal("18.00"))
    variant = Variant.objects.create(
        product=product,
        attribute="brand",
        value="Odoo",
        price_delta=Decimal("560.00"),
    )

    assert product.sales_price == Decimal("120.00")
    assert product.cost_price == Decimal("40.00")
    assert str(product) == "Brightloop License"
    assert tax.rate == Decimal("18.00")
    assert variant.price_delta == Decimal("560.00")
    assert variant.product == product
    assert Product._meta.db_table == "products"
    assert Variant._meta.db_table == "variants"
    assert Tax._meta.db_table == "taxes"
