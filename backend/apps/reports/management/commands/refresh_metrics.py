from django.core.management.base import BaseCommand

from apps.reports.services import refresh_daily_metrics


class Command(BaseCommand):
    help = "Refresh the daily finance metrics read model."

    def handle(self, *args, **options):
        metrics = refresh_daily_metrics()
        self.stdout.write(self.style.SUCCESS(f"Refreshed metrics for {metrics.date}"))
