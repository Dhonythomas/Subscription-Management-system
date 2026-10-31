from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.accounts.models import Customer, Role

User = get_user_model()


@transaction.atomic
def create_customer_account(
    *, email, password, name, billing_address="", billing_phone="", billing_email=""
):
    user = User.objects.create_user(
        email=email,
        password=password,
        role=Role.CUSTOMER,
    )
    Customer.objects.create(
        user=user,
        name=name,
        billing_email=billing_email,
        billing_address=billing_address,
        billing_phone=billing_phone,
    )
    return user


@transaction.atomic
def create_managed_user(*, email, password, role, is_active=True):
    is_staff = role == Role.STAFF
    return User.objects.create_user(
        email=email,
        password=password,
        role=role,
        is_staff=is_staff,
        is_active=is_active,
    )


def send_password_reset(*, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    send_mail(
        "Password reset",
        f"Use uid={uid} and token={token} to reset your password.",
        None,
        [user.email],
        fail_silently=False,
    )
