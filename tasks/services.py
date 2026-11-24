from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from projects.models import Project, Membership
from projects.permissions import require_membership, can_edit_task
from projects.services import receipt, record
from config.errors import Conflict
from .models import Task

@transaction.atomic
def save_task(actor, project, data, task_id=None, version=None, key=None):
    from reminders.services import invalidate
    project = Project.objects.select_for_update().get(pk=project.pk)
    member = require_membership(actor, project)
    previous, fingerprint = receipt(actor, f"create-task-{project.pk}", key, data) if not task_id else (None, None)
    if previous:
        return Task.objects.get(pk=previous.resource_id, project=project)
    task = Task.objects.get(pk=task_id, project=project) if task_id else Task(project=project, assignee=member)
    if task_id:
        can_edit_task(actor, task)
        if task.version != version:
            raise Conflict("Someone changed this task. Reload before saving.")
    target = data.get("assignee", task.assignee)
    if target != task.assignee:
        require_membership(actor, project, "assign")
    if target and not Membership.objects.filter(pk=target.pk, project=project, left_at__isnull=True).exists():
        raise ValidationError("Choose a current project member.")
    schedule = data.get("reminder_at", task.reminder_at)
    if task_id:
        invalidate(task)
        task.version += 1
        task.schedule_generation += schedule != task.reminder_at
        task.assignment_generation += target != task.assignee
    task.title = data.get("title", task.title).strip()
    task.description = data.get("description", task.description)
    task.reminder_at = schedule
    if not task_id or target != task.assignee:
        task.assigned_at = timezone.now() if target else None
    task.assignee = target
    task.full_clean()
    task.save()
    if not task_id:
        task.created_by = actor
        task.save(update_fields=["created_by"])
        record(actor, f"create-task-{project.pk}", key, fingerprint, task)
    return task

@transaction.atomic
def complete_task(actor, task, version):
    from reminders.services import invalidate
    Project.objects.select_for_update().get(pk=task.project_id)
    task = Task.objects.get(pk=task.pk)
    can_edit_task(actor, task)
    if task.version != version:
        raise Conflict("Someone changed this task. Reload before completing.")
    task.status = "completed"
    task.version += 1
    task.save()
    invalidate(task)
