import pytest
from decimal import Decimal
from django.utils import timezone

from apps.catalog.models import Product
from apps.plans.models import Plan


@pytest.mark.django_db
def test_plan_defaults_and_flags():
    product = Product.objects.create(
        name="Platform",
        type=Product.Type.SERVICE,
        sales_price=Decimal("500.00"),
        cost_price=Decimal("150.00"),
    )
    plan = Plan.objects.create(
        product=product,
        price=Decimal("500.00"),
        period=Plan.Period.MONTHLY,
        start_date=timezone.now().date(),
    )

    assert plan.min_qty == 1
    assert plan.auto_close is False
    assert plan.closable is False
    assert plan.pausable is False
    assert plan.renewable is False
    assert plan.is_active is True
    assert plan.product == product


@pytest.mark.django_db
def test_plan_money_and_index():
    price_field = Plan._meta.get_field("price")
    assert price_field.max_digits == 12
    assert price_field.decimal_places == 2

    indexes = {index.name: index.fields for index in Plan._meta.indexes}
    assert indexes["plan_period_idx"] == ["period"]
    assert Plan._meta.db_table == "plans"
