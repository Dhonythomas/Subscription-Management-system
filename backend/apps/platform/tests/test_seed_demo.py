import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import Customer, Role, User
from apps.billing.models import Invoice
from apps.catalog.models import Product
from apps.payments.models import Payment
from apps.plans.models import Plan
from apps.reports.models import DailyMetrics
from apps.subscriptions.models import Subscription


@pytest.mark.django_db
def test_seed_demo_creates_complete_idempotent_demo_data():
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    assert User.objects.filter(role=Role.ADMIN).count() == 1
    assert User.objects.filter(role=Role.STAFF).count() == 1
    assert User.objects.filter(role=Role.CUSTOMER).count() == 1
    assert Customer.objects.count() == 1
    assert Product.objects.count() == 1
    assert Plan.objects.count() == 1
    subscription = Subscription.objects.get(number="SUB-DEMO-001")
    assert subscription.status == Subscription.Status.ACTIVE
    invoice = Invoice.objects.get(subscription=subscription)
    assert invoice.status == Invoice.Status.PAID
    assert Payment.objects.filter(invoice=invoice).count() == 1
    assert DailyMetrics.objects.get(date=timezone.localdate()).revenue_collected > 0
