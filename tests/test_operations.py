import pytest
from datetime import timedelta
from django.core.management import call_command
from django.utils import timezone
from accounts.models import GoogleFlow
from reminders.models import WorkerHeartbeat
from reminders.health import snapshot

pytestmark = pytest.mark.django_db

def test_worker_heartbeat_threshold():
    WorkerHeartbeat.objects.create(name="reminders",seen_at=timezone.now())
    assert snapshot()["healthy"]
    WorkerHeartbeat.objects.update(seen_at=timezone.now()-timedelta(seconds=16))
    assert not snapshot()["healthy"]

def test_flow_secret_cleanup():
    GoogleFlow.objects.create(state_digest="a"*64,session_digest="b"*64,nonce="secret",verifier="proof",
        return_path="/projects",expires_at=timezone.now()-timedelta(seconds=1))
    call_command("cleanup_expired")
    assert not GoogleFlow.objects.exists()
