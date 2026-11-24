import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from accounts.models import Account
from projects.services import create_project, depart
from projects.models import Membership
from tasks.services import save_task
from reminders.models import OutboundMessage
from reminders.services import sweep, dispatch
from reminders.providers import SendResult

pytestmark = pytest.mark.django_db

@pytest.fixture
def setup():
    user = Account.objects.create_user(username="person", email="person@example.test",
        email_enabled=True, email_verified_at=timezone.now())
    project = create_project(user, "Project")
    task = save_task(user, project, {"title": "Due", "reminder_at": timezone.now()-timedelta(seconds=1)})
    return user, project, task

def test_accepted_message_is_not_duplicated(setup):
    sweep()
    dispatch()
    sweep()
    dispatch()
    assert OutboundMessage.objects.filter(state="accepted").count() == 1

def test_rescheduling_cancels_old_schedule(setup):
    user, project, task = setup
    sweep()
    save_task(user, project, {"reminder_at": timezone.now()+timedelta(hours=1)}, task.pk, task.version)
    dispatch()
    assert not OutboundMessage.objects.filter(state="accepted").exists()

def test_preference_rechecked(setup):
    user, project, task = setup
    sweep()
    user.email_enabled = False
    user.save()
    dispatch()
    assert OutboundMessage.objects.get().state == "suppressed"

def test_unknown_is_held_after_retention(setup):
    sweep()
    with patch("reminders.services.send", return_value=SendResult("unknown")):
        dispatch()
    message = OutboundMessage.objects.get()
    assert message.state == "unknown"
    message.first_attempt_at = timezone.now()-timedelta(hours=25)
    message.next_attempt_at = timezone.now()-timedelta(seconds=1)
    message.save()
    dispatch()
    message.refresh_from_db()
    assert message.state == "held"

def test_no_early_email(setup):
    user, project, task = setup
    task.reminder_at = timezone.now()+timedelta(hours=1)
    task.save()
    sweep()
    assert not OutboundMessage.objects.exists()
