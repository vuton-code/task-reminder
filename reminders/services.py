import uuid
import hashlib
import json
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from accounts.models import Account, AccountProof
from projects.models import Project, Invitation
from tasks.models import Task
from .models import OutboundMessage, EmailOccurrence, DeliveryAttempt, DeliveryEvent
from .providers import encrypt, decrypt, send, retrieve, SendResult

def enqueue(purpose, recipient, payload, **relations):
    encoded=json.dumps(payload,sort_keys=True)
    return OutboundMessage.objects.create(purpose=purpose,recipient=recipient,
        encrypted_payload=encrypt(payload),payload_digest=hashlib.sha256(encoded.encode()).hexdigest(),**relations)

def eligible(task):
    member=task.assignee
    return bool(task.status=="open" and task.reminder_at and task.reminder_at<=timezone.now()
        and member and member.left_at is None and member.project_id==task.project_id
        and member.account.is_active and member.account.email_enabled and member.account.email_verified_at)

def reminder_payload(task):
    context={"title":task.title,"task_url":f"{settings.APP_BASE_URL}/projects/{task.project_id}/tasks/{task.pk}"}
    return {"subject":"Task reminder","text":render_to_string("email/task_reminder.txt",context),
            "html":render_to_string("email/task_reminder.html",context)}

@transaction.atomic
def schedule_task(task_id):
    initial=Task.objects.filter(pk=task_id).first()
    if initial is None: return
    if not Project.objects.select_for_update().filter(pk=initial.project_id).exists(): return
    task=Task.objects.select_related("assignee__account").filter(pk=task_id).first()
    if task is None: return
    if not eligible(task): return
    occurrence,_=EmailOccurrence.objects.get_or_create(task=task,
        schedule_generation=task.schedule_generation,assignment_generation=task.assignment_generation,
        recipient=task.assignee,defaults={"due_at":task.reminder_at})
    payload=reminder_payload(task)
    message=OutboundMessage.objects.filter(occurrence=occurrence).first()
    if message is None:
        enqueue("reminder",task.assignee.account.email,payload,occurrence=occurrence)
    elif message.first_attempt_at is None and message.state in ["pending","suppressed"]:
        message.recipient=task.assignee.account.email
        message.encrypted_payload=encrypt(payload)
        message.payload_digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        message.state="pending"
        message.save()

def sweep():
    # Keyset iteration prevents an accepted prefix from starving later overdue tasks.
    cursor=None
    while True:
        query=Task.objects.filter(status="open",reminder_at__lte=timezone.now(),
            assignee__left_at__isnull=True,assignee__account__email_enabled=True,
            assignee__account__email_verified_at__isnull=False).order_by("pk")
        if cursor: query=query.filter(pk__gt=cursor)
        ids=list(query.values_list("pk",flat=True)[:250])
        if not ids: break
        for task_id in ids: schedule_task(task_id)
        cursor=ids[-1]

def invalidate(task):
    OutboundMessage.objects.filter(occurrence__task=task,state__in=["pending","prepared","retry"]).update(state="suppressed")

def mark_accepted(message, provider_id, stamp=None):
    message.state="accepted"
    message.provider_id=provider_id or message.provider_id
    message.accepted_at=stamp or message.accepted_at or timezone.now()
    if message.invitation_id:
        Invitation.objects.filter(pk=message.invitation_id,status="prepared").update(
            status="pending",sent_at=message.accepted_at,expires_at=message.accepted_at+timedelta(days=7))

def dispatch():
    now=timezone.now()
    with transaction.atomic():
        message=OutboundMessage.objects.select_for_update(skip_locked=True).filter(
            state__in=["pending","retry","unknown","dispatching","held"],next_attempt_at__lte=now
        ).filter(Q(lease_until__isnull=True)|Q(lease_until__lte=now)).order_by("next_attempt_at").first()
        if message is None: return False
        uncertain=message.state in ["unknown","dispatching","held"]
        expired=bool(message.first_attempt_at and now-message.first_attempt_at>=timedelta(hours=24))
        message.state="dispatching"
        message.lease_until=now+timedelta(seconds=30)
        message.lease_owner=uuid.uuid4()
        message.first_attempt_at=message.first_attempt_at or now
        message.attempts+=1
        message.save()
        attempt=DeliveryAttempt.objects.create(message=message)
    with transaction.atomic():
        current=OutboundMessage.objects.select_related("occurrence__task","invitation","proof").filter(pk=message.pk).first()
        if current is None: return True
        project_id=current.occurrence.task.project_id if current.occurrence_id else current.invitation.project_id if current.invitation_id else None
        if project_id and not Project.objects.select_for_update().filter(pk=project_id).exists(): return True
        if current.occurrence_id:
            task=Task.objects.select_related("assignee__account").get(pk=current.occurrence.task_id)
            if task.assignee_id:
                Account.objects.select_for_update().get(pk=task.assignee.account_id)
                task=Task.objects.select_related("assignee__account").get(pk=task.pk)
            valid=(eligible(task) and task.schedule_generation==current.occurrence.schedule_generation
                and task.assignment_generation==current.occurrence.assignment_generation
                and task.assignee_id==current.occurrence.recipient_id)
            if valid:
                valid=bool(current.encrypted_payload) and decrypt(current.encrypted_payload)==reminder_payload(task) and current.recipient==task.assignee.account.email
        elif current.proof_id:
            account=Account.objects.select_for_update().get(pk=current.proof.account_id)
            proof=AccountProof.objects.select_for_update().get(pk=current.proof_id)
            valid=(account.is_active and proof.consumed_at is None and proof.expires_at>timezone.now()
                and current.recipient==account.email and (proof.purpose!="reset" or account.has_usable_password()))
        else:
            valid=current.invitation.status in ["prepared","pending"] and (
                current.invitation.expires_at is None or current.invitation.expires_at>timezone.now())
        locked=OutboundMessage.objects.select_for_update().get(pk=current.pk)
        if locked.state=="accepted" or locked.lease_owner!=message.lease_owner: return True
        result=None
        if uncertain and locked.provider_id:
            event=DeliveryEvent.objects.filter(provider_id=locked.provider_id,event_type="email.sent").order_by("event_time").first()
            result=SendResult("accepted",locked.provider_id,accepted_at=event.event_time) if event else retrieve(locked.provider_id)
            # A retrieval consumes this iteration's network budget; never follow it with a send.
            if result.state!="accepted":
                result=SendResult("unknown",locked.provider_id)
        if result is None:
            if not valid or locked.reconciliation_only or expired:
                locked.reconciliation_only=uncertain or locked.reconciliation_only
                result=SendResult("held" if expired else "unknown" if locked.reconciliation_only else "suppressed")
            else:
                result=send(locked)
                locked.observed_at=timezone.now()
        locked.state=result.state
        locked.provider_id=result.provider_id or locked.provider_id
        locked.lease_until=None
        if not valid and uncertain: locked.reconciliation_only=True
        delay=max(result.retry_after_seconds,[2,5,10,20,60][min(locked.attempts-1,4)])
        if locked.reconciliation_only or expired: delay=max(60,delay)
        if expired and locked.state=="unknown": locked.state="held"
        locked.next_attempt_at=timezone.now()+timedelta(seconds=delay)
        if result.state=="accepted": mark_accepted(locked,result.provider_id,result.accepted_at)
        locked.save()
        attempt.result,attempt.finished_at,attempt.provider_status=locked.state,timezone.now(),result.status
        attempt.save()
    return True
