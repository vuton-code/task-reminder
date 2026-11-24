import uuid
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import redirect, render
from config.lookups import get_object_or_404
from django.views.decorators.http import require_POST
from .models import Project, Membership, Invitation, Group
from .permissions import require_membership
from .forms import ProjectForm, InvitationForm
from . import services, invitations, groups
from accounts.services import digest
from config.errors import Conflict

def visible_project(request, project_id):
    return get_object_or_404(Project, pk=project_id, memberships__account=request.user, memberships__left_at__isnull=True)

@login_required
def project_list(request):
    form = ProjectForm(request.POST or None, initial={"mutation_key": uuid.uuid4()})
    if request.method == "POST" and form.is_valid():
        try:
            project = services.create_project(request.user, form.cleaned_data["name"], form.cleaned_data["mutation_key"])
            return redirect("task-list", project_id=project.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "projects/list.html", {"form": form}, status=422 if form.errors else 200)

@login_required
def members(request, project_id):
    project = visible_project(request, project_id)
    member = require_membership(request.user, project)
    owner = request.user.pk == project.owner_id
    form = InvitationForm(request.POST or None, initial={"mutation_key": uuid.uuid4()})
    if request.method == "POST" and form.is_valid():
        try:
            invitations.invite(request.user, project, form.cleaned_data["email"], form.cleaned_data["mutation_key"])
            return redirect("members", project_id=project.pk)
        except (ValidationError, IntegrityError):
            form.add_error(None, "Unable to invite this address. Check whether they are already a member.")
    people = Membership.objects.filter(project=project, left_at__isnull=True).select_related("account")
    selected_group = request.GET.get("group", request.GET.get("group_id"))
    if selected_group:
        get_object_or_404(Group, pk=selected_group, project=project)
        people = people.filter(groupmembership__group__id=selected_group, groupmembership__group__project=project)
    pending = Invitation.objects.filter(project=project, status__in=["prepared", "pending"])
    if not owner:
        pending = pending.filter(inviter=request.user) if member.can_invite else pending.none()
    return render(request, "projects/members.html", {"project": project, "people": people, "form": form,
        "is_owner": owner, "can_invite": owner or member.can_invite, "pending": pending,
        "groups": Group.objects.filter(project=project), "my_membership": member})

@login_required
@require_POST
def member_action(request, project_id, member_id, action):
    project = visible_project(request, project_id)
    member = get_object_or_404(Membership, pk=member_id, project=project)
    try:
        if action == "role":
            services.change_role(request.user, project, member, request.POST.get("role"),
                request.POST.get("can_invite") == "on", request.POST.get("can_assign") == "on", int(request.POST.get("expected_version", request.POST.get("version", "0"))))
        elif action == "remove":
            services.depart(request.user, project, member)
        elif action == "transfer":
            services.transfer(request.user, project, member.pk, int(request.POST.get("expected_version", request.POST.get("version", "0"))))
        else:
            raise Http404
    except (ValidationError, ValueError, KeyError, Membership.DoesNotExist) as exc:
        return render(request, "notice.html", {"title": "Change could not be saved", "notice": str(exc)}, status=409)
    return redirect("members", project_id=project.pk)

@login_required
@require_POST
def leave(request, project_id):
    project = visible_project(request, project_id)
    try:
        services.depart(request.user, project, require_membership(request.user, project))
    except ValidationError as exc:
        return render(request, "notice.html", {"title": "Transfer ownership first", "notice": str(exc)}, status=409)
    return redirect("projects")

@login_required
@require_POST
def cancel_invitation(request, project_id, invitation_id):
    project = visible_project(request, project_id)
    invitation = get_object_or_404(Invitation, pk=invitation_id, project=project)
    invitations.cancel(request.user, invitation)
    return redirect("members", project_id=project.pk)

def invitation_preview(request, token):
    invitation = get_object_or_404(Invitation.objects.select_related("project", "inviter"), token_digest=digest(token))
    error = None
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login?next=/invitations/{token}")
        try:
            member = invitations.accept(request.user, token)
            return redirect("task-list", project_id=member.project_id)
        except ValidationError as exc:
            error = " ".join(exc.messages)
    return render(request, "projects/invitation.html", {"invitation": invitation, "error": error}, status=409 if error else 200)

@login_required
def group_list(request, project_id):
    project = visible_project(request, project_id)
    error = None
    if request.method == "POST":
        try:
            group_id = request.POST.get("group_id") or None
            if request.POST.get("action") == "delete":
                groups.delete_group(request.user, get_object_or_404(Group, pk=group_id, project=project), int(request.POST.get("expected_version", request.POST.get("version", "0"))))
            else:
                groups.save_group(request.user, project, request.POST.get("name", ""), request.POST.getlist("members"),
                    group_id, int(request.POST.get("expected_version", request.POST.get("version", "0"))) if group_id else None)
            return redirect("groups", project_id=project.pk)
        except (ValidationError, IntegrityError, ValueError, KeyError):
            error = "Unable to save. Check the group name, current members, and version."
    return render(request, "projects/groups.html", {"project": project, "error": error,
        "groups": Group.objects.filter(project=project).prefetch_related("members__account"),
        "people": Membership.objects.filter(project=project, left_at__isnull=True).select_related("account"),
        "is_owner": project.owner_id == request.user.pk})


@login_required
def delete_project(request, project_id):
    from django.contrib import messages
    from .forms import DeleteProjectForm
    project = visible_project(request, project_id)
    require_membership(request.user, project, "owner")
    form = DeleteProjectForm(request.POST or None, project=project, initial={"version": project.version})
    if request.method == "POST" and form.is_valid():
        try:
            services.delete_project(request.user, project, form.cleaned_data["confirmation"], form.cleaned_data["version"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Project deleted. Its pending reminders have been canceled.")
            return redirect("projects")
    return render(request, "projects/delete.html", {"project": project, "form": form}, status=409 if form.errors else 200)
