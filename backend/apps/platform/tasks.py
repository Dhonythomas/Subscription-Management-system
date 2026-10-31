from celery import shared_task

from apps.platform.events import dispatch_pending


@shared_task
def dispatch_outbox_task(limit: int = 100) -> int:
    return dispatch_pending(limit=limit)
