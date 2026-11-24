import hashlib
import hmac
import ipaddress
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import RateBucket

def identifier(value):
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()

def source_address(request):
    peer = request.META.get("REMOTE_ADDR", "127.0.0.1")
    try:
        address = ipaddress.ip_address(peer)
        trusted = any(address in ipaddress.ip_network(cidr) for cidr in settings.TRUSTED_PROXY_CIDRS if cidr)
        if trusted:
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
            for candidate in reversed(forwarded):
                candidate = candidate.strip()
                if not candidate:
                    continue
                address = ipaddress.ip_address(candidate)
                if not any(address in ipaddress.ip_network(c) for c in settings.TRUSTED_PROXY_CIDRS if c):
                    break
        return str(address)
    except ValueError:
        return peer

def keys(request, username):
    return ["account:" + identifier(username.casefold()), "source:" + identifier(source_address(request))]

def wait_seconds(request, username):
    now = timezone.now()
    blocks = RateBucket.objects.filter(key__in=keys(request, username), blocked_until__gt=now)
    return max([int((b.blocked_until - now).total_seconds()) + 1 for b in blocks] or [0])

@transaction.atomic
def failed(request, username):
    now = timezone.now()
    for key in sorted(keys(request, username)):
        RateBucket.objects.get_or_create(key=key, defaults={"window_start": now, "last_failure": now})
        bucket = RateBucket.objects.select_for_update().get(pk=key)
        if bucket.blocked_until and bucket.blocked_until > now:
            continue
        account = key.startswith("account:")
        expired = now - (bucket.last_failure if account else bucket.window_start) >= timedelta(minutes=30 if account else 10)
        if expired:
            bucket.count = 0
            bucket.window_start = now
        bucket.count += 1
        bucket.last_failure = now
        delay = 0
        if account and bucket.count >= 6:
            delay = 300 if bucket.count >= 10 else 30
        if not account and bucket.count >= 50:
            delay = 300
        bucket.blocked_until = now + timedelta(seconds=delay) if delay else None
        bucket.save()

def succeeded(username):
    RateBucket.objects.filter(key="account:" + identifier(username.casefold())).delete()

@transaction.atomic
def allow_recovery(request, email):
    now = timezone.now()
    allowed = True
    limits = [(3, "recovery-account:" + identifier(email)), (20, "recovery-source:" + identifier(source_address(request)))]
    for limit, key in sorted(limits, key=lambda pair: pair[1]):
        RateBucket.objects.get_or_create(key=key, defaults={"window_start": now, "last_failure": now})
        bucket = RateBucket.objects.select_for_update().get(pk=key)
        if now - bucket.window_start >= timedelta(minutes=15):
            bucket.window_start, bucket.count = now, 0
        if bucket.count >= limit:
            allowed = False
        else:
            bucket.count += 1
        bucket.last_failure = now
        bucket.save()
    return allowed
