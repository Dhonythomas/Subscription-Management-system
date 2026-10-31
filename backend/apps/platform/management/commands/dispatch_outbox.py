from django.core.management.base import BaseCommand

from apps.platform.events import dispatch_pending


class Command(BaseCommand):
    help = "Dispatch unpublished outbox events."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        count = dispatch_pending(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Dispatched {count} events"))
