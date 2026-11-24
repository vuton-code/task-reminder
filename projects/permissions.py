from django.core.exceptions import PermissionDenied
from .models import Membership

def require_membership(account, project, action="view"):
    if not account.is_authenticated:
        raise PermissionDenied
    member = Membership.objects.filter(project=project, account=account, left_at__isnull=True).first()
    if member is None:
        raise PermissionDenied
    if project.owner_id == account.pk or action == "view":
        return member
    if action == "invite" and member.role == "manager" and member.can_invite:
        return member
    if action == "assign" and member.role == "manager" and member.can_assign:
        return member
    raise PermissionDenied

def can_edit_task(account, task):
    member = require_membership(account, task.project)
    if task.assignee_id == member.pk:
        return member
    return require_membership(account, task.project, "assign")
