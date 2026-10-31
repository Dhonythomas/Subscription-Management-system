import pytest
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.accounts.models import Customer
from apps.catalog.models import Product, Tax
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="actor@example.com",
        password="Secret123!",
        role=Role.ADMIN,
    )


@pytest.fixture
def customer(db):
    user = User.objects.create_user(email="customer@example.com", password="Secret123!")
    return Customer.objects.create(user=user, name="Acme Ltd")


@pytest.fixture
def product(db):
    return Product.objects.create(
        name="Platform",
        type=Product.Type.SERVICE,
        sales_price=Decimal("500.00"),
        cost_price=Decimal("150.00"),
    )


@pytest.fixture
def tax(db):
    return Tax.objects.create(name="VAT", rate=Decimal("18.00"))


@pytest.fixture
def plan(db, product):
    return Plan.objects.create(
        product=product,
        price=Decimal("500.00"),
        period=Plan.Period.MONTHLY,
        start_date=timezone.now().date(),
        pausable=True,
        closable=True,
        renewable=True,
    )


@pytest.fixture
def subscription(db, customer, plan):
    return Subscription.objects.create(
        number="SUB-001",
        customer=customer,
        plan=plan,
        start_date=timezone.now().date(),
        expiry_date=timezone.now().date(),
        payment_terms="Net 30",
        status=Subscription.Status.DRAFT,
    )
