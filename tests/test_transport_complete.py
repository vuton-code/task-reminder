import asyncio
from datetime import timedelta
from unittest.mock import patch
import pytest
import httpx
from django.utils import timezone
from reminders.providers import bounded_request, retrieve, retry_delay

def test_total_deadline_cancels_transport():
    async def slow(*args,**kwargs):
        await asyncio.sleep(10)
    original=asyncio.timeout
    with patch("reminders.providers.httpx.AsyncClient.request",side_effect=slow),patch("reminders.providers.asyncio.timeout",side_effect=lambda _:original(.03)):
        with pytest.raises(TimeoutError): bounded_request("GET","https://example.test")

def test_read_only_retrieve(settings):
    settings.EMAIL_BACKEND_MODE="resend"
    stamp=timezone.now()
    with patch("reminders.providers.bounded_request",return_value=httpx.Response(200,json={"id":"known","created_at":stamp.isoformat()})) as request:
        result=retrieve("known")
    assert request.call_args.args[0]=="GET"
    assert result.state=="accepted" and result.accepted_at==stamp

@pytest.mark.parametrize("value",["invalid","nan","inf","-1"])
def test_bad_retry_after(value):
    assert retry_delay(value)==0
