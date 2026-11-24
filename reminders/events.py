"""Apply signed provider evidence without reversing later business changes."""
import uuid
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from projects.models import Project, Invitation
from .models import OutboundMessage, DeliveryEvent
from .services import mark_accepted

@transaction.atomic
def record_event(event_id,data):
    body=data.get("data",{})
    if not isinstance(body,dict) or not event_id or not body.get("email_id") or not data.get("type"):
        raise ValueError("Missing event identifiers")
    provider_id=body["email_id"]
    if not isinstance(provider_id,str) or len(provider_id)>200 or len(event_id)>200:
        raise ValueError("Invalid identifiers")
    stamp=parse_datetime(data.get("created_at",""))
    if stamp is None or timezone.is_naive(stamp):
        raise ValueError("Invalid event timestamp")
    tags=body.get("tags",{})
    if isinstance(tags,list):
        tags={item.get("name"):item.get("value") for item in tags if isinstance(item,dict)}
    message_id=tags.get("message_id") if isinstance(tags,dict) else None
    if message_id:
        try: message_id=uuid.UUID(message_id)
        except (ValueError,TypeError,AttributeError): raise ValueError("Invalid correlation")
    _,created=DeliveryEvent.objects.get_or_create(event_id=event_id,defaults={
        "provider_id":provider_id,"event_type":data["type"],"event_time":stamp})
    if not created: return
    query=OutboundMessage.objects.filter(pk=message_id) if message_id else OutboundMessage.objects.filter(provider_id=provider_id)
    current=query.select_related("invitation","occurrence__task").first()
    if not current: return  # Event remains available for later read-only reconciliation.
    project_id=current.invitation.project_id if current.invitation_id else current.occurrence.task.project_id if current.occurrence_id else None
    if project_id: Project.objects.select_for_update().get(pk=project_id)
    message=OutboundMessage.objects.select_for_update().get(pk=current.pk)
    if message.provider_id and message.provider_id!=provider_id:
        return
    message.provider_id=provider_id
    if data["type"]=="email.sent":
        mark_accepted(message,provider_id,stamp)
        message.lease_until=None
    message.save()
