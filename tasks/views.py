import uuid
from zoneinfo import ZoneInfo
from django.contrib import messages
from config.errors import Conflict
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from projects.models import Membership
from django.shortcuts import redirect, render
from config.lookups import get_object_or_404
from django.views.decorators.http import require_POST
from projects.views import visible_project
from projects.permissions import require_membership, can_edit_task
from .models import Task
from .forms import TaskForm
from .services import save_task, complete_task
from reminders.views import due_items

@login_required
def task_list(request, project_id):
    project = visible_project(request, project_id)
    member = require_membership(request.user, project)
    initial = {"assignee": member, "timezone": request.user.display_timezone, "mutation_key": uuid.uuid4()}
    form = TaskForm(request.POST or None, project=project, actor=request.user, initial=initial)
    conflict = False
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        data["assignee"] = data.get("assignee") or member
        try:
            save_task(request.user, project, data, key=data.pop("mutation_key"))
            messages.success(request, "Task saved with its current reminder time.")
            return redirect("task-list", project_id=project.pk)
        except ValidationError as exc:
            conflict = isinstance(exc, Conflict)
            form.add_error(None, exc)
    query = Task.objects.filter(project=project).select_related("assignee__account").order_by("-status", "-created_at")
    open_count = query.filter(status="open").count()
    if request.GET.get("status") in {"open", "completed"}:
        query = query.filter(status=request.GET["status"])
    if request.GET.get("assignee"):
        target = get_object_or_404(Membership, pk=request.GET["assignee"], project=project, left_at=None)
        query = query.filter(assignee=target)
    page = Paginator(query, 50).get_page(request.GET.get("page"))
    items = list(page.object_list)
    for task in items:
        task.can_edit = task.assignee_id == member.pk or project.owner_id == request.user.pk or member.can_assign
    return render(request, "tasks/list.html", {"project": project, "tasks": items, "form": form,
        "open_count": open_count, "page": page,
        "people": Membership.objects.filter(project=project,left_at=None).select_related("account"), "due_items": due_items(request.user)},
        status=409 if conflict else 422 if form.errors else 200)

@login_required
def detail(request, project_id, task_id):
    project = visible_project(request, project_id)
    task = get_object_or_404(Task, pk=task_id, project=project)
    if request.method == "POST":
        can_edit_task(request.user, task)
    initial = {"title": task.title, "description": task.description, "assignee": task.assignee,
        "timezone": request.user.display_timezone, "version": task.version,
        "reminder_at": task.reminder_at.astimezone(ZoneInfo(request.user.display_timezone)).strftime("%Y-%m-%dT%H:%M") if task.reminder_at else ""}
    form = TaskForm(request.POST or None, initial=initial, project=project, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            save_task(request.user, project, form.cleaned_data, task.pk, form.cleaned_data["version"])
            return redirect("task-list", project_id=project.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    member = require_membership(request.user, project)
    editable = task.assignee_id == member.pk or project.owner_id == request.user.pk or member.can_assign
    return render(request, "tasks/detail.html", {"project": project, "task": task, "form": form, "editable": editable}, status=409 if form.errors else 200)

@login_required
@require_POST
def complete(request, project_id, task_id):
    project = visible_project(request, project_id)
    task = get_object_or_404(Task, pk=task_id, project=project)
    try:
        complete_task(request.user, task, int(request.POST.get("expected_version", request.POST.get("version", "0"))))
    except (ValidationError, ValueError):
        return render(request, "notice.html", {"title": "Task changed", "notice": "Reload the task before completing it."}, status=409)
    return redirect("task-list", project_id=project.pk)
