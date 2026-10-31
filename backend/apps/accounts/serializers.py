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

    @classmethod
    def user_data_for(cls, user):
        return {
            "id": user.pk,
            "email": user.email,
            "role": user.role,
            "customer_id": cls.customer_id_for(user),
        }

    @classmethod
    def token_response_for(cls, user):
        refresh = cls.get_token(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": cls.user_data_for(user),
        }

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = self.user_data_for(self.user)
        return data


class CustomerRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    name = serializers.CharField(max_length=255)
    billing_address = serializers.CharField(required=False, allow_blank=True)
    billing_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        privileged_fields = {"role", "is_staff", "is_superuser"}
        supplied = privileged_fields.intersection(self.initial_data)
        if supplied:
            raise serializers.ValidationError(
                {field: "This field is not accepted during customer registration." for field in sorted(supplied)}
            )
        return attrs


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
