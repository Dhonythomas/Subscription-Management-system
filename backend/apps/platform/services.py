from django.db import transaction
from django.db.transaction import TransactionManagementError

from apps.platform.exceptions import InvalidTransition
from apps.platform.models import AuditLog, OutboxEvent


def ensure_atomic_block():
    if not transaction.get_connection().in_atomic_block:
        raise TransactionManagementError(
            "Audit and outbox writes require an active transaction.atomic() block."
        )


def record_audit(
    *,
    entity_type,
    entity_id,
    from_status,
    to_status,
    actor=None,
    metadata=None,
):
    ensure_atomic_block()
    return AuditLog.objects.create(
        entity_type=entity_type,
        entity_id=str(entity_id),
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        metadata=metadata or {},
    )


def emit_event(
    *,
    event_type,
    aggregate_type,
    aggregate_id,
    payload=None,
):
    ensure_atomic_block()
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=payload or {},
    )


def apply_transition(
    instance,
    *,
    to_status: str,
    allowed_transitions,
    actor=None,
    event_type: str,
    validate=None,
    metadata=None,
    extra_update_fields=None,
):
    ensure_atomic_block()
    model_cls = instance.__class__
    locked = model_cls.objects.select_for_update().get(pk=instance.pk)
    from_status = locked.status
    allowed = allowed_transitions.get(from_status, set())
    if to_status not in allowed:
        raise InvalidTransition(
            f"Cannot transition {model_cls.__name__} from {from_status} to {to_status}"
        )
    if validate is not None:
        validate(locked)
    update_fields = ["status"]
    locked.status = to_status
    if extra_update_fields:
        for field, value in extra_update_fields.items():
            setattr(locked, field, value)
            update_fields.append(field)
    locked.save(update_fields=update_fields)
    record_audit(
        entity_type=f"{model_cls._meta.app_label}.{model_cls._meta.model_name}",
        entity_id=str(locked.pk),
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        metadata=metadata or {},
    )
    emit_event(
        event_type=event_type,
        aggregate_type=f"{model_cls._meta.app_label}.{model_cls._meta.model_name}",
        aggregate_id=str(locked.pk),
        payload={
            "aggregate_type": f"{model_cls._meta.app_label}.{model_cls._meta.model_name}",
            "aggregate_id": str(locked.pk),
            "from_status": from_status,
            "to_status": to_status,
            "actor_id": getattr(actor, "pk", None),
            "reason": (metadata or {}).get("reason"),
            "occurred_at": None,
        },
    )
    return locked
