from django.db import models

from apps.platform.models import TimeStampedModel


class Product(TimeStampedModel):
    class Type(models.TextChoices):
        SERVICE = "service", "Service"
        GOODS = "goods", "Goods"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    sales_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name


class Variant(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    attribute = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    price_delta = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "variants"

    def __str__(self):
        return f"{self.product.name} - {self.attribute}: {self.value}"


class Tax(TimeStampedModel):
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "taxes"

    def __str__(self):
        return self.name
