from django.db import models

from apps.platform.models import TimeStampedModel


class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    ALLOWED_TRANSITIONS = {
        Status.DRAFT: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PAID, Status.CANCELLED},
        Status.PAID: set(),
        Status.CANCELLED: set(),
    }

    number = models.CharField(max_length=50, unique=True)
    subscription = models.ForeignKey("subscriptions.Subscription", on_delete=models.PROTECT)
    customer = models.ForeignKey("accounts.Customer", on_delete=models.PROTECT)
    period_start = models.DateField()
    period_end = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    due_date = models.DateField()

    class Meta:
        db_table = "invoices"
        indexes = [
            models.Index(fields=["status", "due_date"], name="invoice_status_due_idx"),
            models.Index(fields=["customer"], name="invoice_customer_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "period_start", "period_end"],
                name="uniq_invoice_subscription_period",
            ),
        ]

    def __str__(self):
        return self.number


class InvoiceLine(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "invoice_lines"
