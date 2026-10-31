from django.db import models

from apps.platform.models import TimeStampedModel


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank"
        CARD = "card", "Card"
        OTHER = "other", "Other"

    invoice = models.ForeignKey("billing.Invoice", on_delete=models.PROTECT)
    method = models.CharField(max_length=20, choices=Method.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    note = models.TextField(blank=True)

    class Meta:
        db_table = "payments"
        indexes = [
            models.Index(fields=["invoice", "paid_on"], name="payment_invoice_paid_idx"),
        ]

    def __str__(self):
        return f"Payment {self.pk} - {self.amount}"
