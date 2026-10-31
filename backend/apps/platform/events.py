from __future__ import annotations

import logging
from collections.abc import Callable

from django.db import transaction
from django.utils import timezone

from apps.platform.models import OutboxEvent

logger = logging.getLogger(__name__)

_HANDLERS: dict[str, list[Callable[[OutboxEvent], None]]] = {}


def register_handler(event_type: str, handler: Callable[[OutboxEvent], None]) -> None:
    _HANDLERS.setdefault(event_type, []).append(handler)


def clear_handlers() -> None:
    _HANDLERS.clear()


def dispatch_pending(limit: int = 100) -> int:
    with transaction.atomic():
        events = (
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(published_at__isnull=True)
            .order_by("created_at")[:limit]
        )
        processed = 0
        for event in events:
            handlers = _HANDLERS.get(event.event_type, [])
            event.attempts += 1
            if not handlers:
                logger.warning("No handler registered for outbox event %s (%s)", event.event_type, event.pk)
                event.published_at = timezone.now()
                event.last_error = ""
                event.save(update_fields=["attempts", "published_at", "last_error"])
                processed += 1
                continue
            try:
                for handler in handlers:
                    handler(event)
            except Exception as exc:
                event.last_error = str(exc)
                event.published_at = None
                event.save(update_fields=["attempts", "last_error", "published_at"])
                continue
            event.published_at = timezone.now()
            event.last_error = ""
            event.save(update_fields=["attempts", "published_at", "last_error"])
            processed += 1
    return processed
