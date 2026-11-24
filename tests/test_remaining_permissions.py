import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from accounts.models import Account
from projects.services import create_project, change_role, transfer, depart
from projects.models import Membership
from projects.invitations import invite, cancel
from reminders.services import sweep, dispatch
from reminders.models import OutboundMessage
from tasks.services import save_task
from tasks.models import Task

pytestmark=pytest.mark.django_db

def users_and_project():
    owner=Account.objects.create_user(username="owner",email="owner@example.test",email_verified_at=timezone.now())
    manager=Account.objects.create_user(username="manager",email="manager@example.test",email_verified_at=timezone.now())
    regular=Account.objects.create_user(username="regular",email="regular@example.test",email_verified_at=timezone.now(),email_enabled=True)
    project=create_project(owner,"Project")
    manager_member=Membership.objects.create(project=project,account=manager,role="manager",can_invite=True)
    regular_member=Membership.objects.create(project=project,account=regular)
    return owner,manager,regular,project,manager_member,regular_member

def test_manager_can_cancel_own_invitation_only():
    owner,manager,regular,project,mm,rm=users_and_project()
    mine=invite(manager,project,"one@example.test")
    other=invite(owner,project,"two@example.test")
    cancel(manager,mine)
    with pytest.raises(PermissionDenied):
        cancel(manager,other)
    change_role(owner,project,mm,"manager",False,False,mm.version)
    with pytest.raises(PermissionDenied):
        invite(manager,project,"three@example.test")

def test_owner_must_transfer_before_leaving():
    owner,manager,regular,project,mm,rm=users_and_project()
    own=Membership.objects.get(project=project,account=owner)
    with pytest.raises(ValidationError):
        depart(owner,project,own)
    transfer(owner,project,mm.pk,project.version)
    depart(owner,project,own)
    project.refresh_from_db()
    assert project.owner_id==manager.pk

def test_departed_assignee_receives_no_queued_email():
    owner,manager,regular,project,mm,rm=users_and_project()
    task=save_task(owner,project,{"title":"Private task","assignee":rm,"reminder_at":timezone.now()-timedelta(seconds=1)})
    sweep()
    depart(owner,project,rm)
    dispatch()
    assert not OutboundMessage.objects.filter(state="accepted").exists()
    task.refresh_from_db()
    assert task.assignee_id is None

def test_reassignment_changes_reminder_recipient():
    owner,manager,regular,project,mm,rm=users_and_project()
    owner.email_enabled=True
    owner.save()
    own=Membership.objects.get(project=project,account=owner)
    task=save_task(owner,project,{"title":"Private task","assignee":rm,"reminder_at":timezone.now()-timedelta(seconds=1)})
    sweep()
    save_task(owner,project,{"assignee":own},task.pk,task.version)
    sweep()
    while dispatch():
        pass
    assert list(OutboundMessage.objects.filter(state="accepted").values_list("recipient",flat=True))==[owner.email]
