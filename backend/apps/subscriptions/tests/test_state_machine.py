import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Customer
from apps.catalog.models import Product, Tax
from apps.plans.models import Plan
from apps.platform.exceptions import InvalidTransition
from apps.platform.models import AuditLog, OutboxEvent
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import transition_subscription
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def subscription(db):
    product = Product.objects.create(name="Platform", type=Product.Type.SERVICE, sales_price=Decimal("500.00"), cost_price=Decimal("150.00"))
    plan = Plan.objects.create(product=product, price=Decimal("500.00"), period=Plan.Period.MONTHLY, start_date=timezone.now().date(), pausable=True, closable=True, renewable=True, auto_close=False)
    user = User.objects.create_user(email="c@example.com", password="Secret123!")
    customer = Customer.objects.create(user=user, name="Acme")
    return Subscription.objects.create(number="SUB-001", customer=customer, plan=plan, start_date=timezone.now().date(), expiry_date=timezone.now().date(), payment_terms="Net 30", status=Subscription.Status.DRAFT)


@pytest.mark.django_db
def test_happy_path_and_audit(user, subscription):
    transition_subscription(subscription, Subscription.Status.QUOTATION, actor=user)
    transition_subscription(subscription, Subscription.Status.CONFIRMED, actor=user)
    updated = transition_subscription(subscription, Subscription.Status.ACTIVE, actor=user)
    assert updated.status == Subscription.Status.ACTIVE
    assert AuditLog.objects.filter(entity_type="subscriptions.subscription").count() == 3
    assert OutboxEvent.objects.filter(event_type="subscription.status_changed").count() == 3


@pytest.mark.django_db
def test_illegal_transition_rejected_and_writes_nothing(user, subscription):
    with pytest.raises(InvalidTransition):
        transition_subscription(subscription, Subscription.Status.ACTIVE, actor=user)
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_active_to_paused_requires_pausable(user, subscription):
    sub = subscription
    transition_subscription(sub, Subscription.Status.QUOTATION, actor=user)
    transition_subscription(sub, Subscription.Status.CONFIRMED, actor=user)
    transition_subscription(sub, Subscription.Status.ACTIVE, actor=user)
    sub.plan.pausable = False
    sub.plan.save()
    with pytest.raises(InvalidTransition):
        transition_subscription(sub, Subscription.Status.PAUSED, actor=user)


@pytest.mark.django_db
def test_active_to_closed_requires_closable_or_auto_close(user, subscription):
    sub = subscription
    transition_subscription(sub, Subscription.Status.QUOTATION, actor=user)
    transition_subscription(sub, Subscription.Status.CONFIRMED, actor=user)
    transition_subscription(sub, Subscription.Status.ACTIVE, actor=user)
    sub.plan.closable = False
    sub.plan.auto_close = False
    sub.plan.save()
    with pytest.raises(InvalidTransition):
        transition_subscription(sub, Subscription.Status.CLOSED, actor=user)

    sub.plan.auto_close = True
    sub.plan.save()
    transition_subscription(sub, Subscription.Status.CLOSED, actor=user, at_expiry=True)


@pytest.mark.django_db
def test_renewal_requires_renewable(user, subscription):
    sub = subscription
    transition_subscription(sub, Subscription.Status.QUOTATION, actor=user)
    transition_subscription(sub, Subscription.Status.CONFIRMED, actor=user)
    transition_subscription(sub, Subscription.Status.ACTIVE, actor=user)
    transition_subscription(sub, Subscription.Status.CLOSED, actor=user, at_expiry=True)
    sub.plan.renewable = False
    sub.plan.save()
    with pytest.raises(InvalidTransition):
        transition_subscription(sub, Subscription.Status.ACTIVE, actor=user)


@pytest.mark.django_db
def test_confirmed_to_active_sets_next_billing_date(user, subscription):
    sub = subscription
    sub.next_billing_date = None
    sub.save()
    transition_subscription(sub, Subscription.Status.QUOTATION, actor=user)
    transition_subscription(sub, Subscription.Status.CONFIRMED, actor=user)
    updated = transition_subscription(sub, Subscription.Status.ACTIVE, actor=user)
    assert updated.next_billing_date == sub.start_date


@pytest.mark.django_db
def test_stale_instance_rejected_by_lock(user, subscription):
    sub = subscription
    stale = Subscription.objects.get(pk=sub.pk)
    transition_subscription(sub, Subscription.Status.QUOTATION, actor=user)
    with pytest.raises(InvalidTransition):
        transition_subscription(stale, Subscription.Status.QUOTATION, actor=user)


@pytest.mark.django_db
def test_emit_event_failure_rolls_back(user, subscription, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("emit failed")

    monkeypatch.setattr("apps.platform.services.emit_event", boom)
    with pytest.raises(RuntimeError):
        transition_subscription(subscription, Subscription.Status.QUOTATION, actor=user)

    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.DRAFT
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0
