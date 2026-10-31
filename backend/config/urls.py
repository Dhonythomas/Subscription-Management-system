from django.contrib import admin
from django.urls import include, path

from apps.platform.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/auth/", include("apps.accounts.auth_urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/plans/", include("apps.plans.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/reports/", include("apps.reports.urls")),
]
