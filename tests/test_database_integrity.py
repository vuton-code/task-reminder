import pytest
from django.db import transaction, DatabaseError
from django.utils import timezone
from accounts.models import Account
from projects.models import Membership, Group, GroupMembership
from projects.services import create_project
from tasks.models import Task
pytestmark=pytest.mark.django_db(transaction=True)

@pytest.mark.parametrize("violation",["task","group","move_group","owner","depart"])
def test_database_rejects_invalid_relationship(violation):
    a=Account.objects.create_user(username="a",email="a@example.test",email_verified_at=timezone.now())
    p=create_project(a,"One"); q=create_project(a,"Two")
    m=Membership.objects.get(project=p,account=a)
    g=Group.objects.create(project=p,name="Group")
    GroupMembership.objects.create(group=g,membership=m)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            if violation=="task": Task.objects.create(project=q,assignee=m,title="Wrong")
            elif violation=="group": GroupMembership.objects.create(group=Group.objects.create(project=q,name="Other"),membership=m)
            elif violation=="move_group": Group.objects.filter(pk=g.pk).update(project=q)
            elif violation=="owner": Membership.objects.filter(pk=m.pk).delete()
            else: Membership.objects.filter(pk=m.pk).update(left_at=timezone.now())
