from django.db import models

from apps.platform.models import TimeStampedModel


class Plan(TimeStampedModel):
    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.CharField(max_length=20, choices=Period.choices)
    min_qty = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    auto_close = models.BooleanField(default=False)
    closable = models.BooleanField(default=False)
    pausable = models.BooleanField(default=False)
    renewable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "plans"
        indexes = [models.Index(fields=["period"], name="plan_period_idx")]

    def __str__(self):
        return f"{self.product.name} ({self.period})"
