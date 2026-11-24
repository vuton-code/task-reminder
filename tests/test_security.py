import pytest
from datetime import timedelta
from django.test import RequestFactory, Client
from django.utils import timezone
from accounts.models import Account, AccountProof
from accounts.services import issue_proof, consume_proof
from accounts import rate_limits
from reminders.models import OutboundMessage
from reminders.providers import decrypt
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

def test_password_reset_ends_all_sessions():
    user = Account.objects.create_user(username="person", email="person@example.com", password="old-long-password", email_verified_at=timezone.now())
    a, b = Client(), Client()
    a.force_login(user)
    b.force_login(user)
    a.get("/projects")
    b.get("/projects")
    issue_proof(user, "reset")
    token = decrypt(OutboundMessage.objects.get(purpose="reset").encrypted_payload)["text"].rsplit("/",1)[-1]
    consume_proof(token, "reset", "a-new-very-long-password")
    assert a.get("/reminders/due").status_code == 401
    assert b.get("/reminders/due").status_code == 401
    with pytest.raises(ValidationError):
        consume_proof(token, "reset", "another-long-password")

def test_reset_expires_at_boundary():
    user = Account.objects.create_user(username="person", email="person@example.com", password="old-long-password", email_verified_at=timezone.now())
    proof = issue_proof(user, "reset")
    token = decrypt(OutboundMessage.objects.get(proof=proof).encrypted_payload)["text"].rsplit("/",1)[-1]
    AccountProof.objects.filter(pk=proof.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
    with pytest.raises(ValidationError):
        consume_proof(token, "reset", "a-new-very-long-password")

def test_typo_tolerance_and_account_limit():
    request = RequestFactory().post("/accounts/login", REMOTE_ADDR="127.0.0.1")
    for _ in range(5):
        rate_limits.failed(request, "maya")
    assert rate_limits.wait_seconds(request, "maya") == 0
    rate_limits.failed(request, "maya")
    assert rate_limits.wait_seconds(request, "maya") > 0
    assert rate_limits.allow_recovery(request, "maya@example.com")

def test_csrf_required():
    client = Client(enforce_csrf_checks=True)
    assert client.post("/accounts/login", {"username":"x", "password":"x"}).status_code == 403
