from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.billing.models import Invoice
from apps.payments.models import Payment
from apps.platform.money import quantize_money
from apps.reports.models import DailyMetrics
from apps.subscriptions.models import Subscription

MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)


def _monthly_revenue(price, period):
    if period == "daily":
        return price * 30
    if period == "weekly":
        return price * Decimal("52") / Decimal("12")
    if period == "yearly":
        return price / 12
    return price


def compute_metrics(on_date=None):
    on_date = on_date or timezone.localdate()
    active = Subscription.objects.filter(status=Subscription.Status.ACTIVE)
    active_count = active.count()
    mrr = quantize_money(
        sum(
            (
                _monthly_revenue(price, period)
                for price, period in active.values_list("plan__price", "plan__period")
            ),
            Decimal("0.00"),
        )
    )

    revenue = Payment.objects.filter(paid_on=on_date).aggregate(
        total=Coalesce(Sum("amount"), Value(Decimal("0.00")), output_field=MONEY_FIELD)
    )["total"]
    confirmed = (
        Invoice.objects.filter(status=Invoice.Status.CONFIRMED)
        .annotate(
            paid=Coalesce(
                Sum(
                    "payment__amount",
                    filter=Q(payment__paid_on__lte=on_date),
                ),
                Value(Decimal("0.00")),
                output_field=MONEY_FIELD,
            )
        )
        .annotate(balance=F("total") - F("paid"))
    )
    outstanding = confirmed.aggregate(
        total=Coalesce(Sum("balance"), Value(Decimal("0.00")), output_field=MONEY_FIELD)
    )["total"]
    overdue = confirmed.filter(due_date__lt=on_date, balance__gt=0).count()

    return {
        "active_subscriptions": active_count,
        "revenue_collected": quantize_money(revenue),
        "outstanding": quantize_money(outstanding),
        "overdue_invoices": overdue,
        "mrr": mrr,
        "arr": quantize_money(mrr * 12),
    }


def refresh_daily_metrics(on_date=None):
    on_date = on_date or timezone.localdate()
    metrics, _ = DailyMetrics.objects.update_or_create(
        date=on_date, defaults=compute_metrics(on_date)
    )
    return metrics
