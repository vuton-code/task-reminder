import base64
import json
from datetime import timedelta
import pytest
from django.test import RequestFactory
from django.utils import timezone
from django.core.management import call_command
from svix.webhooks import Webhook
from accounts.models import Account
from accounts.services import issue_proof
from projects.services import create_project
from tasks.services import save_task
from reminders.services import sweep, dispatch
from reminders.models import OutboundMessage, DeliveryEvent, WorkerHeartbeat
from reminders.providers import decrypt
from reminders.health import snapshot
from config.proxy import TrustedProxyMiddleware
pytestmark=pytest.mark.django_db

def message():
    a=Account.objects.create_user(username="a",email="a@example.test",email_verified_at=timezone.now(),email_enabled=True)
    p=create_project(a,"Secret project")
    t=save_task(a,p,{"title":"<script>Title</script>","description":"PRIVATE DESCRIPTION","reminder_at":timezone.now()-timedelta(seconds=1)})
    sweep()
    return a,p,t,OutboundMessage.objects.get()

def signed(client,settings,event_id,payload):
    settings.RESEND_WEBHOOK_SECRET="whsec_"+base64.b64encode(b"x"*32).decode()
    stamp=timezone.now(); body=json.dumps(payload)
    return client.post("/webhooks/resend",body,content_type="application/json",
        HTTP_SVIX_ID=event_id,HTTP_SVIX_TIMESTAMP=str(int(stamp.timestamp())),
        HTTP_SVIX_SIGNATURE=Webhook(settings.RESEND_WEBHOOK_SECRET).sign(event_id,stamp,body))

def test_email_content_private_and_escaped():
    a,p,t,m=message()
    data=decrypt(m.encrypted_payload)
    assert "PRIVATE DESCRIPTION" not in str(data) and "Secret project" not in str(data)
    assert "<script>" not in data["html"]
    assert "&lt;script&gt;" in data["html"]
    assert f"/projects/{p.pk}/tasks/{t.pk}" in data["text"]

def test_out_of_order_webhooks_preserve_acceptance_and_failures(client,settings):
    a,p,t,m=message()
    stamp=timezone.now()
    payload={"type":"email.bounced","created_at":stamp.isoformat(),"data":{"email_id":"provider","tags":[{"name":"message_id","value":str(m.pk)}]}}
    assert signed(client,settings,"bounce",payload).status_code==200
    payload["type"]="email.sent"
    payload["created_at"]=(stamp-timedelta(seconds=1)).isoformat()
    assert signed(client,settings,"sent",payload).status_code==200
    assert signed(client,settings,"sent",payload).status_code==200
    m.refresh_from_db()
    assert m.state=="accepted" and m.accepted_at<stamp
    assert DeliveryEvent.objects.count()==2
    assert snapshot()["later_failures"]==1

def test_invalid_signed_correlation_is_safe(client,settings):
    payload={"type":"email.sent","created_at":timezone.now().isoformat(),"data":{"email_id":"p","tags":{"message_id":"not-uuid"}}}
    assert signed(client,settings,"invalid",payload).status_code==400
    assert not DeliveryEvent.objects.exists()

def test_expired_token_payload_removed_delivery_identity_kept():
    a,p,t,m=message()
    dispatch()
    proof=issue_proof(a,"reset")
    proof.expires_at=timezone.now()-timedelta(seconds=1); proof.save()
    call_command("cleanup_expired")
    assert OutboundMessage.objects.get(proof=proof).encrypted_payload==""
    m.refresh_from_db()
    assert m.state=="accepted" and m.provider_id

def test_backlog_and_latency_metrics():
    a,p,t,m=message()
    WorkerHeartbeat.objects.create(name="reminders")
    OutboundMessage.objects.update(next_attempt_at=timezone.now()-timedelta(seconds=31))
    assert not snapshot()["healthy"]
    dispatch()
    result=snapshot()
    assert result["healthy"] and result["acceptance_samples"]==1

def test_untrusted_proxy_cannot_assert_https(settings):
    settings.TRUSTED_PROXY_CIDRS=["127.0.0.1/32"]
    middleware=TrustedProxyMiddleware(lambda req:req.is_secure())
    factory=RequestFactory()
    assert not middleware(factory.get("/",REMOTE_ADDR="192.0.2.1",HTTP_X_FORWARDED_PROTO="https"))
    assert middleware(factory.get("/",REMOTE_ADDR="127.0.0.1",HTTP_X_FORWARDED_PROTO="https"))

def test_fake_outbox_hidden_in_production(client,settings):
    settings.DEBUG=False
    assert client.get("/dev/outbox").status_code==404
