import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Customer, Role, User
from apps.billing.models import Invoice
from apps.billing.services import run_billing, transition_invoice
from apps.catalog.models import Product, Tax, Variant
from apps.discounts.models import Discount
from apps.payments.models import Payment
from apps.payments.services import record_payment
from apps.plans.models import Plan
from apps.reports.services import refresh_daily_metrics
from apps.subscriptions.models import QuotationTemplate, Subscription, SubscriptionLine
from apps.subscriptions.services import transition_subscription


class Command(BaseCommand):
    help = "Create or refresh a complete demo dataset."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "DemoPassword123!")
        today = timezone.localdate()

        admin, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={"role": Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(password)
            admin.save(update_fields=["password"])
        staff, created = User.objects.get_or_create(
            email="staff@example.com",
            defaults={"role": Role.STAFF, "is_staff": True},
        )
        if created:
            staff.set_password(password)
            staff.save(update_fields=["password"])
        customer_user, created = User.objects.get_or_create(
            email="customer@example.com", defaults={"role": Role.CUSTOMER}
        )
        if created:
            customer_user.set_password(password)
            customer_user.save(update_fields=["password"])
        customer, _ = Customer.objects.get_or_create(
            user=customer_user,
            defaults={
                "name": "Brightloop Demo Customer",
                "billing_email": "billing@example.com",
                "billing_address": "1 Demo Street",
            },
        )

        product, _ = Product.objects.get_or_create(
            name="Brightloop Platform",
            defaults={
                "type": Product.Type.SERVICE,
                "sales_price": Decimal("500.00"),
                "cost_price": Decimal("150.00"),
                "notes": "Demo product",
            },
        )
        Variant.objects.get_or_create(
            product=product,
            attribute="edition",
            value="Pro",
            defaults={"price_delta": Decimal("100.00")},
        )
        tax, _ = Tax.objects.get_or_create(
            name="VAT", defaults={"rate": Decimal("18.00")}
        )
        plan, _ = Plan.objects.get_or_create(
            product=product,
            period=Plan.Period.MONTHLY,
            defaults={
                "price": Decimal("500.00"),
                "start_date": today,
                "pausable": True,
                "closable": True,
                "renewable": True,
                "auto_close": True,
            },
        )
        QuotationTemplate.objects.get_or_create(
            name="Standard Quote",
            defaults={"plan": plan, "validity_days": 30},
        )
        Discount.objects.get_or_create(
            name="Launch 10%",
            defaults={
                "type": Discount.Type.PERCENT,
                "value": Decimal("10.00"),
                "scope": Discount.Scope.SUBSCRIPTION,
                "start_date": today,
                "end_date": today + timedelta(days=365),
                "usage_limit": 100,
            },
        )

        subscription, created = Subscription.objects.get_or_create(
            number="SUB-DEMO-001",
            defaults={
                "customer": customer,
                "plan": plan,
                "start_date": today,
                "expiry_date": today + timedelta(days=365),
                "payment_terms": "Net 30",
            },
        )
        if created:
            SubscriptionLine.objects.create(
                subscription=subscription,
                product=product,
                tax=tax,
                qty=Decimal("1.00"),
                unit_price=plan.price,
                amount=plan.price,
            )
            subscription = transition_subscription(
                subscription, Subscription.Status.QUOTATION, actor=admin
            )
            subscription = transition_subscription(
                subscription, Subscription.Status.CONFIRMED, actor=admin
            )
            subscription = transition_subscription(
                subscription, Subscription.Status.ACTIVE, actor=admin
            )
            subscription.next_billing_date = today
            subscription.save(update_fields=["next_billing_date"])
        elif subscription.status != Subscription.Status.ACTIVE:
            for status in (
                Subscription.Status.QUOTATION,
                Subscription.Status.CONFIRMED,
                Subscription.Status.ACTIVE,
            ):
                if subscription.status != status:
                    subscription = transition_subscription(
                        subscription, status, actor=admin
                    )

        invoice = Invoice.objects.filter(subscription=subscription).order_by("id").first()
        if invoice is None:
            subscription.next_billing_date = today
            subscription.save(update_fields=["next_billing_date"])
            run_billing(today)
            invoice = (
                Invoice.objects.filter(subscription=subscription).order_by("id").first()
            )

        if invoice is not None:
            if invoice.status == Invoice.Status.DRAFT:
                invoice = transition_invoice(
                    invoice, Invoice.Status.CONFIRMED, actor=staff
                )
            if invoice.status == Invoice.Status.CONFIRMED:
                paid = (
                    Payment.objects.filter(invoice=invoice).aggregate(
                        total=Sum("amount")
                    )["total"]
                    or Decimal("0.00")
                )
                remaining = invoice.total - paid
                if remaining > 0:
                    record_payment(
                        invoice=invoice,
                        method=Payment.Method.BANK,
                        amount=remaining,
                        paid_on=today,
                        note="Demo payment",
                        actor=staff,
                    )

        refresh_daily_metrics(today)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready. Login: admin@example.com / staff@example.com / "
                f"customer@example.com. Password: {password}"
            )
        )
