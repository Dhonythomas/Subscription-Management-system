from datetime import date

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import IsStaffOrAdmin
from apps.reports.models import DailyMetrics
from apps.reports.serializers import DailyMetricsSerializer
from apps.reports.services import refresh_daily_metrics


class DashboardView(APIView):
    permission_classes = (IsStaffOrAdmin,)

    def get(self, request):
        requested_date = request.query_params.get("date")
        on_date = (
            date.fromisoformat(requested_date)
            if requested_date
            else timezone.localdate()
        )
        metrics = DailyMetrics.objects.filter(date=on_date).first()
        if metrics is None:
            metrics = refresh_daily_metrics(on_date)
        return Response(DailyMetricsSerializer(metrics).data)


class DailyMetricsViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsStaffOrAdmin,)
    serializer_class = DailyMetricsSerializer
    queryset = DailyMetrics.objects.order_by("-date")
