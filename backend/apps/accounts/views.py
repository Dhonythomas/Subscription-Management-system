from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import Customer, Role
from apps.accounts.permissions import IsAdminOrStaffRole, IsAdminRole
from apps.accounts.serializers import (
    CustomerSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RoleTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from apps.accounts.services import (
    create_managed_user,
    send_password_reset,
)
User = get_user_model()


class RoleTokenObtainPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = RoleTokenObtainPairSerializer


class PublicTokenRefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)
    authentication_classes = ()


class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"],
            is_active=True,
        ).first()
        if user is not None:
            send_password_reset(user=user)
        return Response(
            {"detail": "If the account exists, a reset email has been sent."}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(
            user, serializer.validated_data["token"]
        ):
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=("password",))
        return Response({"detail": "Password reset successful."})


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ManagedUserViewSet(ModelViewSet):
    permission_classes = (IsAdminRole,)
    serializer_class = UserSerializer
    queryset = User.objects.order_by("id")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = create_managed_user(**serializer.validated_data)
        serializer.instance = user


class CustomerViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = CustomerSerializer

    def get_queryset(self):
        queryset = Customer.objects.select_related("user").order_by("id")
        if self.request.user.role in {Role.ADMIN, Role.STAFF}:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsAdminOrStaffRole()]
