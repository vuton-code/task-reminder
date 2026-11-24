import hashlib
import json
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.models import Account
from config.errors import Conflict
from .models import Project, Membership, MutationReceipt, GroupMembership
from .permissions import require_membership

def receipt(actor, operation, key, payload):
    if not key:
        return None, None
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    previous = MutationReceipt.objects.filter(actor=actor, operation=operation, key=key).first()
    if previous and previous.input_digest != digest:
        raise Conflict("This save was already used for different content.")
    return previous, digest

def record(actor, operation, key, digest, resource):
    if key:
        MutationReceipt.objects.create(actor=actor, operation=operation, key=key, input_digest=digest, resource_id=resource.pk)

@transaction.atomic
def create_project(actor, name, key=None):
    account = Account.objects.select_for_update().get(pk=actor.pk)
    if not account.email_verified_at:
        raise PermissionDenied("Verify your email before creating a project.")
    name = name.strip()
    if not name or len(name) > 100:
        raise ValidationError("Use a project name between 1 and 100 characters.")
    previous, digest = receipt(actor, "create-project", key, {"name": name})
    if previous:
        project = Project.objects.get(pk=previous.resource_id)
        require_membership(actor, project)
        return project
    project = Project.objects.create(name=name, owner=actor)
    Membership.objects.create(project=project, account=actor)
    record(actor, "create-project", key, digest, project)
    return project

@transaction.atomic
def change_role(actor, project, membership, role, can_invite=False, can_assign=False, version=None):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_membership(actor, project, "owner")
    target = Membership.objects.select_for_update().get(pk=membership.pk, project=project, left_at__isnull=True)
    if target.account_id == project.owner_id:
        raise ValidationError("Transfer ownership before changing the owner's role.")
    if version is not None and target.version != version:
        raise Conflict("Membership changed. Reload before trying again.")
    if role not in ["member", "manager"]:
        raise ValidationError("Choose a valid role.")
    target.role = role
    target.can_invite = role == "manager" and can_invite
    target.can_assign = role == "manager" and can_assign
    target.version += 1
    target.save()

@transaction.atomic
def transfer(actor, project, target_id, version):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_membership(actor, project, "owner")
    if project.version != version:
        raise Conflict("Project changed. Reload before trying again.")
    target = Membership.objects.get(pk=target_id, project=project, left_at__isnull=True, role="manager")
    old = Membership.objects.get(project=project, account=actor, left_at__isnull=True)
    old.role, old.can_invite, old.can_assign = "manager", True, True
    old.version += 1
    old.save()
    project.owner = target.account
    project.version += 1
    project.save()

@transaction.atomic
def depart(actor, project, membership):
    from tasks.models import Task
    from reminders.services import invalidate
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_membership(actor, project)
    target = Membership.objects.select_for_update().get(pk=membership.pk, project=project)
    if actor.pk != target.account_id:
        require_membership(actor, project, "owner")
    if project.owner_id == target.account_id:
        raise ValidationError("Transfer ownership to a manager before leaving.")
    if target.left_at:
        return
    for task in Task.objects.filter(assignee=target):
        invalidate(task)
        task.assignee = None
        task.assigned_at = None
        task.assignment_generation += 1
        task.version += 1
        task.save()
    GroupMembership.objects.filter(membership=target).delete()
    target.left_at = timezone.now()
    target.version += 1
    target.save()


@transaction.atomic
def delete_project(actor, project, confirmation, version):
    from django.db.models import Q
    from tasks.models import Task
    from reminders.models import OutboundMessage
    from .models import Invitation, Group
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_membership(actor, project, "owner")
    if project.version != version:
        raise Conflict("Project ownership changed. Reload before deleting.")
    if confirmation != project.name:
        raise ValidationError("Enter the project name exactly as shown above.")
    # Remove protected references in dependency order, under the same lock as delivery.
    resource_ids = [project.pk]
    for model in (Task, Invitation, Group, Membership):
        resource_ids.extend(model.objects.filter(project=project).values_list("pk", flat=True))
    OutboundMessage.objects.filter(Q(occurrence__task__project=project) | Q(invitation__project=project)).delete()
    Invitation.objects.filter(project=project).delete()
    Task.objects.filter(project=project).delete()
    MutationReceipt.objects.filter(resource_id__in=resource_ids).delete()
    project.delete()
