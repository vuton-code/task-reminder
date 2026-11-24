import json
import uuid
import base64
from datetime import timedelta
from unittest.mock import patch
import pytest
import time_machine
from svix.webhooks import Webhook
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import RequestFactory
from accounts.models import Account, AccountProof, RateBucket
from accounts.services import register, consume_proof
from accounts.rate_limits import failed, wait_seconds
from projects.services import create_project
from projects.invitations import invite, accept, cancel
from projects.models import Invitation
from reminders.services import dispatch, sweep
from reminders.models import OutboundMessage, DeliveryEvent
from reminders.providers import decrypt
from tasks.services import save_task
from tasks.forms import TaskForm

pytestmark = pytest.mark.django_db

def owner_project():
    owner = Account.objects.create_user(username="owner", email="owner@example.test", email_verified_at=timezone.now(), email_enabled=True)
    return owner, create_project(owner, "Project")

def test_registration_and_verification():
    user = register("newuser", "new@example.test", "a-long-unique-password-952")
    assert user.email_verified_at is None
    token = decrypt(OutboundMessage.objects.get().encrypted_payload)["text"].rsplit("/",1)[-1]
    consume_proof(token, "verify")
    user.refresh_from_db()
    assert user.email_verified_at
    with pytest.raises(ValidationError):
        consume_proof(token, "verify")

@pytest.mark.parametrize("state", ["cancelled","expired","unverified"])
def test_invitation_lifecycle_rejections(state):
    owner, project = owner_project()
    invitation = invite(owner, project, "member@example.test")
    token = decrypt(OutboundMessage.objects.get().encrypted_payload)["text"].rsplit("/",1)[-1]
    dispatch()
    member = Account.objects.create_user(username="member",email="member@example.test",
        email_verified_at=None if state=="unverified" else timezone.now())
    if state=="cancelled":
        cancel(owner, invitation)
    if state=="expired":
        Invitation.objects.filter(pk=invitation.pk).update(expires_at=timezone.now())
    with pytest.raises((ValidationError, PermissionDenied)):
        accept(member, token)

def test_source_limit_and_exact_account_delay():
    request = RequestFactory().post("/", REMOTE_ADDR="192.0.2.8")
    with time_machine.travel("2026-11-14T10:00:00Z", tick=False) as clock:
        for _ in range(6):
            failed(request,"person")
        assert wait_seconds(request,"person")==31
        clock.shift(timedelta(seconds=30))
        assert wait_seconds(request,"person")==0
        for number in range(50):
            failed(request,f"distributed-{number}")
        assert wait_seconds(request,"another")>0

def test_same_creation_key_reuses_task():
    owner, project = owner_project()
    key=uuid.uuid4()
    task=save_task(owner,project,{"title":"Saved"},key=key)
    assert save_task(owner,project,{"title":"Saved"},key=key).pk==task.pk
    with pytest.raises(ValidationError):
        save_task(owner,project,{"title":"Other"},key=key)

def test_dst_gap_and_ambiguous_time():
    owner,project=owner_project()
    base={"title":"Timed", "timezone":"America/Los_Angeles"}
    gap=TaskForm({**base,"reminder_at":"2026-03-08T02:30"},project=project)
    assert not gap.is_valid()
    ambiguous=TaskForm({**base,"reminder_at":"2026-11-01T01:30"},project=project)
    assert not ambiguous.is_valid()
    explicit=TaskForm({**base,"reminder_at":"2026-11-01T01:30","fold":"1"},project=project)
    assert explicit.is_valid(), explicit.errors

def test_pending_title_edit_updates_email():
    owner,project=owner_project()
    task=save_task(owner,project,{"title":"Old","reminder_at":timezone.now()-timedelta(seconds=1)})
    sweep()
    save_task(owner,project,{"title":"Current"},task.pk,task.version)
    sweep()
    dispatch()
    message=OutboundMessage.objects.get()
    assert message.state=="accepted"
    assert "Current" in decrypt(message.encrypted_payload)["text"]

def test_webhook_signature_and_duplicate_receipt(client, settings):
    settings.RESEND_WEBHOOK_SECRET="whsec_"+base64.b64encode(b"a"*32).decode()
    stamp=timezone.now()
    body=json.dumps({"type":"email.bounced","created_at":stamp.isoformat(),"data":{"email_id":"provider-message"}})
    assert client.post("/webhooks/resend",body,content_type="application/json").status_code==400
    headers={"HTTP_SVIX_ID":"event-1","HTTP_SVIX_TIMESTAMP":str(int(stamp.timestamp())),
        "HTTP_SVIX_SIGNATURE":Webhook(settings.RESEND_WEBHOOK_SECRET).sign("event-1",stamp,body)}
    assert client.post("/webhooks/resend",body,content_type="application/json",**headers).status_code==200
    assert client.post("/webhooks/resend",body,content_type="application/json",**headers).status_code==200
    assert DeliveryEvent.objects.count()==1
