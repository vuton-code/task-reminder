import uuid
from django.db import models
from django.utils import timezone

class EmailOccurrence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE)
    schedule_generation = models.PositiveIntegerField()
    assignment_generation = models.PositiveIntegerField()
    recipient = models.ForeignKey("projects.Membership", on_delete=models.PROTECT)
    due_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["task", "schedule_generation", "assignment_generation", "recipient"], name="occurrence_unique")]

class OutboundMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purpose = models.CharField(max_length=20)
    occurrence = models.OneToOneField(EmailOccurrence, null=True, on_delete=models.PROTECT)
    proof = models.OneToOneField("accounts.AccountProof", null=True, on_delete=models.PROTECT)
    invitation = models.OneToOneField("projects.Invitation", null=True, on_delete=models.PROTECT)
    recipient = models.EmailField()
    encrypted_payload = models.TextField()
    payload_digest = models.CharField(max_length=64)
    state = models.CharField(max_length=20, default="pending")
    first_attempt_at = models.DateTimeField(null=True)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    lease_until = models.DateTimeField(null=True)
    lease_owner = models.UUIDField(null=True)
    provider_id = models.CharField(max_length=200, blank=True, db_index=True)
    accepted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)
    reconciliation_only = models.BooleanField(default=False)
    observed_at = models.DateTimeField(null=True)

class DeliveryAttempt(models.Model):
    message = models.ForeignKey(OutboundMessage, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True)
    result = models.CharField(max_length=20, default="unknown")
    provider_status = models.PositiveIntegerField(null=True)

class DeliveryEvent(models.Model):
    event_id = models.CharField(max_length=200, primary_key=True)
    provider_id = models.CharField(max_length=200, db_index=True)
    event_type = models.CharField(max_length=80)
    event_time = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)

class WorkerHeartbeat(models.Model):
    name = models.CharField(max_length=50, primary_key=True)
    seen_at = models.DateTimeField(default=timezone.now)
