from django.core.exceptions import ValidationError
from django.db import transaction
from config.errors import Conflict
from .models import Project, Group, GroupMembership, Membership
from .permissions import require_membership

@transaction.atomic
def save_group(actor, project, name, member_ids, group_id=None, version=None):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_membership(actor, project, "owner")
    name = name.strip()
    if not name or len(name) > 80:
        raise ValidationError("Use a group name between 1 and 80 characters.")
    members = list(Membership.objects.filter(project=project, left_at__isnull=True, pk__in=member_ids))
    if len(members) != len(set(map(str, member_ids))):
        raise ValidationError("Choose current members of this project.")
    group = Group.objects.get(pk=group_id, project=project) if group_id else Group(project=project)
    if group_id and group.version != version:
        raise Conflict("Group changed. Reload and try again.")
    group.name = name
    group.version += bool(group_id)
    group.full_clean()
    group.save()
    GroupMembership.objects.filter(group=group).delete()
    GroupMembership.objects.bulk_create([GroupMembership(group=group, membership=m) for m in members])
    return group

@transaction.atomic
def delete_group(actor, group, version):
    project = Project.objects.select_for_update().get(pk=group.project_id)
    require_membership(actor, project, "owner")
    group.refresh_from_db()
    if group.version != version:
        raise Conflict("Group changed. Reload and try again.")
    group.delete()
