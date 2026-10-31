import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.utils import timezone

from apps.reports.models import DailyMetrics


@pytest.mark.django_db
def test_daily_metrics_uniqueness_and_decimals():
    metrics = DailyMetrics.objects.create(
        date=timezone.now().date(),
        active_subscriptions=10,
        revenue_collected=Decimal("5900.00"),
        outstanding=Decimal("0.00"),
        overdue_invoices=0,
        mrr=Decimal("5900.00"),
        arr=Decimal("70800.00"),
    )
    with pytest.raises(IntegrityError):
        DailyMetrics.objects.create(date=metrics.date)
    for field in ["revenue_collected", "outstanding", "mrr", "arr"]:
        f = DailyMetrics._meta.get_field(field)
        assert f.max_digits == 12
        assert f.decimal_places == 2
    assert str(metrics) == f"DailyMetrics {metrics.date}"
    assert DailyMetrics._meta.db_table == "daily_metrics"
