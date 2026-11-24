from datetime import timedelta
from unittest.mock import patch
import pytest
from django.utils import timezone
from accounts.models import Account
from projects.services import create_project
from tasks.services import save_task, complete_task
from reminders.models import OutboundMessage
from reminders.services import sweep, dispatch
from reminders.providers import SendResult
pytestmark = pytest.mark.django_db

def fixture():
    user=Account.objects.create_user(username="retry",email="retry@example.test",email_verified_at=timezone.now(),email_enabled=True)
    project=create_project(user,"Retries")
    task=save_task(user,project,{"title":"Private title","description":"SECRET DESCRIPTION","reminder_at":timezone.now()-timedelta(seconds=1)})
    sweep()
    return user,project,task

def test_unknown_after_completion_keeps_readonly_reconciliation():
    user,project,task=fixture()
    with patch("reminders.services.send",return_value=SendResult("unknown",provider_id="known-id")):
        dispatch()
    complete_task(user,task,task.version)
    OutboundMessage.objects.update(next_attempt_at=timezone.now()-timedelta(seconds=1))
    with patch("reminders.services.retrieve",return_value=SendResult("accepted",provider_id="known-id")) as read, patch("reminders.services.send") as send:
        dispatch()
    assert read.called
    send.assert_not_called()
    assert OutboundMessage.objects.get().state=="accepted"

def test_unknown_changed_title_never_replays_and_remains_reconcilable():
    user,project,task=fixture()
    with patch("reminders.services.send",return_value=SendResult("unknown")):
        dispatch()
    save_task(user,project,{"title":"Changed"},task.pk,task.version)
    OutboundMessage.objects.update(next_attempt_at=timezone.now()-timedelta(seconds=1))
    with patch("reminders.services.send") as send:
        dispatch()
    send.assert_not_called()
    message=OutboundMessage.objects.get()
    assert message.state=="unknown"
    assert message.reconciliation_only

def test_late_eligible_task_not_starved_by_accepted_prefix():
    user,project,task=fixture()
    dispatch()
    # Sweep must page all eligible records instead of endlessly revisiting the first batch.
    with patch("reminders.services.schedule_task") as schedule:
        sweep()
    assert schedule.call_count==1

def test_login_delay_explains_retry(client):
    from accounts.rate_limits import failed
    from django.test import RequestFactory
    req=RequestFactory().post("/",REMOTE_ADDR="127.0.0.1")
    for _ in range(6): failed(req,"typo")
    response=client.post("/accounts/login",{"username":"typo","password":"a wrong password"})
    assert response.status_code==429
    assert b"wait" in response.content.lower()
