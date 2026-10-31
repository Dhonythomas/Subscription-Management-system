import pytest

from apps.accounts.models import Role, User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="actor@example.com",
        password="Secret123!",
        role=Role.ADMIN,
    )
