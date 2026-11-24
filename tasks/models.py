import uuid
from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator

class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE)
    title = models.CharField(max_length=200, validators=[MinLengthValidator(1)])
    description = models.TextField(blank=True, validators=[MaxLengthValidator(10000)])
    assignee = models.ForeignKey("projects.Membership", null=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, default="open", choices=[("open", "Open"), ("completed", "Completed")])
    reminder_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    schedule_generation = models.PositiveIntegerField(default=1)
    assignment_generation = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey("accounts.Account", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_tasks")
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["assignee", "reminder_at"]),
        ]
        constraints = [models.CheckConstraint(condition=models.Q(status__in=["open", "completed"]), name="valid_task_status")]
