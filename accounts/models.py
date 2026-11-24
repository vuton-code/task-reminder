import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

class Account(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    auth_generation = models.PositiveIntegerField(default=0)
    email_enabled = models.BooleanField(default=False)
    display_timezone = models.CharField(max_length=80, default="America/Los_Angeles")

    @property
    def display_name(self):
        if self.first_name:
            return self.first_name
        if self.username.startswith("google_"):
            return self.email.split("@", 1)[0]
        return self.username

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("username"), name="account_username_lower_unique"),
            models.UniqueConstraint(Lower("email"), name="account_email_lower_unique"),
        ]

class AccountProof(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=10, choices=[("verify", "Verify"), ("reset", "Reset")])
    token_digest = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)

class RateBucket(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    window_start = models.DateTimeField()
    last_failure = models.DateTimeField()
    blocked_until = models.DateTimeField(null=True)

class GoogleFlow(models.Model):
    state_digest = models.CharField(max_length=64, primary_key=True)
    session_digest = models.CharField(max_length=64)
    nonce = models.CharField(max_length=100)
    verifier = models.CharField(max_length=100)
    connect_account = models.ForeignKey(Account, null=True, on_delete=models.CASCADE)
    return_path = models.CharField(max_length=500)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)
