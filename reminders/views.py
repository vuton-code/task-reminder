from django.conf import settings
from zoneinfo import ZoneInfo
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from svix.webhooks import Webhook, WebhookVerificationError
from tasks.models import Task
from .models import OutboundMessage, DeliveryEvent
from .providers import decrypt

def due_items(user, offset=0):
    items = Task.objects.filter(status="open", reminder_at__lte=timezone.now(), assignee__account=user,
        assignee__left_at__isnull=True).select_related("assignee__account", "created_by").order_by("reminder_at", "id")[offset:offset+100]
    zone = ZoneInfo(user.display_timezone)
    def formatted(stamp):
        return stamp.astimezone(zone).strftime("%b %d, %Y · %I:%M %p %Z") if stamp else None
    return [{"occurrence_key": f"{t.pk}:{t.schedule_generation}:{t.assignment_generation}",
        "project_id": str(t.project_id), "task_id": str(t.pk), "title": t.title,
        "scheduled_at": t.reminder_at.isoformat(),
        "scheduled_label": formatted(t.reminder_at), "timezone": user.display_timezone,
        "assignee_name": t.assignee.account.display_name,
        "creator_name": t.created_by.display_name if t.created_by else None,
        "created_at": t.created_at.isoformat(), "created_label": formatted(t.created_at),
        "assigned_at": t.assigned_at.isoformat() if t.assigned_at else None,
        "assigned_label": formatted(t.assigned_at), "task_version": t.version,
        "task_url": f"/projects/{t.project_id}/tasks/{t.pk}"} for t in items]

def due(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in required"}, status=401)
    try:
        offset = max(0, int(request.GET.get("cursor", "0")))
    except ValueError:
        return JsonResponse({"error": "Invalid cursor"}, status=400)
    items = due_items(request.user, offset)
    return JsonResponse({"server_time": timezone.now().isoformat(), "items": items,
        "next_cursor": str(offset+100) if len(items) == 100 else None})

@login_required
def reminder_page(request):
    try:
        offset=max(0,int(request.GET.get("cursor","0")))
    except ValueError:
        raise Http404
    items=due_items(request.user,offset)
    return render(request,"reminders/list.html",{"due_items":items,"reminder_offset":offset,
        "next_reminders":offset+100 if len(items)==100 else None})

def outbox(request):
    if not settings.DEBUG or settings.EMAIL_BACKEND_MODE != "fake":
        raise Http404
    if request.META.get("REMOTE_ADDR") not in ["127.0.0.1", "::1"]:
        raise Http404
    messages = []
    for message in OutboundMessage.objects.order_by("-created_at")[:30]:
        if message.encrypted_payload:
            messages.append({"recipient": message.recipient, "state": message.state, **decrypt(message.encrypted_payload)})
    return render(request, "reminders/outbox.html", {"outbox_messages": messages})

@csrf_exempt
@require_POST
def webhook(request):
    try:
        data = Webhook(settings.RESEND_WEBHOOK_SECRET).verify(request.body, dict(request.headers))
    except (WebhookVerificationError, ValueError):
        return JsonResponse({"error": "Invalid signature"}, status=400)
    from .events import record_event
    try:
        record_event(request.headers.get("svix-id"), data)
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"error": "Invalid event"}, status=400)
    return JsonResponse({"received": True})
