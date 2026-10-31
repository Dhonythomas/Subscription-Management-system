from django.contrib import admin
from django.urls import include, path

from apps.platform.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/accounts/", include("apps.accounts.urls")),
]
