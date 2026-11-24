import base64
import hashlib
import secrets
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import urlencode

import httpx
import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError, connection
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import _verify_and_decode
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from .models import Account, AccountProof
from .services import normalize_email, digest

def authoritative(claims):
    email = claims.get("email", "").casefold()
    return claims.get("email_verified") is True and (email.endswith("@gmail.com") or bool(claims.get("hd")))

@transaction.atomic
def resolve_identity(claims, connect_account=None):
    email = normalize_email(claims.get("email", ""))
    subject = claims.get("sub")
    if not subject or not email:
        raise ValidationError("Google did not return the required identity.")
    # Serialize first login for the same provider subject across processes.
    lock_id = int.from_bytes(hashlib.sha256(subject.encode()).digest()[:8], "big", signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
    existing = SocialAccount.objects.select_related("user").filter(provider="google", uid=subject).first()
    if existing:
        if connect_account and existing.user_id != connect_account.pk:
            raise ValidationError("This Google account is already connected elsewhere.")
        account = Account.objects.select_for_update().get(pk=existing.user_id)
        if not account.is_active:
            raise ValidationError("This account is unavailable.")
        if email != normalize_email(account.email):
            account.email_verified_at = None
            account.save(update_fields=["email_verified_at"])
        return account
    if connect_account:
        account = Account.objects.select_for_update().get(pk=connect_account.pk)
        if not account.email_verified_at or claims.get("email_verified") is not True or normalize_email(account.email) != email:
            raise ValidationError("Connect Google using the same verified email as this account.")
        if SocialAccount.objects.filter(user=account, provider="google").exists():
            raise ValidationError("A Google identity is already connected.")
    else:
        if Account.objects.filter(email__iexact=email).exists():
            raise ValidationError("Sign in to your existing account, then connect Google in Preferences.")
        account = Account(username="google_" + secrets.token_hex(12), email=email,
            first_name=claims.get("given_name", "")[:150],
            email_verified_at=timezone.now() if authoritative(claims) else None)
        account.set_unusable_password()
        account.save()
        if not account.email_verified_at:
            from .services import issue_proof
            issue_proof(account, "verify")
    SocialAccount.objects.create(user=account, provider="google", uid=subject,
        extra_data={"email": email})
    return account

@require_POST
def begin(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return render(request, "notice.html", {"title": "Google sign-in needs configuration",
            "notice": "The site administrator needs to configure the Google OAuth client."}, status=503)
    connect = request.POST.get("process") == "connect"
    if connect:
        recent = request.session.get("password_confirmed_at", 0)
        same_account = request.session.get("password_confirmed_account") == str(request.user.pk)
        if not request.user.is_authenticated or not same_account or timezone.now().timestamp() - recent > 300:
            return HttpResponseRedirect("/accounts/reauthenticate")
    if not request.session.session_key:
        request.session.create()
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    target = request.POST.get("next", "/projects")
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}):
        target = "/projects"
    from .models import GoogleFlow
    GoogleFlow.objects.create(state_digest=digest(state), session_digest=digest(request.session.session_key),
        nonce=nonce, verifier=verifier, connect_account=request.user if connect else None,
        return_path=target, expires_at=timezone.now()+timedelta(minutes=10))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    query = urlencode({"client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.APP_BASE_URL + "/accounts/google/login/callback/",
        "response_type": "code", "scope": "openid email profile", "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account"})
    return HttpResponseRedirect("https://accounts.google.com/o/oauth2/v2/auth?" + query)

def callback(request):
    from .models import GoogleFlow
    error = "Google sign-in could not be completed. Please start again."
    with transaction.atomic():
        flow = GoogleFlow.objects.select_for_update().filter(state_digest=digest(request.GET.get("state", ""))).first()
        if (not flow or flow.consumed_at or timezone.now() >= flow.expires_at
                or flow.session_digest != digest(request.session.session_key or "")):
            return render(request, "notice.html", {"title": "Sign-in unavailable", "notice": error}, status=400)
        flow.consumed_at = timezone.now()
        flow.save(update_fields=["consumed_at"])
    try:
        if request.GET.get("error") or not request.GET.get("code"):
            raise ValidationError(error)
        response = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": request.GET["code"], "code_verifier": flow.verifier, "grant_type": "authorization_code",
            "redirect_uri": settings.APP_BASE_URL + "/accounts/google/login/callback/"}, timeout=5)
        response.raise_for_status()
        claims = _verify_and_decode(SimpleNamespace(client_id=settings.GOOGLE_CLIENT_ID), response.json()["id_token"], verify_signature=True)
        if not all(field in claims for field in ["sub", "exp", "iss", "aud", "nonce"]):
            raise ValidationError(error)
        if not secrets.compare_digest(claims.get("nonce", ""), flow.nonce):
            raise ValidationError(error)
        target = None
        if flow.connect_account_id:
            recent = request.session.get("password_confirmed_at", 0)
            if (not request.user.is_authenticated or request.user.pk != flow.connect_account_id
                    or timezone.now().timestamp() - recent > 300):
                raise ValidationError("Confirm your password again before connecting Google.")
            target = request.user
        account = resolve_identity(claims, connect_account=target)
        login(request, account, backend="django.contrib.auth.backends.ModelBackend")
        request.session["auth_generation"] = account.auth_generation
        return HttpResponseRedirect(flow.return_path)
    except (ValidationError, IntegrityError, httpx.HTTPError, requests.RequestException, OAuth2Error, ValueError, KeyError) as exc:
        notice = str(exc.messages[0]) if isinstance(exc, ValidationError) else error
        return render(request, "notice.html", {"title": "Sign-in unavailable", "notice": notice}, status=400)
    finally:
        GoogleFlow.objects.filter(pk=flow.pk).update(nonce="", verifier="")

@login_required
def connections(request):
    return render(request, "accounts/connections.html", {
        "google_connection": SocialAccount.objects.filter(user=request.user, provider="google").first()})
