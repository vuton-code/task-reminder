import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=10, choices=[("member", "Member"), ("manager", "Manager")], default="member")
    can_invite = models.BooleanField(default=False)
    can_assign = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "account"], condition=Q(left_at__isnull=True), name="active_membership_unique"),
            models.CheckConstraint(condition=Q(role="manager") | Q(role="member", can_invite=False, can_assign=False), name="valid_membership_role"),
        ]

class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recipient_email = models.EmailField()
    token_digest = models.CharField(max_length=64, unique=True)
    sent_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=12, default="prepared", choices=[(x, x) for x in ["prepared", "pending", "accepted", "cancelled"]])
    accepted_membership = models.ForeignKey(Membership, null=True, on_delete=models.PROTECT)

class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    version = models.PositiveIntegerField(default=1)
    members = models.ManyToManyField(Membership, through="GroupMembership")

    class Meta:
        constraints = [models.UniqueConstraint(Lower("name"), "project", name="project_group_name_unique")]

class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "membership"], name="group_member_unique")]

class MutationReceipt(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    operation = models.CharField(max_length=100)
    key = models.UUIDField()
    input_digest = models.CharField(max_length=64)
    resource_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["actor", "operation", "key"], name="mutation_unique")]
