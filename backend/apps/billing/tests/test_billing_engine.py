from datetime import date
from decimal import Decimal

import pytest

from apps.billing.models import Invoice, InvoiceLine
from apps.billing.services import generate_invoice_for_subscription, run_billing
from apps.platform.models import OutboxEvent
from apps.subscriptions.models import Subscription, SubscriptionLine
from apps.subscriptions.services import transition_subscription


def active_subscription(subscription, user):
    for status in (
        Subscription.Status.QUOTATION,
        Subscription.Status.CONFIRMED,
        Subscription.Status.ACTIVE,
    ):
        subscription = transition_subscription(subscription, status, actor=user)
    return subscription


@pytest.mark.django_db
def test_billing_generates_invoice_snapshots_and_advances_next_date(
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
    subscription.next_billing_date = date(2026, 11, 1)
    subscription.save(update_fields=["next_billing_date"])

    invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 1))

    assert invoice.period_start == date(2026, 11, 1)
    assert invoice.period_end == date(2026, 11, 30)
    assert invoice.subtotal == Decimal("500.00")
    assert invoice.tax == Decimal("90.00")
    assert invoice.total == Decimal("590.00")
    assert invoice.due_date == date(2026, 12, 30)
    line = InvoiceLine.objects.get(invoice=invoice)
    assert line.quantity == Decimal("1.00")
    assert line.unit_price == Decimal("500.00")
    assert line.tax_rate == Decimal("18.00")
    assert line.amount == Decimal("500.00")
    subscription.refresh_from_db()
    assert subscription.next_billing_date == date(2026, 12, 1)
    assert OutboxEvent.objects.filter(event_type="invoice.created").count() == 1


@pytest.mark.django_db
def test_billing_snapshot_survives_tax_change(
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
    subscription.next_billing_date = date(2026, 11, 1)
    subscription.save(update_fields=["next_billing_date"])
    invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 1))

    tax.rate = Decimal("25.00")
    tax.save(update_fields=["rate"])
    invoice.refresh_from_db()
    invoice_line = InvoiceLine.objects.get(invoice=invoice)

    assert invoice.tax == Decimal("90.00")
    assert invoice_line.tax_rate == Decimal("18.00")


@pytest.mark.django_db
def test_running_billing_twice_is_idempotent(subscription, plan, product, user):
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    subscription = active_subscription(subscription, user)
    subscription.next_billing_date = date(2026, 11, 1)
    subscription.save(update_fields=["next_billing_date"])

    first_run = run_billing(date(2026, 11, 1))
    second_run = run_billing(date(2026, 11, 1))

    assert first_run == 1
    assert second_run == 0
    assert Invoice.objects.filter(subscription=subscription).count() == 1


@pytest.mark.django_db
def test_billing_skips_non_active_subscription(subscription, product):
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    subscription.next_billing_date = date(2026, 11, 1)
    subscription.save(update_fields=["next_billing_date"])

    assert run_billing(date(2026, 11, 1)) == 0
    assert not Invoice.objects.exists()


@pytest.mark.django_db
def test_billing_supports_daily_and_yearly_periods(
    subscription, plan, product, user
):
    SubscriptionLine.objects.create(
        subscription=subscription,
        product=product,
        qty=Decimal("1.00"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    subscription = active_subscription(subscription, user)
    subscription.next_billing_date = date(2026, 11, 1)
    subscription.save(update_fields=["next_billing_date"])

    plan.period = plan.Period.DAILY
    plan.save(update_fields=["period"])
    daily_invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 1))
    assert daily_invoice.period_end == date(2026, 11, 1)

    subscription.refresh_from_db()
    assert subscription.next_billing_date == date(2026, 11, 2)
    plan.period = plan.Period.YEARLY
    plan.save(update_fields=["period"])
    yearly_invoice = generate_invoice_for_subscription(subscription.pk, date(2026, 11, 2))
    assert yearly_invoice.period_end == date(2027, 11, 1)
