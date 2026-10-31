import base64
import json
import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Customer, Role, User


def decode_jwt_claims(token):
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def test_jwt_signing_key_meets_hs256_minimum_length():
    signing_key = settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY)
    assert len(signing_key.encode("utf-8")) >= 32


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="AdminPassword123!",
        role=Role.ADMIN,
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com",
        password="StaffPassword123!",
        role=Role.STAFF,
        is_staff=True,
    )


@pytest.fixture
def customer_users(db):
    user_a = User.objects.create_user(
        email="customer-a@example.com",
        password="CustomerPassword123!",
        role=Role.CUSTOMER,
    )
    user_b = User.objects.create_user(
        email="customer-b@example.com",
        password="CustomerPassword123!",
        role=Role.CUSTOMER,
    )
    customer_a = Customer.objects.create(user=user_a, name="Customer A")
    customer_b = Customer.objects.create(user=user_b, name="Customer B")
    return user_a, user_b, customer_a, customer_b


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.ADMIN, Role.STAFF, Role.CUSTOMER])
def test_all_roles_can_log_in(api_client, role):
    user = User.objects.create_user(
        email=f"{role}@example.com",
        password="ValidPassword123!",
        role=role,
    )

    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "ValidPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    assert set(response.data) == {"access", "refresh", "user"}
    claims = decode_jwt_claims(response.data["access"])
    assert claims["role"] == role
    assert claims["email"] == user.email
    assert claims["customer_id"] is None
    assert response.data["user"]["role"] == role


@pytest.mark.django_db
def test_invalid_login_is_rejected(api_client, customer_users):
    user_a, *_ = customer_users

    response = api_client.post(
        "/api/auth/login/",
        {"email": user_a.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_customer_login_includes_customer_id_claim(api_client, customer_users):
    user_a, _, customer_a, _ = customer_users
    response = api_client.post(
        "/api/auth/login/",
        {"email": user_a.email, "password": "CustomerPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    claims = decode_jwt_claims(response.data["access"])
    assert claims["customer_id"] == customer_a.pk
    assert response.data["user"]["customer_id"] == customer_a.pk


@pytest.mark.django_db
def test_refresh_returns_access_token_with_same_role_claim(api_client, staff_user):
    login = api_client.post(
        "/api/auth/login/",
        {"email": staff_user.email, "password": "StaffPassword123!"},
        format="json",
    )
    assert login.status_code == 200

    response = api_client.post(
        "/api/auth/refresh/",
        {"refresh": login.data["refresh"]},
        format="json",
    )

    assert response.status_code == 200
    assert decode_jwt_claims(response.data["access"])["role"] == Role.STAFF


@pytest.mark.django_db
def test_jwt_bearer_token_authenticates_protected_profile(api_client, staff_user):
    login = api_client.post(
        "/api/auth/login/",
        {"email": staff_user.email, "password": "StaffPassword123!"},
        format="json",
    )
    assert login.status_code == 200
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
    )

    response = api_client.get("/api/accounts/me/")

    assert response.status_code == 200
    assert response.data["email"] == staff_user.email


@pytest.mark.django_db
def test_public_registration_creates_customer_and_returns_jwt(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "new-customer@example.com",
            "password": "CustomerPassword123!",
            "name": "New Customer",
            "billing_address": "12 Sample Road",
            "billing_phone": "+1 555 0100",
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="new-customer@example.com")
    customer = Customer.objects.get(user=user)
    assert user.role == Role.CUSTOMER
    assert user.is_staff is False
    assert user.is_superuser is False
    assert customer.name == "New Customer"
    assert customer.billing_address == "12 Sample Road"
    assert customer.billing_phone == "+1 555 0100"
    assert response.data["user"]["customer_id"] == customer.pk
    assert response.data["customer"]["id"] == customer.pk
    assert response.data["customer"]["name"] == "New Customer"
    assert decode_jwt_claims(response.data["access"])["customer_id"] == customer.pk
    assert response.data["refresh"]


@pytest.mark.django_db
def test_registration_rejects_weak_password_without_creating_user(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "weak-password@example.com",
            "password": "weak",
            "name": "Weak Password",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "password" in response.data
    assert not User.objects.filter(email="weak-password@example.com").exists()


@pytest.mark.django_db
def test_registration_rejects_existing_email(api_client, customer_users):
    user_a, *_ = customer_users
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": user_a.email,
            "password": "CustomerPassword123!",
            "name": "Duplicate",
        },
        format="json",
    )

    assert response.status_code == 400
    assert User.objects.filter(email=user_a.email).count() == 1


@pytest.mark.django_db
def test_registration_rejects_privileged_role_fields(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "privilege-attempt@example.com",
            "password": "CustomerPassword123!",
            "name": "Privilege Attempt",
            "role": Role.ADMIN,
            "is_staff": True,
            "is_superuser": True,
        },
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="privilege-attempt@example.com").exists()


@pytest.mark.django_db
def test_admin_can_create_staff_account(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/accounts/staff/",
        {
            "email": "new-staff@example.com",
            "password": "ValidPassword123!",
        },
        format="json",
    )

    assert response.status_code == 201
    new_user = User.objects.get(email="new-staff@example.com")
    assert new_user.role == Role.STAFF
    assert new_user.is_staff is True
    assert new_user.is_active is True
    assert new_user.check_password("ValidPassword123!")
    assert response.data["role"] == Role.STAFF


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.STAFF, Role.CUSTOMER])
def test_staff_and_customer_cannot_create_staff(
    api_client, role, staff_user, customer_users
):
    user = staff_user if role == Role.STAFF else customer_users[0]
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/accounts/staff/",
        {"email": "blocked-staff@example.com", "password": "ValidPassword123!"},
        format="json",
    )

    assert response.status_code == 403
    assert not User.objects.filter(email="blocked-staff@example.com").exists()


