from django.db import models

from apps.platform.models import TimeStampedModel


class DailyMetrics(TimeStampedModel):
    date = models.DateField(unique=True)
    active_subscriptions = models.PositiveIntegerField(default=0)
    revenue_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overdue_invoices = models.PositiveIntegerField(default=0)
    mrr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    arr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "daily_metrics"

    def __str__(self):
        return f"DailyMetrics {self.date}"
