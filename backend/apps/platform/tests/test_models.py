from django.db import models

from apps.platform.models import AuditLog, OutboxEvent


def test_audit_log_field_metadata():
    entity_type = AuditLog._meta.get_field("entity_type")
    entity_id = AuditLog._meta.get_field("entity_id")
    from_status = AuditLog._meta.get_field("from_status")
    to_status = AuditLog._meta.get_field("to_status")
    metadata = AuditLog._meta.get_field("metadata")

    assert entity_type.max_length == 100
    assert entity_id.max_length == 64
    assert from_status.max_length == 32
    assert to_status.max_length == 32
    assert isinstance(metadata, models.JSONField)
    assert metadata.default is dict
    assert AuditLog._meta.db_table == "audit_log"


def test_audit_log_actor_is_nullable_and_set_null():
    actor = AuditLog._meta.get_field("actor")

    assert actor.null is True
    assert actor.remote_field.on_delete is models.SET_NULL


def test_audit_log_has_entity_index():
    indexes = {index.name: index.fields for index in AuditLog._meta.indexes}

    assert indexes["audit_entity_idx"] == ["entity_type", "entity_id"]


def test_outbox_event_field_metadata():
    event_type = OutboxEvent._meta.get_field("event_type")
    aggregate_type = OutboxEvent._meta.get_field("aggregate_type")
    aggregate_id = OutboxEvent._meta.get_field("aggregate_id")
    payload = OutboxEvent._meta.get_field("payload")
    published_at = OutboxEvent._meta.get_field("published_at")
    attempts = OutboxEvent._meta.get_field("attempts")

    assert event_type.max_length == 100
    assert aggregate_type.max_length == 100
    assert aggregate_id.max_length == 64
    assert isinstance(payload, models.JSONField)
    assert payload.default is dict
    assert published_at.null is True
    assert attempts.default == 0
    assert OutboxEvent._meta.db_table == "outbox_event"


def test_outbox_event_has_published_at_index():
    indexes = {index.name: index.fields for index in OutboxEvent._meta.indexes}

    assert indexes["outbox_published_idx"] == ["published_at"]
