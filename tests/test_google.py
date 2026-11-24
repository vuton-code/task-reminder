import pytest
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import Account
from accounts.google_flow import resolve_identity

pytestmark = pytest.mark.django_db

def claims(sub="google-sub", email="person@gmail.com"):
    return {"sub": sub, "email": email, "email_verified": True}

def test_google_creates_profile_without_local_password():
    account = resolve_identity(claims())
    assert not account.has_usable_password()
    assert account.email_verified_at
    assert resolve_identity(claims()).pk == account.pk
    assert Account.objects.count() == 1

def test_google_does_not_merge_email_collision():
    Account.objects.create_user(username="old", email="person@gmail.com", password="long-password")
    with pytest.raises(ValidationError):
        resolve_identity(claims())

def test_google_external_email_needs_verification():
    account = resolve_identity(claims(email="external@example.com"))
    assert account.email_verified_at is None

def test_google_connect_requires_matching_email():
    account = Account.objects.create_user(username="old", email="other@gmail.com", email_verified_at=timezone.now())
    with pytest.raises(ValidationError):
        resolve_identity(claims(), connect_account=account)
