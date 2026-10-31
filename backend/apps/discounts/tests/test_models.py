import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.utils import timezone

from apps.discounts.models import Discount, DiscountUsage


@pytest.mark.django_db
def test_discount_money_and_index():
    value = Discount._meta.get_field("value")
    min_amount = Discount._meta.get_field("min_amount")
    assert value.max_digits == 12
    assert value.decimal_places == 2
    assert min_amount.max_digits == 12
    assert min_amount.decimal_places == 2
    discount = Discount.objects.create(
        name="Welcome",
        type=Discount.Type.FIXED,
        value=Decimal("50.00"),
        scope=Discount.Scope.SUBSCRIPTION,
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
        usage_limit=10,
    )
    indexes = {index.name: index.fields for index in Discount._meta.indexes}
    assert indexes["discount_dates_idx"] == ["start_date", "end_date"]
    assert Discount._meta.db_table == "discounts"


@pytest.mark.django_db
def test_discount_usage_uniqueness(discount, subscription, invoice):
    DiscountUsage.objects.create(discount=discount, subscription=subscription, invoice=invoice)
    with pytest.raises(IntegrityError):
        DiscountUsage.objects.create(discount=discount, subscription=subscription, invoice=invoice)
    assert DiscountUsage._meta.db_table == "discount_usage"
