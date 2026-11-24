from unittest.mock import patch
from types import SimpleNamespace
import httpx
from reminders.providers import encrypt, send


def test_provider_retry_after(settings):
    settings.EMAIL_BACKEND_MODE = "resend"
    message = SimpleNamespace(pk="test-key", recipient="test@example.test",
        encrypted_payload=encrypt({"subject": "Reminder", "text": "Open task"}))
    with patch("reminders.providers.bounded_request", return_value=httpx.Response(429, headers={"Retry-After": "120"})):
        result = send(message)
    assert result.state == "retry"
    assert result.retry_after_seconds == 120
