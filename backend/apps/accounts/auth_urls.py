from django.urls import path

from apps.accounts.views import PublicTokenRefreshView, RoleTokenObtainPairView

urlpatterns = [
    path("login/", RoleTokenObtainPairView.as_view(), name="login"),
    path("refresh/", PublicTokenRefreshView.as_view(), name="token_refresh"),
]
