from django.db import models

from apps.platform.models import TimeStampedModel


class Discount(TimeStampedModel):
    class Type(models.TextChoices):
        FIXED = "fixed", "Fixed"
        PERCENT = "percent", "Percent"

    class Scope(models.TextChoices):
        PRODUCT = "product", "Product"
        SUBSCRIPTION = "subscription", "Subscription"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    products = models.ManyToManyField("catalog.Product", blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "discounts"
        indexes = [
            models.Index(fields=["start_date", "end_date"], name="discount_dates_idx"),
        ]

    def __str__(self):
        return self.name


class DiscountUsage(TimeStampedModel):
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT)
    subscription = models.ForeignKey("subscriptions.Subscription", on_delete=models.PROTECT)
    invoice = models.ForeignKey("billing.Invoice", on_delete=models.PROTECT)

    class Meta:
        db_table = "discount_usage"
        constraints = [
            models.UniqueConstraint(
                fields=["discount", "subscription", "invoice"],
                name="uniq_discount_usage",
            ),
        ]
        indexes = [
            models.Index(fields=["discount", "subscription", "invoice"], name="discount_usage_idx"),
        ]
