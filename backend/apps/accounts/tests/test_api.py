import re

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Customer, Role, User


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
        reverse("login"),
        {"email": user.email, "password": "ValidPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    assert re.fullmatch(r"[0-9a-f]{40}", response.data["token"])
    assert response.data["user"]["role"] == role


@pytest.mark.django_db
def test_invalid_login_is_rejected(api_client, customer_users):
    user_a, *_ = customer_users

    response = api_client.post(
        reverse("login"),
        {"email": user_a.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_only_admin_can_create_managed_users(api_client, admin_user, staff_user):
    api_client.force_authenticate(user=staff_user)
    forbidden = api_client.post(
        reverse("managed-user-list"),
        {
            "email": "new@example.com",
            "password": "ValidPassword123!",
            "role": Role.CUSTOMER,
        },
        format="json",
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(user=admin_user)
    created = api_client.post(
        reverse("managed-user-list"),
        {
            "email": "new@example.com",
            "password": "ValidPassword123!",
            "role": Role.STAFF,
        },
        format="json",
    )

    assert created.status_code == 201
    new_user = User.objects.get(email="new@example.com")
    assert new_user.role == Role.STAFF
    assert new_user.is_staff is True
    assert new_user.check_password("ValidPassword123!")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password",
    ["shortA!", "alllowercase1!", "ALLUPPERCASE1!", "NoSpecial123"],
)
def test_password_policy_is_enforced(api_client, admin_user, password):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        reverse("managed-user-list"),
        {"email": "invalid@example.com", "password": password, "role": Role.CUSTOMER},
        format="json",
    )

    assert response.status_code == 400
    assert "password" in response.data


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
        reverse("password-reset"),
        {"email": user_a.email},
        format="json",
    )
    assert request_response.status_code == 200
    assert len(mail.outbox) == 1

    message = mail.outbox[0].body
    uid = re.search(r"uid=([^ ]+)", message).group(1)
    token = re.search(r"token=([^ ]+)", message).group(1)
    payload = {
        "uid": uid,
        "token": token,
        "new_password": "NewPassword123!",
    }

    first_reset = api_client.post(
        reverse("password-reset-confirm"), payload, format="json"
    )
    second_reset = api_client.post(
        reverse("password-reset-confirm"), payload, format="json"
    )

    assert first_reset.status_code == 200
    assert second_reset.status_code == 400
    user_a.refresh_from_db()
    assert user_a.check_password("NewPassword123!")
