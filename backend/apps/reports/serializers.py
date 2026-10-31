from rest_framework import serializers

from apps.reports.models import DailyMetrics


class DailyMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMetrics
        fields = (
            "id",
            "date",
            "active_subscriptions",
            "revenue_collected",
            "outstanding",
            "overdue_invoices",
            "mrr",
            "arr",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
