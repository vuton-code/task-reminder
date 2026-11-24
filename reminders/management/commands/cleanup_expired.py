from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from django.contrib.sessions.models import Session
from accounts.models import GoogleFlow
from projects.models import MutationReceipt
from reminders.models import OutboundMessage

class Command(BaseCommand):
    help="Remove transient secrets while preserving acceptance and idempotency evidence."
    def handle(self,*args,**kwargs):
        now=timezone.now()
        Session.objects.filter(expire_date__lte=now).delete()
        GoogleFlow.objects.filter(expires_at__lte=now).delete()
        MutationReceipt.objects.filter(created_at__lt=now-timedelta(days=30)).delete()
        # Expired/consumed proof tokens must not survive inside encrypted outbound payloads.
        expired=OutboundMessage.objects.filter(Q(proof__expires_at__lte=now)|Q(proof__consumed_at__isnull=False))
        expired.filter(state__in=["pending","retry"]).update(state="suppressed")
        expired.update(encrypted_payload="")
        OutboundMessage.objects.filter(state__in=["accepted","rejected","suppressed"],
            created_at__lt=now-timedelta(days=7)).update(encrypted_payload="")
        self.stdout.write("Expired sessions/flows and transient payloads cleaned; delivery identities retained.")
