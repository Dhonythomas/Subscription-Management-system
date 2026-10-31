from rest_framework import serializers

from apps.catalog.models import Product, Tax, Variant


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "type",
            "sales_price",
            "cost_price",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_sales_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Sales price cannot be negative.")
        return value

    def validate_cost_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Cost price cannot be negative.")
        return value


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = (
            "id",
            "product",
            "attribute",
            "value",
            "price_delta",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ("id", "name", "rate", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_rate(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return value
