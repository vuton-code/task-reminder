from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch
import uuid
import pytest
from django.db import connections, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from accounts.models import Account
from accounts.services import digest
from projects.models import Membership, Project, Invitation
from projects.services import create_project, depart
from projects.invitations import invite, accept, cancel
from tasks.services import save_task, complete_task
from reminders.services import sweep, dispatch
from reminders.providers import SendResult, decrypt
from reminders.models import OutboundMessage
pytestmark=pytest.mark.django_db(transaction=True)

def separate(fn):
    try: return fn()
    finally: connections.close_all()

def setup():
    a=Account.objects.create_user(username="owner",email="owner@example.test",email_verified_at=timezone.now(),email_enabled=True)
    b=Account.objects.create_user(username="member",email="member@example.test",email_verified_at=timezone.now(),email_enabled=True)
    p=create_project(a,"Race")
    m=Membership.objects.create(project=p,account=b)
    t=save_task(b,p,{"title":"Task","reminder_at":timezone.now()-timedelta(seconds=1)})
    return a,b,p,m,t

def mutate(kind,a,b,p,m,t):
    if kind=="complete": complete_task(b,t,t.version)
    elif kind=="reschedule": save_task(b,p,{"reminder_at":timezone.now()+timedelta(hours=1)},t.pk,t.version)
    elif kind=="departure": depart(a,p,m)
    elif kind=="assign": save_task(a,p,{"assignee":Membership.objects.get(project=p,account=a)},t.pk,t.version)
    else:
        with transaction.atomic():
            account=Account.objects.select_for_update().get(pk=b.pk)
            account.email_enabled=False
            account.save()

@pytest.mark.parametrize("kind",["complete","reschedule","departure","assign","preference"])
def test_change_committed_before_handoff_suppresses(kind):
    a,b,p,m,t=setup()
    sweep()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            Project.objects.select_for_update().get(pk=p.pk)
            Account.objects.select_for_update().get(pk=b.pk)
            future=pool.submit(separate,dispatch)
            mutate(kind,a,b,p,m,t)
        future.result(timeout=10)
    assert not OutboundMessage.objects.filter(state="accepted").exists()

@pytest.mark.parametrize("kind",["complete","reschedule","departure","assign","preference"])
def test_inflight_handoff_serializes_change(kind):
    a,b,p,m,t=setup()
    sweep()
    started,release,mutation_started=Event(),Event(),Event()
    def provider(message):
        started.set()
        assert release.wait(5)
        return SendResult("accepted","provider-id")
    def change():
        mutation_started.set()
        mutate(kind,a,b,p,m,t)
    with patch("reminders.services.send",side_effect=provider),ThreadPoolExecutor(max_workers=2) as pool:
        sending=pool.submit(separate,dispatch)
        assert started.wait(5)
        changing=pool.submit(separate,change)
        assert mutation_started.wait(5)
        assert not changing.done()
        release.set()
        sending.result(timeout=10); changing.result(timeout=10)
    assert OutboundMessage.objects.get().state=="accepted"

def test_concurrent_duplicate_create_returns_one():
    a,b,p,m,t=setup()
    key=uuid.uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids=list(pool.map(lambda _:separate(lambda:save_task(b,p,{"title":"Once"},key=key).pk),range(2)))
    assert ids[0]==ids[1]

def test_competing_invitation_accept_cancel():
    a,b,p,m,t=setup()
    depart(b,p,m)
    invitation=invite(a,p,b.email)
    message=OutboundMessage.objects.get(invitation=invitation)
    token=decrypt(message.encrypted_payload)["text"].rsplit("/",1)[-1]
    dispatch()
    def accepting():
        try: return accept(b,token).pk
        except ValidationError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        joined=pool.submit(separate,accepting)
        cancelled=pool.submit(separate,lambda:cancel(a,invitation))
        joined.result(timeout=10); cancelled.result(timeout=10)
    invitation.refresh_from_db()
    assert invitation.status in ["accepted","cancelled"]
    assert Membership.objects.filter(project=p,account=b,left_at=None).count()==(1 if invitation.status=="accepted" else 0)

def test_two_acceptances_reuse_membership():
    a,b,p,m,t=setup()
    depart(b,p,m)
    invitation=invite(a,p,b.email); dispatch()
    token=decrypt(OutboundMessage.objects.get(invitation=invitation).encrypted_payload)["text"].rsplit("/",1)[-1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids=list(pool.map(lambda _:separate(lambda:accept(b,token).pk),range(2)))
    assert ids[0]==ids[1]

def test_crash_after_acceptance_replays_identical_key_and_payload():
    a,b,p,m,t=setup(); sweep()
    ledger={}
    def provider(message):
        identity=(message.recipient,message.payload_digest)
        assert ledger.setdefault(str(message.pk),identity)==identity
        if len(ledger)==1 and message.attempts==1:
            raise RuntimeError("simulated worker crash")
        return SendResult("accepted","deduplicated")
    with patch("reminders.services.send",side_effect=provider):
        with pytest.raises(RuntimeError): dispatch()
        OutboundMessage.objects.update(lease_until=timezone.now()-timedelta(seconds=1))
        dispatch()
    assert len(ledger)==1
    assert OutboundMessage.objects.get().state=="accepted"
