import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Customer, Role
from apps.catalog.models import Product, Tax
from apps.plans.models import Plan
from apps.platform.models import AuditLog, OutboxEvent
from apps.platform.services import apply_transition
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import transition_subscription

User = get_user_model()


@pytest.mark.django_db
def test_apply_transition_locks_checks_and_writes_audit_and_outbox(user):
    product = Product.objects.create(
        name="Platform",
        type=Product.Type.SERVICE,
        sales_price=Decimal("500.00"),
        cost_price=Decimal("150.00"),
    )
    plan = Plan.objects.create(
        product=product,
        price=Decimal("500.00"),
        period=Plan.Period.MONTHLY,
        start_date=timezone.now().date(),
    )
    user = User.objects.create_user(email="sub@example.com", password="Secret123!")
    customer = Customer.objects.create(user=user, name="Acme Ltd")
    subscription = Subscription.objects.create(
        number="SUB-001",
        customer=customer,
        plan=plan,
        start_date=timezone.now().date(),
        expiry_date=timezone.now().date(),
        payment_terms="Net 30",
        status=Subscription.Status.DRAFT,
    )

    updated = transition_subscription(subscription, Subscription.Status.QUOTATION, actor=user)
    assert updated.status == Subscription.Status.QUOTATION
    assert AuditLog.objects.filter(entity_type="subscriptions.subscription", entity_id=str(subscription.pk)).count() == 1
    assert OutboxEvent.objects.filter(event_type="subscription.status_changed").count() == 1
