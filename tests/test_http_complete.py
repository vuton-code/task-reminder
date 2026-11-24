import uuid
from datetime import timedelta
import pytest
from django.utils import timezone
from accounts.models import Account, AccountProof
from projects.services import create_project
from projects.models import Membership
from tasks.services import save_task
from reminders.services import sweep
from reminders.models import OutboundMessage
from reminders.providers import decrypt
pytestmark=pytest.mark.django_db

def setup(client):
    a=Account.objects.create_user(username="owner",email="owner@example.test",email_verified_at=timezone.now(),email_enabled=True)
    p=create_project(a,"Project")
    client.force_login(a)
    return a,p

@pytest.mark.parametrize("path",["members?group=bad","tasks?assignee=bad"])
def test_invalid_uuid_returns_safe_not_found(client,path):
    a,p=setup(client)
    assert client.get(f"/projects/{p.pk}/{path}").status_code==404

def test_task_pagination_filters_and_conflict_preserves_input(client):
    a,p=setup(client)
    for i in range(51): save_task(a,p,{"title":f"Task {i}"})
    url=f"/projects/{p.pk}/tasks"
    assert len(client.get(url).context["tasks"])==50
    assert len(client.get(url+"?page=2").context["tasks"])==1
    assert len(client.get(url+"?status=completed").context["tasks"])==0
    task=save_task(a,p,{"title":"Concurrent"})
    response=client.post(f"{url}/{task.pk}/edit",{"title":"My unsaved work","timezone":"UTC","expected_version":0})
    assert response.status_code==409 and b"My unsaved work" in response.content

def test_due_pagination_and_completion(client):
    a,p=setup(client)
    for i in range(101): save_task(a,p,{"title":f"Due {i}","reminder_at":timezone.now()-timedelta(seconds=1)})
    first=client.get("/reminders/due").json()
    second=client.get("/reminders/due?cursor="+first["next_cursor"]).json()
    assert len(first["items"])==100 and len(second["items"])==1
    response=client.get("/reminders?cursor=100")
    assert len(response.context["due_items"])==1
    assert b"data-offset=\"100\"" in response.content

def test_verification_get_does_not_consume_and_boundary(client):
    from accounts.services import issue_proof
    a,p=setup(client)
    proof=issue_proof(a,"verify")
    token=decrypt(OutboundMessage.objects.get(proof=proof).encrypted_payload)["text"].rsplit("/",1)[-1]
    assert client.get("/accounts/verify/"+token).status_code==200
    proof.refresh_from_db(); assert proof.consumed_at is None
    proof.expires_at=timezone.now(); proof.save()
    assert client.post("/accounts/verify/"+token).status_code==400

def test_registration_duplicates_and_password_confirmation(client):
    payload={"username":"new","email":"new@example.test","password":"a-long-test-password","confirmation":"wrong"}
    assert client.post("/accounts/register",payload).status_code==422
    assert not Account.objects.exists()
    payload["confirmation"]=payload["password"]
    assert client.post("/accounts/register",payload).status_code==302
    assert client.post("/accounts/register",payload).status_code==422
    assert Account.objects.count()==1

def test_transfer_contract_endpoint(client):
    a,p=setup(client)
    b=Account.objects.create_user(username="manager",email="manager@example.test")
    m=Membership.objects.create(project=p,account=b,role="manager")
    response=client.post(f"/projects/{p.pk}/transfer",{"target_membership_id":str(m.pk),"expected_version":p.version})
    assert response.status_code==302
    p.refresh_from_db(); assert p.owner_id==b.pk
