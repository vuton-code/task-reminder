from django.urls import path
from django.shortcuts import redirect
from django.http import HttpResponse
from accounts import views as a, google_flow as google
from projects import views as p, group_views, transfer_view
from tasks import views as t, assignment
from reminders import views as r

urlpatterns = [
    path("", lambda request: redirect("projects")),
    path("health", lambda request: HttpResponse("ok")),
    path("accounts/register", a.register_view, name="register"),
    path("accounts/login", a.login_view, name="login"),
    path("accounts/logout", a.logout_view, name="logout"),
    path("accounts/recovery", a.recovery, name="recovery"),
    path("accounts/verify/<str:token>", a.proof_view, {"purpose": "verify"}, name="verify"),
    path("accounts/reset/<str:token>", a.proof_view, {"purpose": "reset"}, name="reset"),
    path("accounts/verification/resend", a.resend_verification, name="resend-verification"),
    path("accounts/preferences", a.preferences, name="preferences"),
    path("accounts/reauthenticate", a.reauthenticate, name="reauthenticate"),
    path("accounts/connections", google.connections, name="connections"),
    path("accounts/google/login/", google.begin, name="google-login"),
    path("accounts/google/login/callback/", google.callback, name="google-callback"),
    path("projects", p.project_list, name="projects"),
    path("projects/<uuid:project_id>/delete", p.delete_project, name="project-delete"),
    path("projects/<uuid:project_id>/tasks", t.task_list, name="task-list"),
    path("projects/<uuid:project_id>/tasks/<uuid:task_id>", t.detail, name="task-detail"),
    path("projects/<uuid:project_id>/tasks/<uuid:task_id>/complete", t.complete, name="task-complete"),
    path("projects/<uuid:project_id>/members", p.members, name="members"),
    path("projects/<uuid:project_id>/members/<uuid:member_id>/<str:action>", p.member_action, name="member-action"),
    path("projects/<uuid:project_id>/transfer", transfer_view.transfer),
    path("projects/<uuid:project_id>/leave", p.leave, name="leave"),
    path("projects/<uuid:project_id>/invitations/<uuid:invitation_id>/cancel", p.cancel_invitation, name="cancel-invitation"),
    path("projects/<uuid:project_id>/groups", p.group_list, name="groups"),
    path("invitations/<str:token>", p.invitation_preview, name="invitation"),
    path("projects/<uuid:project_id>/tasks/<uuid:task_id>/edit", t.detail),
    path("invitations/<str:token>/accept", p.invitation_preview),
    path("projects/<uuid:project_id>/invitations", p.members),
    path("projects/<uuid:project_id>/tasks/<uuid:task_id>/assign", assignment.assign),
    path("projects/<uuid:project_id>/groups/<uuid:group_id>/<str:action>", group_views.action),
    path("reminders", r.reminder_page, name="reminders"),
    path("reminders/due", r.due, name="due"),
    path("webhooks/resend", r.webhook, name="webhook"),
    path("dev/outbox", r.outbox, name="outbox"),
]


handler500 = "config.error_views.server_error"
