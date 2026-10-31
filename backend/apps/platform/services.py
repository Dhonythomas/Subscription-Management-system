from django.db import transaction
from django.db.transaction import TransactionManagementError

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
