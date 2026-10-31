import calendar
import logging
import re
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.models import Invoice, InvoiceLine
from apps.platform.exceptions import InvalidTransition
from apps.platform.money import quantize_money
from apps.platform.services import apply_transition, emit_event
from apps.subscriptions.models import Subscription

logger = logging.getLogger(__name__)


def transition_invoice(invoice, to_status, *, actor=None, reason=""):
    """Transition an invoice using the allowed-transitions map.

    Payment preconditions for moving to Paid and the \"no payments recorded\"
    precondition for Cancelled are enforced in later phases.
    """
    with transaction.atomic():
        return apply_transition(
            invoice,
            to_status=to_status,
            allowed_transitions=invoice.__class__.ALLOWED_TRANSITIONS,
            actor=actor,
            event_type="invoice.status_changed",
            metadata={"reason": reason},
        )


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _period_end(period_start, period):
    if period == "daily":
        return period_start
    if period == "weekly":
        return period_start + timedelta(days=6)
    if period == "monthly":
        return _add_months(period_start, 1) - timedelta(days=1)
    return _add_months(period_start, 12) - timedelta(days=1)


def _payment_term_days(payment_terms):
    # shortcut: first number in payment terms; replace with structured terms when billing rules expand.
    match = re.search(r"\d+", payment_terms or "")
    return int(match.group(0)) if match else 30


def _invoice_line_description(subscription_line):
    product = subscription_line.product.name
    variant = subscription_line.variant
    description = product if variant is None else f"{product} ({variant.attribute}: {variant.value})"
    return description[:255]


def generate_invoice_for_subscription(subscription_id, billing_date=None):
    billing_date = billing_date or timezone.localdate()
    with transaction.atomic():
        subscription = (
            Subscription.objects.select_for_update()
            .select_related("plan", "customer")
            .get(pk=subscription_id)
        )
        if (
            subscription.status != Subscription.Status.ACTIVE
            or subscription.next_billing_date is None
            or subscription.next_billing_date > billing_date
        ):
            return None

        subscription_lines = list(
            subscription.lines.select_related("product", "variant", "tax")
        )
        if not subscription_lines:
            raise ValueError(f"Subscription {subscription.pk} has no lines to bill.")

        period_start = subscription.next_billing_date
        period_end = _period_end(period_start, subscription.plan.period)
        due_date = period_end + timedelta(days=_payment_term_days(subscription.payment_terms))

        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        line_rows = []
        for subscription_line in subscription_lines:
            tax_rate = (
                subscription_line.tax.rate
                if subscription_line.tax is not None
                else Decimal("0.00")
            )
            line_amount = quantize_money(subscription_line.amount)
            line_tax = quantize_money(line_amount * tax_rate / Decimal("100"))
            subtotal += line_amount
            tax_total += line_tax
            line_rows.append(
                InvoiceLine(
                    description=_invoice_line_description(subscription_line),
                    quantity=subscription_line.qty,
                    unit_price=subscription_line.unit_price,
                    tax_rate=tax_rate,
                    discount=Decimal("0.00"),
                    amount=line_amount,
                )
            )

        subtotal = quantize_money(subtotal)
        tax_total = quantize_money(tax_total)
        invoice = Invoice.objects.create(
            number=f"INV-{subscription.pk}-{period_start:%Y%m%d}",
            subscription=subscription,
            customer=subscription.customer,
            period_start=period_start,
            period_end=period_end,
            subtotal=subtotal,
            tax=tax_total,
            discount=Decimal("0.00"),
            total=quantize_money(subtotal + tax_total),
            due_date=due_date,
        )
        for line in line_rows:
            line.invoice = invoice
        InvoiceLine.objects.bulk_create(line_rows)

        subscription.next_billing_date = period_end + timedelta(days=1)
        subscription.save(update_fields=["next_billing_date", "updated_at"])

        emit_event(
            event_type="invoice.created",
            aggregate_type="billing.invoice",
            aggregate_id=str(invoice.pk),
            payload={
                "invoice_id": invoice.pk,
                "number": invoice.number,
                "subscription_id": subscription.pk,
                "total": str(invoice.total),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "due_date": due_date.isoformat(),
            },
        )
        return invoice


def run_billing(billing_date=None, limit=100):
    billing_date = billing_date or timezone.localdate()
    subscription_ids = list(
        Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            next_billing_date__lte=billing_date,
        )
        .order_by("next_billing_date", "id")
        .values_list("id", flat=True)[:limit]
    )
    created = 0
    for subscription_id in subscription_ids:
        try:
            if generate_invoice_for_subscription(subscription_id, billing_date):
                created += 1
        except Exception:
            logger.exception("Billing failed for subscription %s", subscription_id)
    return created
