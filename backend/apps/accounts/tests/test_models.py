import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.models import Customer, Role

User = get_user_model()


@pytest.mark.django_db
def test_create_user_hashes_password_and_defaults_to_customer():
    user = User.objects.create_user(email="person@example.com", password="Secret123!")
    assert user.role == Role.CUSTOMER
    assert user.check_password("Secret123!")
    assert user.password != "Secret123!"


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(email="same@example.com", password="Secret123!")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="same@example.com", password="Secret123!")


@pytest.mark.django_db
def test_customer_links_to_user():
    user = User.objects.create_user(email="customer@example.com", password="Secret123!")
    customer = Customer.objects.create(user=user, name="Acme Ltd")
    assert customer.user == user
    assert str(customer) == "Acme Ltd"
