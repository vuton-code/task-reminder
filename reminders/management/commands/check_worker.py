import json
from django.core.management.base import BaseCommand, CommandError
from reminders.health import snapshot

class Command(BaseCommand):
    help = "Report worker health without private task content."

    def handle(self, *args, **kwargs):
        result = snapshot()
        self.stdout.write(json.dumps(result))
        if not result["healthy"]:
            raise CommandError("Worker heartbeat or backlog is outside the expected window.")
