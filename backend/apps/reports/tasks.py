from celery import shared_task

from apps.reports.services import refresh_daily_metrics


@shared_task
def refresh_daily_metrics_task():
    metrics = refresh_daily_metrics()
    return metrics.date.isoformat()
