import logging
from datetime import timedelta
import pytest
import time_machine
from django.test import RequestFactory, Client
from django.utils import timezone
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError
from accounts.models import Account, AccountProof, RateBucket
from accounts.services import issue_proof, consume_proof
from accounts.rate_limits import failed, wait_seconds, allow_recovery, source_address, succeeded
from reminders.models import OutboundMessage
from reminders.providers import decrypt
from config.logging import SensitiveFilter
pytestmark=pytest.mark.django_db

def user():
    return Account.objects.create_user(username="person",email="person@example.test",password="a-strong-test-password",email_verified_at=timezone.now())

def test_storage_and_redaction():
    a=user()
    b=Account.objects.create_user(username="second",email="second@example.test",password="a-strong-test-password")
    assert identify_hasher(a.password).algorithm=="argon2"
    assert a.password!=b.password
    record=logging.LogRecord("django.server",20,"",1,'GET /accounts/reset/SECRET?code=CODE&state=STATE',(),None)
    SensitiveFilter().filter(record)
    assert all(value not in record.getMessage() for value in ["SECRET","CODE","STATE"])

def test_reset_single_use_and_invalidates_other_proofs(client):
    a=user()
    first=issue_proof(a,"reset")
    second=issue_proof(a,"reset")
    token=decrypt(OutboundMessage.objects.get(proof=first).encrypted_payload)["text"].rsplit("/",1)[-1]
    consume_proof(token,"reset","a-different-strong-password")
    with pytest.raises(ValidationError): consume_proof(token,"reset","another-strong-password")
    second.refresh_from_db()
    assert second.consumed_at is not None

@pytest.mark.parametrize("kind",["unknown","google","unverified"])
def test_recovery_never_issues_ineligible_proof(client,kind):
    if kind!="unknown":
        a=user()
        if kind=="google": a.set_unusable_password()
        else: a.email_verified_at=None
        a.save()
    response=client.post("/accounts/recovery",{"email":"person@example.test"})
    assert response.status_code==200
    assert not AccountProof.objects.filter(purpose="reset").exists()
    assert b"If an eligible password account exists" in response.content

def test_recovery_available_during_login_delay(client):
    a=user()
    req=RequestFactory().post("/",REMOTE_ADDR="127.0.0.1")
    for _ in range(6): failed(req,a.username)
    assert wait_seconds(req,a.username)>0
    assert client.post("/accounts/recovery",{"email":a.email}).status_code==200
    assert AccountProof.objects.filter(purpose="reset").count()==1

def test_throttle_boundaries_and_reset_windows():
    req=RequestFactory().post("/",REMOTE_ADDR="198.51.100.1")
    with time_machine.travel("2026-11-14T12:00:00Z",tick=False) as clock:
        for _ in range(5): failed(req,"name")
        assert wait_seconds(req,"name")==0
        failed(req,"name")
        assert wait_seconds(req,"name")>0
        for _ in range(3):
            clock.shift(timedelta(seconds=30))
            assert wait_seconds(req,"name")==0
            failed(req,"name")
        clock.shift(timedelta(seconds=30)); failed(req,"name")
        assert wait_seconds(req,"name")>=300
        clock.shift(timedelta(minutes=30))
        failed(req,"name")
        assert wait_seconds(req,"name")==0
        succeeded("name")
        assert not RateBucket.objects.filter(key__startswith="account:").exists()

def test_shared_and_distributed_sources(settings):
    factory=RequestFactory()
    for i in range(50): failed(factory.post("/",REMOTE_ADDR="198.51.100.2"),f"name-{i}")
    assert wait_seconds(factory.post("/",REMOTE_ADDR="198.51.100.2"),"new")>0
    for i in range(6): failed(factory.post("/",REMOTE_ADDR=f"198.51.100.{i+10}"),"distributed")
    assert wait_seconds(factory.post("/",REMOTE_ADDR="192.0.2.1"),"distributed")>0
    settings.TRUSTED_PROXY_CIDRS=["127.0.0.1/32"]
    assert source_address(factory.get("/",REMOTE_ADDR="198.51.100.3",HTTP_X_FORWARDED_FOR="1.1.1.1"))=="198.51.100.3"
    assert source_address(factory.get("/",REMOTE_ADDR="127.0.0.1",HTTP_X_FORWARDED_FOR="1.1.1.1, 198.51.100.4"))=="198.51.100.4"

def test_recovery_limits_and_window():
    req=RequestFactory().post("/",REMOTE_ADDR="192.0.2.1")
    with time_machine.travel("2026-11-14T12:00:00Z",tick=False) as clock:
        assert all(allow_recovery(req,"one@example.test") for _ in range(3))
        assert not allow_recovery(req,"one@example.test")
        clock.shift(timedelta(minutes=15))
        assert allow_recovery(req,"one@example.test")
        for i in range(19): assert allow_recovery(req,f"{i}@example.test")
        assert not allow_recovery(req,"last@example.test")

def test_private_pages_no_store_and_safe_redirect(client):
    a=user()
    response=client.post("/accounts/login?next=https://evil.example",{"username":a.username,"password":"a-strong-test-password"})
    assert response.url=="/projects"
    assert "no-store" in response["Cache-Control"]
    assert client.get("/accounts/logout").status_code==405
