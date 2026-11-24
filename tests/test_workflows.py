import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from datetime import timedelta
from accounts.models import Account
from projects.models import Membership
from projects.services import create_project, depart, change_role
from projects.invitations import invite, accept
from tasks.services import save_task, complete_task
from reminders.services import sweep, dispatch
from reminders.models import OutboundMessage
from reminders.providers import decrypt

pytestmark = pytest.mark.django_db

@pytest.fixture
def owner():
    return Account.objects.create_user(username="owner", email="owner@example.com",
        password="test-password-123", email_verified_at=timezone.now(), email_enabled=True)

def test_task_save_retry_and_completion(owner):
    project = create_project(owner, "Website")
    task = save_task(owner, project, {"title": "Review", "reminder_at": timezone.now()-timedelta(seconds=1)})
    sweep()
    assert OutboundMessage.objects.filter(occurrence__task=task).count() == 1
    complete_task(owner, task, task.version)
    dispatch()
    assert not OutboundMessage.objects.filter(state="accepted").exists()

def test_invitation_requires_correct_verified_account(owner):
    project = create_project(owner, "Private")
    invite(owner, project, "member@example.com")
    message = OutboundMessage.objects.get(purpose="invitation")
    token = decrypt(message.encrypted_payload)["text"].rsplit("/", 1)[-1]
    dispatch()
    stranger = Account.objects.create_user(username="wrong", email="wrong@example.com", email_verified_at=timezone.now())
    with pytest.raises(PermissionDenied):
        accept(stranger, token)
    member = Account.objects.create_user(username="member", email="member@example.com", email_verified_at=timezone.now())
    accept(member, token)
    assert Membership.objects.get(project=project, account=member).role == "member"
    depart(owner, project, Membership.objects.get(project=project, account=member))
    with pytest.raises(ValidationError):
        accept(member, token)

def test_member_cannot_assign_other_members(owner):
    project = create_project(owner, "Private")
    user = Account.objects.create_user(username="member", email="member@example.com", email_verified_at=timezone.now())
    Membership.objects.create(project=project, account=user)
    owner_member = Membership.objects.get(project=project, account=owner)
    with pytest.raises(PermissionDenied):
        save_task(user, project, {"title": "No", "assignee": owner_member})

def test_stale_task_version_fails(owner):
    project = create_project(owner, "Work")
    task = save_task(owner, project, {"title": "First"})
    save_task(owner, project, {"title": "Second"}, task_id=task.pk, version=1)
    with pytest.raises(ValidationError):
        save_task(owner, project, {"title": "Stale"}, task_id=task.pk, version=1)
