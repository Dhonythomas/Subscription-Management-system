import pytest
from django.db import transaction
from django.utils import timezone

from apps.platform import events
from apps.platform.events import clear_handlers, dispatch_pending, register_handler
from apps.platform.models import OutboxEvent


@pytest.fixture(autouse=True)
def _clear_handlers():
    clear_handlers()
    yield
    clear_handlers()


@pytest.mark.django_db
def test_dispatch_publishes_event_and_marks_published():
    received = []

    def handler(event):
        received.append(event.pk)

    register_handler("test.event", handler)
    with transaction.atomic():
        event = OutboxEvent.objects.create(
            event_type="test.event",
            aggregate_type="test.entity",
            aggregate_id="1",
            payload={},
        )

    count = dispatch_pending()
    event.refresh_from_db()

    assert count == 1
    assert received == [event.pk]
    assert event.published_at is not None
    assert event.attempts == 1
    assert event.last_error == ""


@pytest.mark.django_db
def test_dispatch_records_failure_and_can_retry():
    calls = []

    def failing_handler(event):
        calls.append("fail")
        raise ValueError("boom")

    def success_handler(event):
        calls.append("ok")

    register_handler("test.event", failing_handler)
    with transaction.atomic():
        event = OutboxEvent.objects.create(
            event_type="test.event",
            aggregate_type="test.entity",
            aggregate_id="1",
            payload={},
        )

    count = dispatch_pending()
    event.refresh_from_db()

    assert count == 0
    assert event.published_at is None
    assert event.attempts == 1
    assert "boom" in event.last_error
    assert calls == ["fail"]

    clear_handlers()
    register_handler("test.event", success_handler)
    count = dispatch_pending()
    event.refresh_from_db()

    assert count == 1
    assert event.published_at is not None
    assert event.attempts == 2
    assert event.last_error == ""
    assert calls == ["fail", "ok"]


@pytest.mark.django_db
def test_dispatch_marks_unhandled_events_published_with_warning(caplog):
    with transaction.atomic():
        event = OutboxEvent.objects.create(
            event_type="unknown.event",
            aggregate_type="test.entity",
            aggregate_id="1",
            payload={},
        )

    with caplog.at_level("WARNING"):
        count = dispatch_pending()

    event.refresh_from_db()

    assert count == 1
    assert event.published_at is not None
    assert event.attempts == 1
    assert "No handler registered" in caplog.text


@pytest.mark.django_db
def test_dispatch_only_publishes_unpublished_events():
    seen = []

    def handler(event):
        seen.append(event.pk)

    register_handler("test.event", handler)
    with transaction.atomic():
        published = OutboxEvent.objects.create(
            event_type="test.event",
            aggregate_type="test.entity",
            aggregate_id="1",
            payload={},
            published_at=timezone.now(),
            attempts=1,
        )
        unpublished = OutboxEvent.objects.create(
            event_type="test.event",
            aggregate_type="test.entity",
            aggregate_id="2",
            payload={},
        )

    count = dispatch_pending()
    published.refresh_from_db()
    unpublished.refresh_from_db()

    assert count == 1
    assert seen == [unpublished.pk]
    assert published.published_at is not None
    assert unpublished.published_at is not None
    assert unpublished.attempts == 1
