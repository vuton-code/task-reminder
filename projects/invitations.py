import secrets
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.services import digest, normalize_email
from .models import Project, Membership, Invitation
from .permissions import require_membership
from .services import receipt, record

@transaction.atomic
def invite(actor, project, email, key=None):
    from reminders.services import enqueue
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_membership(actor, project, "invite")
    email = normalize_email(email)
    if Membership.objects.filter(project=project, account__email__iexact=email, left_at__isnull=True).exists():
        raise ValidationError("This person already belongs to the project.")
    previous, fingerprint = receipt(actor, f"invite-{project.pk}", key, {"email": email})
    if previous:
        return Invitation.objects.get(pk=previous.resource_id)
    token = secrets.token_urlsafe(32)
    invitation = Invitation(project=project, inviter=actor, recipient_email=email, token_digest=digest(token))
    invitation.full_clean(exclude=["sent_at", "expires_at", "accepted_membership"])
    invitation.save()
    enqueue("invitation", email, {"subject": "Project invitation",
        "text": f"{actor.username} invited you to {project.name}.\n\n{settings.APP_BASE_URL}/invitations/{token}"},
        invitation=invitation)
    record(actor, f"invite-{project.pk}", key, fingerprint, invitation)
    return invitation

@transaction.atomic
def accept(actor, token):
    invitation = Invitation.objects.get(token_digest=digest(token))
    Project.objects.select_for_update().get(pk=invitation.project_id)
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    from accounts.models import Account
    actor = Account.objects.select_for_update().get(pk=actor.pk)
    if not actor.is_active or not actor.email_verified_at or normalize_email(actor.email) != invitation.recipient_email:
        raise PermissionDenied("Sign in with the verified invited email.")
    if invitation.status == "accepted":
        if invitation.accepted_membership and invitation.accepted_membership.left_at is None:
            return invitation.accepted_membership
        raise ValidationError("You need a new invitation. You no longer belong to this project. Ask the owner or a manager with invitation permission to invite you again.")
    if invitation.status != "pending" or not invitation.expires_at or timezone.now() >= invitation.expires_at:
        raise ValidationError("This invitation has expired or been canceled. Ask the owner or a manager with invitation permission for a new invitation.")
    member, _ = Membership.objects.get_or_create(project=invitation.project, account=actor,
        left_at=None, defaults={"role": "member"})
    invitation.status = "accepted"
    invitation.accepted_membership = member
    invitation.save()
    return member

@transaction.atomic
def cancel(actor, invitation):
    from reminders.models import OutboundMessage
    project = Project.objects.select_for_update().get(pk=invitation.project_id)
    require_membership(actor, project, "invite")
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if actor.pk != project.owner_id and actor.pk != invitation.inviter_id:
        raise PermissionDenied
    if invitation.status in ["prepared", "pending"]:
        invitation.status = "cancelled"
        invitation.save()
        OutboundMessage.objects.filter(invitation=invitation, state__in=["pending", "retry"]).update(state="suppressed")
