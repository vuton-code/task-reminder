import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from accounts.models import Account
from projects.models import Membership
from projects.services import create_project, depart
from projects.groups import save_group

pytestmark = pytest.mark.django_db

def test_group_membership_does_not_change_roles():
    owner = Account.objects.create_user(username="owner",email="owner@example.test",email_verified_at=timezone.now())
    person = Account.objects.create_user(username="person",email="person@example.test")
    project = create_project(owner, "Group project")
    member = Membership.objects.create(project=project, account=person)
    group = save_group(owner, project, "Leads", [member.pk])
    member.refresh_from_db()
    assert member.role == "member"
    assert not member.can_invite and not member.can_assign
    with pytest.raises(PermissionDenied):
        save_group(person, project, "Another", [])
    depart(owner, project, member)
    assert not group.members.exists()

def test_group_rejects_cross_project_member():
    owner = Account.objects.create_user(username="owner",email="owner@example.test",email_verified_at=timezone.now())
    first = create_project(owner, "First")
    second = create_project(owner, "Second")
    member = Membership.objects.get(project=second,account=owner)
    with pytest.raises(ValidationError):
        save_group(owner, first, "Cross", [member.pk])
