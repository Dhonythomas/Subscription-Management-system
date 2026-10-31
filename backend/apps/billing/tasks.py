from celery import shared_task

from apps.billing.services import run_billing


@shared_task
def run_billing_task(limit=100):
    return run_billing(limit=limit)
