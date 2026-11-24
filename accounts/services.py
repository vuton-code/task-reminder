import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Account, AccountProof

def normalize_email(value):
    return value.strip().casefold()

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

@transaction.atomic
def issue_proof(account, purpose):
    from reminders.services import enqueue
    token = secrets.token_urlsafe(32)
    duration = timedelta(hours=24) if purpose == "verify" else timedelta(minutes=30)
    proof = AccountProof.objects.create(account=account, purpose=purpose, token_digest=digest(token), expires_at=timezone.now() + duration)
    route = "verify" if purpose == "verify" else "reset"
    url = f"{settings.APP_BASE_URL}/accounts/{route}/{token}"
    enqueue(purpose, account.email, {"subject": "Verify your email" if purpose == "verify" else "Reset your password", "text": url}, proof=proof)
    return proof

@transaction.atomic
def consume_proof(token, purpose, password=None):
    proof = AccountProof.objects.filter(token_digest=digest(token), purpose=purpose).first()
    if proof is None:
        raise ValidationError("This link is invalid or expired.")
    account = Account.objects.select_for_update().get(pk=proof.account_id)
    proof = AccountProof.objects.select_for_update().get(pk=proof.pk)
    now = timezone.now()
    if proof.consumed_at or now >= proof.expires_at:
        raise ValidationError("This link is invalid or expired.")
    if purpose == "reset":
        if not account.has_usable_password():
            raise ValidationError("Use Google to recover this account.")
        validate_password(password, account)
        account.set_password(password)
        account.auth_generation += 1
        AccountProof.objects.filter(account=account, purpose="reset", consumed_at__isnull=True).update(consumed_at=now)
    else:
        account.email_verified_at = now
    proof.consumed_at = now
    proof.save(update_fields=["consumed_at"])
    account.save()
    return account

@transaction.atomic
def register(username, email, password):
    account = Account(username=username.strip(), email=normalize_email(email))
    validate_password(password, account)
    account.set_password(password)
    account.full_clean()
    account.save()
    issue_proof(account, "verify")
    return account
