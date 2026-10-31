from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils.http import urlencode
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
def create_staff_account(*, email, password):
    return User.objects.create_user(
        email=email,
        password=password,
        role=Role.STAFF,
        is_staff=True,
    )


@transaction.atomic
def update_customer_profile(*, customer, **fields):
    for field, value in fields.items():
        setattr(customer, field, value)
    customer.save(update_fields=[*fields, "updated_at"])
    return customer


def send_password_reset(*, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = (
        f"{settings.PASSWORD_RESET_FRONTEND_URL}?"
        f"{urlencode({'uidb64': uid, 'token': token})}"
    )
    send_mail(
        "Password reset",
        f"Reset your password using this single-use link:\n\n{reset_url}",
        None,
        [user.email],
        fail_silently=False,
    )
