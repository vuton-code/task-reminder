from concurrent.futures import ThreadPoolExecutor
import pytest
from django.db import connections, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from accounts.models import Account
from projects.models import Membership, Project
from projects.services import create_project, transfer
from tasks.services import save_task
from reminders.services import sweep, dispatch
from reminders.models import OutboundMessage

def run_separate(operation):
    try:
        return operation()
    finally:
        connections.close_all()

@pytest.mark.django_db(transaction=True)
def test_competing_ownership_transfers():
    owner = Account.objects.create_user(username="owner", email="owner@example.test", email_verified_at=timezone.now())
    project = create_project(owner, "Concurrent")
    members = []
    for number in range(2):
        user = Account.objects.create_user(username=f"manager{number}", email=f"manager{number}@example.test")
        members.append(Membership.objects.create(account=user, project=project, role="manager"))
    def move(member):
        try:
            transfer(owner, project, member.pk, 1)
            return True
        except (ValidationError, PermissionDenied):
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda member: run_separate(lambda: move(member)), members))
    assert results.count(True) == 1
    project.refresh_from_db()
    assert project.owner_id in [m.account_id for m in members]
    assert Membership.objects.filter(project=project, account_id=project.owner_id, left_at=None).exists()

@pytest.mark.django_db(transaction=True)
def test_two_workers_accept_once():
    from datetime import timedelta
    owner = Account.objects.create_user(username="owner", email="owner@example.test", email_verified_at=timezone.now(), email_enabled=True)
    project = create_project(owner, "Dispatch")
    save_task(owner, project, {"title":"Once", "reminder_at":timezone.now()-timedelta(seconds=1)})
    sweep()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: run_separate(dispatch), range(2)))
    message = OutboundMessage.objects.get()
    assert message.state == "accepted"
    assert message.attempts == 1
