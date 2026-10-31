from rest_framework import serializers

from apps.billing.models import Invoice, InvoiceLine


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = (
            "id",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "discount",
            "amount",
        )
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "number",
            "subscription",
            "customer",
            "period_start",
            "period_end",
            "subtotal",
            "tax",
            "discount",
            "total",
            "status",
            "due_date",
            "lines",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
