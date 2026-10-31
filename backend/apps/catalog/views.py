from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsAdminOrStaffReadOnly
from apps.catalog.models import Product, Tax, Variant
from apps.catalog.serializers import ProductSerializer, TaxSerializer, VariantSerializer


class ProductViewSet(ModelViewSet):
    permission_classes = (IsAdminOrStaffReadOnly,)
    serializer_class = ProductSerializer
    queryset = Product.objects.order_by("id")


class VariantViewSet(ModelViewSet):
    permission_classes = (IsAdminOrStaffReadOnly,)
    serializer_class = VariantSerializer
    queryset = Variant.objects.select_related("product").order_by("id")


class TaxViewSet(ModelViewSet):
    permission_classes = (IsAdminOrStaffReadOnly,)
    serializer_class = TaxSerializer
    queryset = Tax.objects.order_by("id")
