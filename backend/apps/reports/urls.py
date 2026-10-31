from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.reports.views import DailyMetricsViewSet, DashboardView

router = SimpleRouter()
router.register("metrics", DailyMetricsViewSet, basename="daily-metrics")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
] + router.urls
