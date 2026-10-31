from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Customer, Role, User


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    @staticmethod
    def customer_id_for(user):
        if user.role != Role.CUSTOMER:
            return None
        return (
            Customer.objects.filter(user_id=user.pk)
            .values_list("pk", flat=True)
            .first()
        )

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        token["customer_id"] = cls.customer_id_for(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.pk,
            "email": self.user.email,
            "role": self.user.role,
            "customer_id": self.customer_id_for(self.user),
        }
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "role", "is_active", "date_joined")
        read_only_fields = ("id", "date_joined")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("id", "email", "password", "role", "is_active")
        read_only_fields = ("id",)

    def validate_role(self, value):
        if value == Role.ADMIN:
            raise serializers.ValidationError("Admin users cannot be created through this endpoint.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "user",
            "name",
            "billing_email",
            "billing_address",
            "billing_phone",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")
