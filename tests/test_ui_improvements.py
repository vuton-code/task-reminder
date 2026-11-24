from datetime import timedelta
from unittest.mock import patch
import pytest
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.utils import timezone
from accounts.models import Account
from projects.models import Project, Membership, Invitation, Group, GroupMembership
from projects.services import create_project, delete_project, transfer
from projects.invitations import invite, accept
from tasks.models import Task
from tasks.services import save_task
from reminders.models import OutboundMessage, EmailOccurrence
from reminders.services import sweep, dispatch, schedule_task
from reminders.providers import decrypt

pytestmark = pytest.mark.django_db

@pytest.fixture
def setup():
    owner = Account.objects.create_user(username="owner", email="owner@example.test", email_verified_at=timezone.now(), email_enabled=True)
    user = Account.objects.create_user(username="member", email="member@example.test", email_verified_at=timezone.now(), email_enabled=True)
    project = create_project(owner, "Project to delete")
    member = Membership.objects.create(project=project, account=user)
    return owner, user, project, member


def test_member_choices_and_forged_assignment(client, setup):
    owner, user, project, member = setup
    client.force_login(user)
    url = f"/projects/{project.pk}/tasks"
    response = client.get(url)
    assert list(response.context["form"].fields["assignee"].queryset) == [member]
    response = client.post(url, {"title":"Forgery", "timezone":"UTC", "assignee":str(Membership.objects.get(project=project,account=owner).pk)})
    assert response.status_code == 422
    assert not Task.objects.filter(title="Forgery").exists()
    with pytest.raises(PermissionDenied):
        save_task(user, project, {"title":"Forgery", "assignee":Membership.objects.get(project=project,account=owner)})
    member.role="manager"; member.can_assign=True; member.save()
    assert client.get(url).context["form"].fields["assignee"].queryset.count() == 2


def test_project_roles_and_identity(client, setup):
    owner, user, project, member = setup
    other=create_project(user,"My own project")
    client.force_login(user)
    response=client.get("/projects")
    roles={p.pk:p.current_role for p in response.context["navigation_projects"]}
    assert roles == {project.pk:"Member",other.pk:"Owner"}
    assert b"Signed in as" in response.content and b"member@example.test" in response.content
    member.role="manager"; member.save()
    assert {p.pk:p.current_role for p in client.get("/projects").context["navigation_projects"]}[project.pk] == "Manager"


def test_assignment_timestamp_and_reminder_metadata(client, setup):
    owner,user,project,member=setup
    first=timezone.now()-timedelta(hours=1)
    with patch("tasks.services.timezone.now", return_value=first):
        task=save_task(owner,project,{"title":"Due", "reminder_at":first})
    save_task(owner,project,{"title":"Updated"},task.pk,task.version)
    task.refresh_from_db(); assert task.assigned_at == first
    save_task(owner,project,{"assignee":member},task.pk,task.version)
    task.refresh_from_db(); assert task.assigned_at > first
    client.force_login(user)
    item=client.get("/reminders/due").json()["items"][0]
    assert item["assignee_name"] == user.display_name and item["assigned_at"] == task.assigned_at.isoformat()
    assert item["created_at"] == task.created_at.isoformat()
    assert b"Created <time" in client.get("/reminders").content
    assert "PST" in item["scheduled_label"] or "PDT" in item["scheduled_label"]
    assert item["creator_name"] == owner.display_name
    assert b"Assigned by owner" in client.get("/reminders").content
    Task.objects.filter(pk=task.pk).update(assigned_at=None)
    assert b"Assignment time not recorded" not in client.get("/reminders").content


@pytest.mark.parametrize("role",["member","manager","outsider"])
def test_only_owner_can_delete(client, setup, role):
    owner,user,project,member=setup
    if role=="outsider": member.delete()
    elif role=="manager": member.role="manager"; member.can_assign=True; member.can_invite=True; member.save()
    client.force_login(user)
    url=f"/projects/{project.pk}/delete"
    expected=404 if role=="outsider" else 403
    assert client.get(url).status_code == expected
    assert client.post(url,{"confirmation":project.name,"version":project.version}).status_code == expected
    assert Project.objects.filter(pk=project.pk).exists()


def test_delete_confirmation_cleanup_and_isolation(client, setup):
    owner,user,project,member=setup
    other=create_project(owner,"Keep me")
    other_task=save_task(owner,other,{"title":"Keep task"})
    task=save_task(owner,project,{"title":"Private due task","reminder_at":timezone.now()-timedelta(seconds=1)})
    group=Group.objects.create(project=project,name="Group")
    GroupMembership.objects.create(group=group,membership=member)
    invitation=invite(owner,project,"invitee@example.test")
    sweep()
    assert OutboundMessage.objects.filter(occurrence__task=task).exists()
    client.force_login(owner);url=f"/projects/{project.pk}/delete"
    assert client.get(url).status_code==200
    assert Project.objects.filter(pk=project.pk).exists()
    assert client.post(url,{"confirmation":"wrong","version":project.version}).status_code==409
    csrf=Client(enforce_csrf_checks=True);csrf.force_login(owner)
    assert csrf.post(url,{"confirmation":project.name,"version":project.version}).status_code==403
    response=client.post(url,{"confirmation":project.name,"version":project.version})
    assert response.status_code==302
    assert not Project.objects.filter(pk=project.pk).exists()
    assert not Task.objects.filter(pk=task.pk).exists()
    assert not Membership.objects.filter(project_id=project.pk).exists()
    assert not Invitation.objects.filter(pk=invitation.pk).exists()
    assert not Group.objects.filter(pk=group.pk).exists()
    assert not EmailOccurrence.objects.filter(task_id=task.pk).exists()
    assert not OutboundMessage.objects.exists()
    assert Task.objects.filter(pk=other_task.pk).exists() and Account.objects.filter(pk=user.pk).exists()
    assert client.get(f"/projects/{project.pk}/tasks/{task.pk}").status_code==404
    schedule_task(task.pk)  # Worker picked this ID before deletion; safe to skip.
    assert dispatch() is False


def test_accepted_invitation_does_not_prevent_deletion(setup):
    owner,user,project,member=setup
    invitation=invite(owner,project,"new@example.test")
    token=decrypt(OutboundMessage.objects.get(invitation=invitation).encrypted_payload)["text"].rsplit("/",1)[-1]
    dispatch()
    new=Account.objects.create_user(username="new",email="new@example.test",email_verified_at=timezone.now())
    accept(new,token)
    delete_project(owner,project,project.name,project.version)
    assert not Project.objects.filter(pk=project.pk).exists()


def test_transfer_revokes_old_owner_delete_authority(setup):
    owner,user,project,member=setup
    member.role="manager";member.save()
    transfer(owner,project,member.pk,project.version)
    with pytest.raises(PermissionDenied): delete_project(owner,project,project.name,project.version)


def test_cancelled_invitation_has_clean_copy(client, setup):
    from projects.invitations import cancel
    owner,user,project,member=setup
    other=Account.objects.create_user(username="invitee",email="invitee@example.test",email_verified_at=timezone.now())
    invitation=invite(owner,project,other.email)
    token=decrypt(OutboundMessage.objects.get(invitation=invitation).encrypted_payload)["text"].rsplit("/",1)[-1]
    cancel(owner,invitation)
    client.force_login(other)
    response=client.post(f"/invitations/{token}")
    assert response.status_code==409
    assert b"expired or been canceled" in response.content
    assert b"[&#x27;" not in response.content and b"Back to projects" in response.content
