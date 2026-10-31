from django.db import transaction

from apps.platform.exceptions import InvalidTransition
from apps.platform.services import apply_transition


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
