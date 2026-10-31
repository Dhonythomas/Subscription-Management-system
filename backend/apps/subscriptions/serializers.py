from django.db import transaction
from rest_framework import serializers

from apps.subscriptions.models import QuotationTemplate, Subscription, SubscriptionLine


class QuotationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationTemplate
        fields = (
            "id",
            "name",
            "plan",
            "validity_days",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_validity_days(self, value):
        if value < 1:
            raise serializers.ValidationError("Validity must be at least one day.")
        return value


class SubscriptionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionLine
        fields = ("id", "product", "variant", "tax", "qty", "unit_price", "amount")
        read_only_fields = ("id",)

    def validate(self, attrs):
        product = attrs.get("product", getattr(self.instance, "product", None))
        variant = attrs.get("variant", getattr(self.instance, "variant", None))
        if variant is not None and product is not None and variant.product_id != product.pk:
            raise serializers.ValidationError(
                {"variant": "Variant does not belong to the selected product."}
            )
        if attrs.get("qty", getattr(self.instance, "qty", 0)) <= 0:
            raise serializers.ValidationError({"qty": "Quantity must be positive."})
        for field in ("unit_price", "amount"):
            value = attrs.get(field, getattr(self.instance, field, 0))
            if value < 0:
                raise serializers.ValidationError({field: "Amount cannot be negative."})
        return attrs


class SubscriptionSerializer(serializers.ModelSerializer):
    lines = SubscriptionLineSerializer(many=True, required=False)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "number",
            "customer",
            "plan",
            "start_date",
            "expiry_date",
            "payment_terms",
            "status",
            "next_billing_date",
            "lines",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "next_billing_date",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        expiry_date = attrs.get("expiry_date", getattr(self.instance, "expiry_date", None))
        if start_date and expiry_date and expiry_date < start_date:
            raise serializers.ValidationError(
                {"expiry_date": "Expiry date cannot be before start date."}
            )
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        if plan is not None and not plan.is_active:
            raise serializers.ValidationError({"plan": "Plan is not active."})
        return attrs

    @staticmethod
    def _create_lines(subscription, lines):
        for line in lines:
            SubscriptionLine.objects.create(subscription=subscription, **line)

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        with transaction.atomic():
            subscription = Subscription.objects.create(**validated_data)
            self._create_lines(subscription, lines)
        return subscription

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        if lines is not None and instance.status not in {
            Subscription.Status.DRAFT,
            Subscription.Status.QUOTATION,
        }:
            raise serializers.ValidationError(
                {"lines": "Lines can only change while the subscription is draft or quotation."}
            )
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if lines is not None:
                instance.lines.all().delete()
                self._create_lines(instance, lines)
        return instance


class SubscriptionActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    at_expiry = serializers.BooleanField(required=False, default=False)
