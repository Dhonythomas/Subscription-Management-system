from django.conf import settings
from django.db import models

from apps.platform.models import TimeStampedModel


class QuotationTemplate(TimeStampedModel):
    name = models.CharField(max_length=255)
    plan = models.ForeignKey("plans.Plan", on_delete=models.PROTECT)
    validity_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "quotation_templates"

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUOTATION = "quotation", "Quotation"
        CONFIRMED = "confirmed", "Confirmed"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    ALLOWED_TRANSITIONS = {
        Status.DRAFT: {Status.QUOTATION},
        Status.QUOTATION: {Status.CONFIRMED},
        Status.CONFIRMED: {Status.ACTIVE},
        Status.ACTIVE: {Status.PAUSED, Status.CLOSED},
        Status.PAUSED: {Status.ACTIVE},
        Status.CLOSED: {Status.ACTIVE},
    }

    number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey("accounts.Customer", on_delete=models.PROTECT)
    plan = models.ForeignKey("plans.Plan", on_delete=models.PROTECT)
    start_date = models.DateField()
    expiry_date = models.DateField()
    payment_terms = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    next_billing_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "subscriptions"
        indexes = [
            models.Index(fields=["status", "next_billing_date"], name="sub_status_billing_idx"),
        ]

    def __str__(self):
        return self.number


class SubscriptionLine(TimeStampedModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    variant = models.ForeignKey("catalog.Variant", on_delete=models.PROTECT, null=True, blank=True)
    tax = models.ForeignKey("catalog.Tax", on_delete=models.PROTECT, null=True, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "subscription_lines"
