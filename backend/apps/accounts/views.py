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
from apps.accounts.permissions import IsAdmin, IsStaffOrAdmin
from apps.accounts.serializers import (
    CustomerSerializer,
    CustomerRegistrationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RoleTokenObtainPairSerializer,
    StaffCreateSerializer,
    UserSerializer,
)
from apps.accounts.services import (
    create_customer_account,
    create_staff_account,
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


class CustomerRegistrationView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_customer_account(**serializer.validated_data)
        response_data = RoleTokenObtainPairSerializer.token_response_for(user)
        response_data["customer"] = CustomerSerializer(user.customer).data
        return Response(response_data, status=status.HTTP_201_CREATED)


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
            user_id = force_str(
                urlsafe_base64_decode(serializer.validated_data["uidb64"])
            )
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


class StaffCreateView(APIView):
    permission_classes = (IsAdmin,)

    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_staff_account(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


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
        return [IsStaffOrAdmin()]
