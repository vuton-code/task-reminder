import uuid
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from accounts.models import Account
from projects.models import Membership, GroupMembership
from projects.services import create_project, change_role, depart
from projects.permissions import require_membership
from projects.groups import save_group, delete_group
from tasks.services import save_task, complete_task
pytestmark=pytest.mark.django_db

@pytest.fixture
def matrix():
    users={}
    for role in ["owner","manager","inviter","assigner","member","outsider"]:
        users[role]=Account.objects.create_user(username=role,email=role+"@example.test",email_verified_at=timezone.now())
    p=create_project(users["owner"],"Private project")
    for role in ["manager","inviter","assigner","member"]:
        Membership.objects.create(project=p,account=users[role],role="member" if role=="member" else "manager",
            can_invite=role=="inviter",can_assign=role=="assigner")
    return users,p

@pytest.mark.parametrize("role",["owner","manager","inviter","assigner","member","outsider"])
@pytest.mark.parametrize("action",["view","invite","assign","owner"])
def test_authority_matrix(matrix,role,action):
    users,p=matrix
    allowed=role=="owner" or (action=="view" and role!="outsider") or (action=="invite" and role=="inviter") or (action=="assign" and role=="assigner")
    if allowed: assert require_membership(users[role],p,action)
    else:
        with pytest.raises(PermissionDenied): require_membership(users[role],p,action)

@pytest.mark.parametrize("role",["owner","manager","inviter","assigner","member","outsider"])
def test_assign_and_complete_matrix(matrix,role):
    users,p=matrix
    task=save_task(users["member"],p,{"title":"Member work"})
    if role in ["owner","assigner","member"]:
        complete_task(users[role],task,task.version)
    else:
        with pytest.raises(PermissionDenied): complete_task(users[role],task,task.version)

@pytest.mark.parametrize("path",["tasks","members","groups"])
def test_cross_project_direct_reads(matrix,client,path):
    users,p=matrix
    create_project(users["outsider"],"Other owned project")
    client.force_login(users["outsider"])
    response=client.get(f"/projects/{p.pk}/{path}")
    assert response.status_code==404
    assert b"Private project" not in response.content

def test_group_cleanup_and_no_authority_change(matrix):
    users,p=matrix
    member=Membership.objects.get(project=p,account=users["member"])
    group=save_group(users["owner"],p,"Design",[member.pk])
    with pytest.raises(PermissionDenied):
        save_group(users["member"],p,"Bad",[])
    task=save_task(users["member"],p,{"title":"Retained"})
    depart(users["member"],p,member)
    assert not GroupMembership.objects.filter(group=group).exists()
    task.refresh_from_db()
    assert task.assignee is None
    delete_group(users["owner"],group,group.version)
    assert task.__class__.objects.filter(pk=task.pk).exists()

def test_duplicate_key_conflict_and_replay_revocation(matrix):
    users,p=matrix
    key=uuid.uuid4()
    save_task(users["member"],p,{"title":"Once"},key=key)
    with pytest.raises(ValidationError): save_task(users["member"],p,{"title":"Different"},key=key)
    depart(users["member"],p,Membership.objects.get(project=p,account=users["member"]))
    with pytest.raises(PermissionDenied): save_task(users["member"],p,{"title":"Once"},key=key)

def test_revoked_assignment_permission_rechecked(matrix):
    users,p=matrix
    mm=Membership.objects.get(project=p,account=users["assigner"])
    task=save_task(users["member"],p,{"title":"Not yours"})
    change_role(users["owner"],p,mm,"manager",False,False,mm.version)
    with pytest.raises(PermissionDenied): save_task(users["assigner"],p,{"title":"Denied"},task.pk,task.version)
