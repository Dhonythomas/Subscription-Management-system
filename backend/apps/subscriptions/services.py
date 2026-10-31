from django.db import transaction

from apps.platform.exceptions import InvalidTransition
from apps.platform.services import apply_transition, emit_event, record_audit


def transition_subscription(subscription, to_status, *, actor=None, reason="", at_expiry=False):
    with transaction.atomic():
        sub = subscription.__class__.objects.select_for_update().get(pk=subscription.pk)
        plan = sub.plan

        def validate(locked):
            if to_status == locked.__class__.Status.PAUSED and not plan.pausable:
                raise InvalidTransition("Plan does not allow pausing")
            if to_status == locked.__class__.Status.CLOSED:
                if not (plan.closable or (at_expiry and plan.auto_close)):
                    raise InvalidTransition("Plan does not allow closing")
            if to_status == locked.__class__.Status.ACTIVE and locked.status == locked.__class__.Status.CLOSED:
                if not plan.renewable:
                    raise InvalidTransition("Plan does not allow renewal")
            if to_status == locked.__class__.Status.ACTIVE and locked.status == locked.__class__.Status.ACTIVE:
                if not plan.renewable:
                    raise InvalidTransition("Plan does not allow renewal")

        extra = {}
        if to_status == subscription.__class__.Status.ACTIVE and subscription.__class__.objects.get(pk=subscription.pk).status == subscription.__class__.Status.CONFIRMED:
            extra["next_billing_date"] = sub.start_date

        return apply_transition(
            subscription,
            to_status=to_status,
            allowed_transitions=subscription.__class__.ALLOWED_TRANSITIONS,
            actor=actor,
            event_type="subscription.status_changed",
            validate=validate,
            metadata={"reason": reason},
            extra_update_fields=extra or None,
        )
