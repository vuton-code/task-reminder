"""Bounded provider transport. Never log message bodies or credentials."""
import asyncio
import json
import math
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import httpx
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

@dataclass
class SendResult:
    state: str
    provider_id: str = ""
    status: int | None = None
    retry_after_seconds: float = 0
    accepted_at: datetime | None = None

def encrypt(payload):
    return Fernet(settings.OUTBOX_ENCRYPTION_KEY.encode()).encrypt(json.dumps(payload,sort_keys=True).encode()).decode()

def decrypt(payload):
    return json.loads(Fernet(settings.OUTBOX_ENCRYPTION_KEY.encode()).decrypt(payload.encode()))

async def _request(method, url, **kwargs):
    # asyncio's total deadline includes connection, write and response-body read.
    async with asyncio.timeout(5):
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            return await client.request(method,url,**kwargs)

def bounded_request(method,url,**kwargs):
    return asyncio.run(_request(method,url,**kwargs))

def retry_delay(value):
    try:
        delay=float(value)
    except (ValueError,TypeError):
        try:
            delay=(parsedate_to_datetime(value)-timezone.now()).total_seconds()
        except (ValueError,TypeError,OverflowError):
            return 0
    return min(86400,max(0,delay)) if math.isfinite(delay) else 0

def send(message):
    if settings.EMAIL_BACKEND_MODE=="fake":
        if not settings.DEBUG:
            raise RuntimeError("Fake email is restricted to development.")
        return SendResult("accepted",f"fake-{message.pk}",200)
    payload=decrypt(message.encrypted_payload)
    body={"from":settings.EMAIL_FROM,"to":[message.recipient],"subject":payload["subject"],
          "text":payload["text"],"tags":[{"name":"message_id","value":str(message.pk)}]}
    if payload.get("html"):
        body["html"]=payload["html"]
    try:
        response=bounded_request("POST","https://api.resend.com/emails",json=body,
            headers={"Authorization":f"Bearer {settings.RESEND_API_KEY}","Idempotency-Key":str(message.pk)})
        if 200<=response.status_code<300:
            provider_id=response.json().get("id","")
            return SendResult("accepted" if provider_id else "unknown",provider_id,response.status_code)
        if response.status_code==429 or response.status_code>=500:
            return SendResult("retry",status=response.status_code,
                retry_after_seconds=retry_delay(response.headers.get("Retry-After","0")))
        return SendResult("rejected",status=response.status_code)
    except (httpx.HTTPError,TimeoutError,ValueError):
        return SendResult("unknown")

def retrieve(provider_id):
    if not provider_id or settings.EMAIL_BACKEND_MODE=="fake":
        return SendResult("unknown",provider_id)
    try:
        response=bounded_request("GET","https://api.resend.com/emails/"+quote(provider_id,safe=""),
            headers={"Authorization":f"Bearer {settings.RESEND_API_KEY}"})
        if response.status_code==200:
            data=response.json()
            if data.get("id")==provider_id:
                stamp=parse_datetime(data.get("created_at",""))
                if stamp and timezone.is_naive(stamp):
                    stamp=None
                return SendResult("accepted",provider_id,200,accepted_at=stamp)
        return SendResult("unknown",provider_id,response.status_code)
    except (httpx.HTTPError,TimeoutError,ValueError,TypeError):
        return SendResult("unknown",provider_id)
