from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from config.lookups import get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from projects.models import Membership
from projects.views import visible_project
from projects.permissions import require_membership
from .services import save_task

@login_required
@require_POST
def assign(request, project_id, task_id):
    project = visible_project(request, project_id)
    require_membership(request.user, project, "assign")
    target = get_object_or_404(Membership, pk=request.POST.get("assignee_membership_id"), project=project, left_at=None)
    try:
        version = int(request.POST.get("expected_version", request.POST.get("version", "0")))
        save_task(request.user, project, {"assignee":target}, task_id, version)
    except (ValidationError, ValueError) as exc:
        return render(request, "notice.html", {"title":"Unable to assign task","notice":str(exc)}, status=409)
    return redirect("task-list", project_id=project.pk)
