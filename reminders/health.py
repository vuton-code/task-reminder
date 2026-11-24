from django.db.models import Count
from django.utils import timezone
from .models import WorkerHeartbeat, OutboundMessage, DeliveryEvent

def snapshot():
    now=timezone.now()
    heartbeat=WorkerHeartbeat.objects.filter(name="reminders").first()
    pending=OutboundMessage.objects.filter(state__in=["pending","retry","unknown","dispatching"]).order_by("next_attempt_at").first()
    heartbeat_age=(now-heartbeat.seen_at).total_seconds() if heartbeat else None
    backlog_age=max(0,(now-pending.next_attempt_at).total_seconds()) if pending else 0
    counts=dict(OutboundMessage.objects.values("state").annotate(count=Count("pk")).values_list("state","count"))
    samples=OutboundMessage.objects.filter(state="accepted",occurrence__isnull=False,accepted_at__isnull=False).select_related("occurrence").order_by("-accepted_at")[:100]
    latencies=[(m.accepted_at-m.occurrence.due_at).total_seconds() for m in samples]
    return {"healthy":heartbeat_age is not None and heartbeat_age<=15 and backlog_age<=30,
        "heartbeat_age_seconds":heartbeat_age,"oldest_due_seconds":backlog_age,
        "pending":counts.get("pending",0)+counts.get("retry",0),"unknown":counts.get("unknown",0),
        "held":counts.get("held",0),"rejected":counts.get("rejected",0),
        "later_failures":DeliveryEvent.objects.filter(event_type__in=["email.bounced","email.failed","email.suppressed","email.complained"]).count(),
        "acceptance_samples":len(latencies),"max_acceptance_delay_seconds":max(latencies) if latencies else None}
