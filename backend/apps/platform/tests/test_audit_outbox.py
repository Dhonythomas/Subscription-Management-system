import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.transaction import TransactionManagementError

from apps.platform.models import AuditLog, OutboxEvent
from apps.platform.services import emit_event, record_audit


@pytest.mark.django_db(transaction=True)
def test_record_audit_requires_an_atomic_block(user):
    with pytest.raises(TransactionManagementError):
        record_audit(
            entity_type="test.entity",
            entity_id="1",
            from_status="a",
            to_status="b",
            actor=user,
        )


@pytest.mark.django_db(transaction=True)
def test_emit_event_requires_an_atomic_block():
    with pytest.raises(TransactionManagementError):
        emit_event(
            event_type="test.event",
            aggregate_type="test.entity",
            aggregate_id="1",
        )


@pytest.mark.django_db
def test_audit_and_outbox_roll_back_together(user):
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            record_audit(
                entity_type="test.entity",
                entity_id="1",
                from_status="a",
                to_status="b",
                actor=user,
            )
            emit_event(
                event_type="test.event",
                aggregate_type="test.entity",
                aggregate_id="1",
            )
            raise RuntimeError("force rollback")

    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_audit_log_rejects_instance_update(user):
    with transaction.atomic():
        log = record_audit(
            entity_type="test.entity",
            entity_id="1",
            from_status="a",
            to_status="b",
            actor=user,
        )

    log.to_status = "c"
    with pytest.raises(ValidationError):
        log.save()


@pytest.mark.django_db
def test_audit_log_rejects_instance_delete(user):
    with transaction.atomic():
        log = record_audit(
            entity_type="test.entity",
            entity_id="1",
            from_status="a",
            to_status="b",
            actor=user,
        )

    with pytest.raises(ValidationError):
        log.delete()


@pytest.mark.django_db
def test_audit_log_rejects_queryset_update(user):
    with transaction.atomic():
        log = record_audit(
            entity_type="test.entity",
            entity_id="1",
            from_status="a",
            to_status="b",
            actor=user,
        )

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.filter(pk=log.pk).update(to_status="c")


@pytest.mark.django_db
def test_outbox_event_defaults():
    with transaction.atomic():
        event = emit_event(
            event_type="test.event",
            aggregate_type="test.entity",
            aggregate_id="1",
        )

    assert event.attempts == 0
    assert event.published_at is None
    assert event.last_error == ""
