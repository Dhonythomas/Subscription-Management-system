from rest_framework import serializers

from apps.discounts.models import Discount


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = (
            "id",
            "name",
            "type",
            "value",
            "min_amount",
            "min_qty",
            "scope",
            "products",
            "start_date",
            "end_date",
            "usage_limit",
            "used_count",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "used_count", "created_at", "updated_at")

    def validate_value(self, value):
        if value <= 0:
            raise serializers.ValidationError("Discount value must be positive.")
        return value

    def validate(self, attrs):
        discount_type = attrs.get("type", getattr(self.instance, "type", None))
        value = attrs.get("value", getattr(self.instance, "value", None))
        if discount_type == Discount.Type.PERCENT and value is not None and value > 100:
            raise serializers.ValidationError(
                {"value": "Percentage discounts cannot exceed 100."}
            )
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before start date."}
            )
        for field_name in ("min_amount", "min_qty"):
            field_value = attrs.get(
                field_name, getattr(self.instance, field_name, None)
            )
            if field_value is not None and field_value < 0:
                raise serializers.ValidationError(
                    {field_name: "Minimum values cannot be negative."}
                )
        return attrs
