from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Invoice
from apps.billing.services import transition_invoice
from apps.payments.models import Payment
from apps.reports.models import DailyMetrics
from apps.reports.services import refresh_daily_metrics
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import transition_subscription


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_subscription(subscription, user):
    for status in (
        Subscription.Status.QUOTATION,
        Subscription.Status.CONFIRMED,
        Subscription.Status.ACTIVE,
    ):
        subscription = transition_subscription(subscription, status, actor=user)
    return subscription


@pytest.fixture
def confirmed_overdue_invoice(invoice, user):
    invoice.due_date = date(2026, 10, 31)
    invoice.save(update_fields=["due_date"])
    return transition_invoice(invoice, Invoice.Status.CONFIRMED, actor=user)


@pytest.mark.django_db
def test_refresh_daily_metrics_computes_finance_snapshot(
    active_subscription, confirmed_overdue_invoice
):
    Payment.objects.create(
        invoice=confirmed_overdue_invoice,
        method=Payment.Method.BANK,
        amount=Decimal("100.00"),
        paid_on=date(2026, 11, 1),
    )

    metrics = refresh_daily_metrics(date(2026, 11, 1))

    assert metrics.active_subscriptions == 1
    assert metrics.revenue_collected == Decimal("100.00")
    assert metrics.outstanding == Decimal("490.00")
    assert metrics.overdue_invoices == 1
    assert metrics.mrr == Decimal("500.00")
    assert metrics.arr == Decimal("6000.00")


@pytest.mark.django_db
def test_refresh_daily_metrics_is_idempotent(active_subscription):
    refresh_daily_metrics(date(2026, 11, 1))
    metrics = refresh_daily_metrics(date(2026, 11, 1))

    assert DailyMetrics.objects.count() == 1
    assert metrics.date == date(2026, 11, 1)


@pytest.mark.django_db
def test_dashboard_api_returns_finance_metrics(
    api_client, user, active_subscription, confirmed_overdue_invoice
):
    Payment.objects.create(
        invoice=confirmed_overdue_invoice,
        method=Payment.Method.BANK,
        amount=Decimal("100.00"),
        paid_on=date(2026, 11, 1),
    )
    api_client.force_authenticate(user)

    response = api_client.get("/api/reports/dashboard/?date=2026-11-01")

    assert response.status_code == 200
    assert response.data["active_subscriptions"] == 1
    assert response.data["mrr"] == "500.00"
    assert response.data["arr"] == "6000.00"
    assert response.data["outstanding"] == "490.00"


@pytest.mark.django_db
def test_customer_cannot_access_reports(api_client, customer):
    api_client.force_authenticate(customer.user)

    assert api_client.get("/api/reports/dashboard/").status_code == 403
    assert api_client.get("/api/reports/metrics/").status_code == 403


@pytest.mark.django_db
def test_metrics_list_is_paginated(api_client, user):
    for day in range(1, 28):
        DailyMetrics.objects.create(
            date=date(2026, 10, day),
            active_subscriptions=day,
            revenue_collected=Decimal("0.00"),
            outstanding=Decimal("0.00"),
            overdue_invoices=0,
            mrr=Decimal("0.00"),
            arr=Decimal("0.00"),
        )
    api_client.force_authenticate(user)

    response = api_client.get("/api/reports/metrics/")

    assert response.status_code == 200
    assert response.data["count"] == 27
    assert len(response.data["results"]) == 25
