import json
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import Account
from projects.services import create_project
from tasks.services import save_task
from reminders.services import sweep, dispatch
from reminders.models import OutboundMessage

class Command(BaseCommand):
    help = "Record controlled reminder acceptance observations."

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["fake","live"], default="fake")
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--recipient")
        parser.add_argument("--output", default="artifacts/reminder-results.json")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Run benchmarks in an isolated test environment.")
        if not 1 <= options["count"] <= 1000:
            raise CommandError("Count must be between 1 and 1000.")
        if options["mode"] != settings.EMAIL_BACKEND_MODE and not (options["mode"] == "live" and settings.EMAIL_BACKEND_MODE == "resend"):
            raise CommandError("Configure the matching email backend first.")
        email = options["recipient"] or "benchmark@example.test"
        if options["mode"] == "live":
            allowed = getattr(settings, "BENCHMARK_RECIPIENTS", [])
            if email not in allowed:
                raise CommandError("Recipient must be in BENCHMARK_RECIPIENTS.")
        stamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
        user = Account(username="benchmark_"+stamp, email=email if options["mode"] == "live" else f"{stamp}@example.test",
            email_verified_at=timezone.now(), email_enabled=True)
        user.set_unusable_password()
        user.save()
        project = create_project(user, "Reminder benchmark "+stamp)
        for number in range(options["count"]):
            save_task(user, project, {"title":f"Controlled test {number+1}", "reminder_at":timezone.now()+timedelta(seconds=2)})
        import time
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            sweep()
            for _ in range(options["count"]):
                if not dispatch():
                    break
            messages = OutboundMessage.objects.filter(occurrence__task__project=project)
            if messages.count() == options["count"] and not messages.exclude(state__in=["accepted","rejected","held"]).exists():
                break
            time.sleep(1)
        samples = []
        for message in OutboundMessage.objects.filter(occurrence__task__project=project).select_related("occurrence"):
            delay = (message.accepted_at-message.occurrence.due_at).total_seconds() if message.accepted_at else None
            samples.append({"state":message.state, "due_at":message.occurrence.due_at.isoformat(),
                "accepted_at":message.accepted_at.isoformat() if message.accepted_at else None,
                "delay_seconds":delay, "passes":delay is not None and 0 <= delay <= 60})
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"mode":options["mode"], "expected":options["count"], "samples":samples,
            "passing":sum(sample["passes"] for sample in samples), "live_verified":options["mode"]=="live"}, indent=2))
        self.stdout.write(f"Recorded {len(samples)} samples in {output}")
