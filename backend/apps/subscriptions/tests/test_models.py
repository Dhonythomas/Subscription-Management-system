import pytest
from decimal import Decimal
from django.utils import timezone

from apps.subscriptions.models import Subscription, SubscriptionLine
from apps.accounts.models import Customer
from apps.catalog.models import Product, Tax
from apps.plans.models import Plan


@pytest.mark.django_db
def test_subscription_number_is_unique():
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
    customer = Customer.objects.create(user=__import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.create_user(email="c1@example.com", password="Secret123!"), name="Acme")
    Subscription.objects.create(number="SUB-001", customer=customer, plan=plan, start_date=timezone.now().date(), expiry_date=timezone.now().date(), payment_terms="Net 30")
    with pytest.raises(Exception):
        Subscription.objects.create(number="SUB-001", customer=customer, plan=plan, start_date=timezone.now().date(), expiry_date=timezone.now().date(), payment_terms="Net 30")


@pytest.mark.django_db
def test_subscription_line_decimal_fields():
    qty = SubscriptionLine._meta.get_field("qty")
    unit_price = SubscriptionLine._meta.get_field("unit_price")
    amount = SubscriptionLine._meta.get_field("amount")
    assert qty.max_digits == 12
    assert qty.decimal_places == 2
    assert unit_price.max_digits == 12
    assert unit_price.decimal_places == 2
    assert amount.max_digits == 12
    assert amount.decimal_places == 2


@pytest.mark.django_db
def test_subscription_status_index():
    indexes = {index.name: index.fields for index in Subscription._meta.indexes}
    assert indexes["sub_status_billing_idx"] == ["status", "next_billing_date"]
    assert Subscription._meta.db_table == "subscriptions"
    assert SubscriptionLine._meta.db_table == "subscription_lines"
    assert __import__("apps.subscriptions.models", fromlist=["QuotationTemplate"]).QuotationTemplate._meta.db_table == "quotation_templates"