@pytest.mark.django_db
def test_unauthenticated_cannot_create_staff(api_client):
    response = api_client.post(
        "/api/accounts/staff/",
        {"email": "anonymous-staff@example.com", "password": "ValidPassword123!"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password",
    ["shortA!", "alllowercase1!", "ALLUPPERCASE1!", "NoSpecial123"],
)
def test_staff_creation_enforces_password_policy(api_client, admin_user, password):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        "/api/accounts/staff/",
        {"email": "invalid-staff@example.com", "password": password},
        format="json",
    )

    assert response.status_code == 400
    assert "password" in response.data


@pytest.mark.django_db
def test_staff_creation_rejects_privileged_field_injection(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        "/api/accounts/staff/",
        {
            "email": "injected-staff@example.com",
            "password": "ValidPassword123!",
            "role": Role.ADMIN,
            "is_staff": False,
            "is_superuser": True,
        },
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="injected-staff@example.com").exists()


@pytest.mark.django_db
def test_customer_cannot_read_another_customer(api_client, customer_users):
    user_a, _, customer_a, customer_b = customer_users
    api_client.force_authenticate(user=user_a)

    list_response = api_client.get(reverse("customer-list"))
    detail_response = api_client.get(
        reverse("customer-detail", args=[customer_b.pk])
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.data["results"]] == [customer_a.pk]
    assert detail_response.status_code == 404


@pytest.mark.django_db
def test_staff_can_read_all_customers(api_client, staff_user, customer_users):
    api_client.force_authenticate(user=staff_user)

    response = api_client.get(reverse("customer-list"))

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_token_is_single_use(api_client, customer_users):
    user_a, *_ = customer_users
    request_response = api_client.post(
        "/api/auth/password-reset/",
        {"email": user_a.email},
        format="json",
    )
    assert request_response.status_code == 200
    assert len(mail.outbox) == 1

    reset_url = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
    query = parse_qs(urlparse(reset_url).query)
    payload = {
        "uidb64": query["uidb64"][0],
        "token": query["token"][0],
        "new_password": "NewPassword123!",
    }

    first_reset = api_client.post(
        "/api/auth/password-reset-confirm/", payload, format="json"
    )
    second_reset = api_client.post(
        "/api/auth/password-reset-confirm/", payload, format="json"
    )

    assert first_reset.status_code == 200
    assert second_reset.status_code == 400
    user_a.refresh_from_db()
    assert user_a.check_password("NewPassword123!")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_request_does_not_reveal_unknown_email(api_client, customer_users):
    user_a, *_ = customer_users
    known = api_client.post(
        "/api/auth/password-reset/", {"email": user_a.email}, format="json"
    )
    unknown = api_client.post(
        "/api/auth/password-reset/",
        {"email": "missing@example.com"},
        format="json",
    )

    assert known.status_code == unknown.status_code == 200
    assert known.data == unknown.data
    assert len(mail.outbox) == 1


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_RESET_TIMEOUT=-1,
)
def test_password_reset_rejects_expired_token(api_client, customer_users):
    user_a, *_ = customer_users
    request_response = api_client.post(
        "/api/auth/password-reset/", {"email": user_a.email}, format="json"
    )
    assert request_response.status_code == 200
    reset_url = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
    query = parse_qs(urlparse(reset_url).query)

    response = api_client.post(
        "/api/auth/password-reset-confirm/",
        {
            "uidb64": query["uidb64"][0],
            "token": query["token"][0],
            "new_password": "NewPassword123!",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Invalid or expired reset token."


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_rejects_weak_new_password(api_client, customer_users):
    user_a, *_ = customer_users
    request_response = api_client.post(
        "/api/auth/password-reset/", {"email": user_a.email}, format="json"
    )
    assert request_response.status_code == 200
    reset_url = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
    query = parse_qs(urlparse(reset_url).query)

    response = api_client.post(
        "/api/auth/password-reset-confirm/",
        {
            "uidb64": query["uidb64"][0],
            "token": query["token"][0],
            "new_password": "weak",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "new_password" in response.data


@pytest.mark.django_db
def test_password_reset_rejects_malformed_uid_and_token(api_client):
    response = api_client.post(
        "/api/auth/password-reset-confirm/",
        {"uidb64": "%%%", "token": "invalid", "new_password": "NewPassword123!"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Invalid or expired reset token."
