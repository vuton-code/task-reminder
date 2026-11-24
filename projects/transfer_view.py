from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from config.lookups import get_object_or_404
from .models import Membership
from .views import visible_project, member_action

@login_required
@require_POST
def transfer(request,project_id):
    project=visible_project(request,project_id)
    member=get_object_or_404(Membership,pk=request.POST.get("target_membership_id"),project=project,left_at=None)
    return member_action(request,project_id,member.pk,"transfer")
