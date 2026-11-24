import pytest
from django.db import IntegrityError, transaction
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from accounts.models import Account
from projects.models import Project, Membership
from projects.permissions import require_membership

pytestmark = pytest.mark.django_db

def test_casefold_unique_accounts():
    Account.objects.create_user(username="Maya", email="maya@example.com", password="long-test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        Account.objects.create_user(username="maya", email="other@example.com")

def test_roles_are_project_scoped():
    user = Account.objects.create_user(username="user", email="user@example.com")
    owner = Account.objects.create_user(username="owner", email="owner@example.com")
    a = Project.objects.create(name="A", owner=owner)
    b = Project.objects.create(name="B", owner=owner)
    Membership.objects.create(project=a, account=owner)
    Membership.objects.create(project=b, account=owner)
    Membership.objects.create(project=a, account=user, role="manager", can_invite=True)
    Membership.objects.create(project=b, account=user)
    require_membership(user, a, "invite")
    with pytest.raises(PermissionDenied):
        require_membership(user, b, "invite")

def test_departed_membership_is_denied():
    owner = Account.objects.create_user(username="owner", email="owner@example.com")
    member = Account.objects.create_user(username="member", email="member@example.com")
    project = Project.objects.create(name="A", owner=owner)
    Membership.objects.create(project=project, account=owner)
    Membership.objects.create(project=project, account=member, left_at=timezone.now())
    with pytest.raises(PermissionDenied):
        require_membership(member, project)
