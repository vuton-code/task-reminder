from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Account
from .forms import RegistrationForm, LoginForm, RecoveryForm, PasswordForm, PreferencesForm
from .services import register, issue_proof, consume_proof, normalize_email
from . import rate_limits

def form_page(request, form, title, button="Continue", **context):
    return render(request, "form.html", {"form": form, "title": title, "button": button, **context},
                  status=422 if form is not None and form.is_bound and form.errors else 200)

def register_view(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            register(form.cleaned_data["username"], form.cleaned_data["email"], form.cleaned_data["password"])
            messages.success(request, "Check your email to verify your address, then sign in.")
            return redirect("login")
        except (ValidationError, IntegrityError):
            form.add_error(None, "Unable to register. Check your details or sign in to an existing account.")
    return form_page(request, form, "Create your account", "Create account", google=True)

def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["username"].strip()
        delay = rate_limits.wait_seconds(request, name)
        if delay:
            form.add_error(None, f"Please wait {delay} seconds before trying again. Password recovery is still available.")
            response = form_page(request, form, "Welcome back", google=True)
            response.status_code = 429
            response["Retry-After"] = str(delay)
            return response
        account = Account.objects.filter(username__iexact=name).first()
        user = authenticate(request, username=account.username if account else name, password=form.cleaned_data["password"])
        if user:
            rate_limits.succeeded(name)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session["auth_generation"] = user.auth_generation
            target = request.GET.get("next", "/projects")
            if not url_has_allowed_host_and_scheme(target, {request.get_host()}):
                target = "/projects"
            return redirect(target)
        rate_limits.failed(request, name)
        form.add_error(None, "Unable to sign in with those details.")
    return form_page(request, form, "Welcome back", "Sign in", google=True)

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")

def proof_view(request, token, purpose):
    form = PasswordForm(request.POST or None) if purpose == "reset" else None
    if request.method == "POST" and (form is None or form.is_valid()):
        try:
            consume_proof(token, purpose, form.cleaned_data["password"] if form else None)
            if purpose == "reset":
                logout(request)
            messages.success(request, "Password reset. Sign in again." if purpose == "reset" else "Your email is verified.")
            return redirect("login")
        except ValidationError as exc:
            if form:
                form.add_error(None, exc)
            else:
                return render(request, "notice.html", {"title": "Link unavailable", "notice": "This link is invalid or expired."}, status=400)
    return form_page(request, form, "Reset your password" if purpose == "reset" else "Verify your email", "Confirm")

@login_required
@require_POST
def resend_verification(request):
    if not request.user.email_verified_at and rate_limits.allow_recovery(request, request.user.email):
        issue_proof(request.user, "verify")
    messages.success(request, "If verification is needed, a new message is on its way.")
    return redirect("projects")

def recovery(request):
    form = RecoveryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = normalize_email(form.cleaned_data["email"])
        if rate_limits.allow_recovery(request, email):
            account = Account.objects.filter(email__iexact=email, email_verified_at__isnull=False).first()
            if account and account.has_usable_password():
                issue_proof(account, "reset")
        return render(request, "notice.html", {"title": "Check your email", "notice": "If an eligible password account exists, we have sent a recovery link. If you use Google, recover access through Google."})
    return form_page(request, form, "Recover your account", "Send recovery link")

@login_required
def preferences(request):
    form = PreferencesForm(request.POST or None, initial={"email_enabled": request.user.email_enabled, "display_timezone": request.user.display_timezone})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            account = Account.objects.select_for_update().get(pk=request.user.pk)
            account.email_enabled = form.cleaned_data["email_enabled"]
            account.display_timezone = form.cleaned_data["display_timezone"]
            account.save()
        messages.success(request, "Preferences saved.")
        return redirect("preferences")
    return form_page(request, form, "Your preferences", "Save preferences", connections=True)

@login_required
def reauthenticate(request):
    form = LoginForm(request.POST or None, initial={"username": request.user.username})
    if request.method == "POST" and form.is_valid():
        delay = rate_limits.wait_seconds(request, request.user.username)
        if not delay and request.user.check_password(form.cleaned_data["password"]):
            request.session["password_confirmed_at"] = timezone.now().timestamp()
            request.session["password_confirmed_account"] = str(request.user.pk)
            return redirect("connections")
        if not delay:
            rate_limits.failed(request, request.user.username)
        form.add_error(None, "Unable to confirm. Try again after the sign-in delay.")
    return form_page(request, form, "Confirm your password", "Confirm")
