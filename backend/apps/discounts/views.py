from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsAdmin
from apps.discounts.models import Discount
from apps.discounts.serializers import DiscountSerializer


class DiscountViewSet(ModelViewSet):
    permission_classes = (IsAdmin,)
    serializer_class = DiscountSerializer
    queryset = Discount.objects.prefetch_related("products").order_by("id")
