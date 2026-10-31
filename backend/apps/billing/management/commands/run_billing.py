from datetime import date

from django.core.management.base import BaseCommand

from apps.billing.services import run_billing


class Command(BaseCommand):
    help = "Generate invoices for active subscriptions due on or before a date."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=date.fromisoformat, default=None)

    def handle(self, *args, **options):
        count = run_billing(billing_date=options["date"])
        self.stdout.write(self.style.SUCCESS(f"Generated {count} invoices"))
