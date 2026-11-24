import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from reminders.services import sweep, dispatch
from reminders.models import WorkerHeartbeat

class Command(BaseCommand):
    help = "Run the durable reminder worker."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            WorkerHeartbeat.objects.update_or_create(name="reminders", defaults={"seen_at": timezone.now()})
            sweep()
            for _ in range(100):
                WorkerHeartbeat.objects.update_or_create(name="reminders", defaults={"seen_at": timezone.now()})
                if not dispatch():
                    break
            if options["once"]:
                return
            time.sleep(1)
