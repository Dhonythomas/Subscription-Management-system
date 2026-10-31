from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsAdminOrStaffReadOnly
from apps.plans.models import Plan
from apps.plans.serializers import PlanSerializer


class PlanViewSet(ModelViewSet):
    permission_classes = (IsAdminOrStaffReadOnly,)
    serializer_class = PlanSerializer
    queryset = Plan.objects.select_related("product").order_by("id")
