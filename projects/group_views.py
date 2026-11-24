from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from config.lookups import get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db import IntegrityError
from .models import Group
from .views import visible_project
from .permissions import require_membership
from .groups import save_group, delete_group

@login_required
@require_POST
def action(request, project_id, group_id, action):
    if action not in {"edit", "members", "delete"}:
        raise Http404
    project = visible_project(request, project_id)
    require_membership(request.user,project,"owner")
    group = get_object_or_404(Group,pk=group_id,project=project)
    try:
        version = int(request.POST.get("expected_version", request.POST.get("version","0")))
        if action=="delete":
            delete_group(request.user,group,version)
        else:
            members = request.POST.getlist("members") if action=="members" else list(group.members.values_list("pk",flat=True))
            name = request.POST.get("name",group.name) if action=="edit" else group.name
            save_group(request.user,project,name,members,group.pk,version)
    except (ValidationError,ValueError,IntegrityError) as exc:
        return render(request,"notice.html",{"title":"Group changed","notice":str(exc)},status=409)
    return redirect("groups", project_id=project.pk)
