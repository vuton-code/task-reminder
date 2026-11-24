from .models import Membership


def navigation(request):
    if not request.user.is_authenticated:
        return {}
    from reminders.views import due_items
    projects = []
    for membership in Membership.objects.filter(account=request.user, left_at=None).select_related("project").order_by("project__name"):
        project = membership.project
        project.current_role = "Owner" if project.owner_id == request.user.pk else membership.get_role_display()
        projects.append(project)
    return {"navigation_projects": projects, "due_items": due_items(request.user)}
