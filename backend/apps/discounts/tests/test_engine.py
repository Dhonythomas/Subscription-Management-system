from datetime import date
from decimal import Decimal

import pytest
from django.db.models import Sum

from apps.accounts.models import Customer, Role, User
from apps.billing.models import Invoice
from apps.billing.services import generate_invoice_for_subscription, run_billing
from apps.catalog.models import Product
from apps.discounts.models import Discount, DiscountUsage
from apps.subscriptions.models import Subscription, SubscriptionLine
from apps.subscriptions.services import transition_subscription


def active_subscription(subscription, user, next_billing_date=date(2026, 11, 1)):
    for status in (
        Subscription.Status.QUOTATION,
        Subscription.Status.CONFIRMED,
        Subscription.Status.ACTIVE,
    ):
        subscription = transition_subscription(subscription, status, actor=user)
    subscription.next_billing_date = next_billing_date
    subscription.save(update_fields=["next_billing_date"])
    return subscription


def percent_discount(**overrides):
    values = {
        "name": "Ten percent",
        "type": Discount.Type.PERCENT,
        "value": Decimal("10.00"),
        "scope": Discount.Scope.SUBSCRIPTION,
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "usage_limit": 5,
    }
    values.update(overrides)
    return Discount.objects.create(**values)


@pytest.mark.django_db
def test_percent_subscription_discount_applies_to_invoice(
    subscription, plan, product, tax, user
):
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        tax=tax,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    subscription = active_subscription(subscription, user)
    discount = percent_discount()

    invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 1))

    discount.refresh_from_db()
    invoice_line = invoice.lines.get()
    assert invoice.subtotal == Decimal("500.00")
    assert invoice.discount == Decimal("50.00")
    assert invoice.tax == Decimal("81.00")
    assert invoice.total == Decimal("531.00")
    assert invoice_line.discount == Decimal("50.00")
    assert discount.used_count == 1
    assert DiscountUsage.objects.filter(discount=discount, invoice=invoice).count() == 1


@pytest.mark.django_db
def test_product_discount_only_targets_matching_lines(
    subscription, plan, product, user
):
    other_product = Product.objects.create(
        name="Support",
        type=Product.Type.SERVICE,
        sales_price=Decimal("200.00"),
        cost_price=Decimal("50.00"),
    )
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=other_product,
        qty=Decimal("1.00"),
        unit_price=Decimal("200.00"),
        amount=Decimal("200.00"),
    )
    subscription = active_subscription(subscription, user)
    discount = percent_discount(
        name="Product credit",
        type=Discount.Type.FIXED,
        value=Decimal("100.00"),
        scope=Discount.Scope.PRODUCT,
    )
    discount.products.add(product)

    invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 1))

    assert invoice.discount == Decimal("100.00")
    assert invoice.total == Decimal("600.00")
    product_line = invoice.lines.get(description=product.name)
    other_line = invoice.lines.get(description=other_product.name)
    assert product_line.discount == Decimal("100.00")
    assert other_line.discount == Decimal("0.00")


@pytest.mark.django_db
def test_usage_limit_is_respected_across_billing_runs(
    subscription, plan, product, user, customer
):
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    first = active_subscription(subscription, user)

    other_user = User.objects.create_user(
        email="discount-second@example.com",
        password="CustomerPassword123!",
        role=Role.CUSTOMER,
    )
    other_customer = Customer.objects.create(user=other_user, name="Second Customer")
    second = Subscription.objects.create(
        number="SUB-200",
        customer=other_customer,
        plan=plan,
        start_date=date(2026, 11, 1),
        expiry_date=date(2027, 11, 1),
        payment_terms="Net 30",
    )
    SubscriptionLine.objects.create(
        subscription=second,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    active_subscription(second, user)
    discount = percent_discount(usage_limit=1)

    created = run_billing(date(2026, 11, 1))

    discount.refresh_from_db()
    assert created == 2
    assert discount.used_count == 1
    assert DiscountUsage.objects.filter(discount=discount).count() == 1
    total_discount = Invoice.objects.filter(
        subscription__in=[first.pk, second.pk]
    ).aggregate(total_discount=Sum("discount"))["total_discount"]
    assert total_discount == Decimal("50.00")


@pytest.mark.django_db
def test_expired_discount_is_not_applied(subscription, plan, product, user):
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    subscription = active_subscription(subscription, user)
    discount = percent_discount(end_date=date(2026, 10, 31))

    invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 1))

    discount.refresh_from_db()
    assert invoice.discount == Decimal("0.00")
    assert discount.used_count == 0
    assert not DiscountUsage.objects.exists()
