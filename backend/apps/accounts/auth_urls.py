from django.urls import path

from apps.accounts.views import (
    CustomerRegistrationView,
    PublicTokenRefreshView,
    RoleTokenObtainPairView,
)

urlpatterns = [
    path("register/", CustomerRegistrationView.as_view(), name="register"),
    path("login/", RoleTokenObtainPairView.as_view(), name="login"),
    path("refresh/", PublicTokenRefreshView.as_view(), name="token_refresh"),
]
