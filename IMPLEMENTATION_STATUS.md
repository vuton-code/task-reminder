# task-reminder handoff

Updated 2026-11-22. Local implementation is complete for automated verification; release
remains gated by live providers, physical devices and human trials.

## Start here

- Product authority: .specify/memory/constitution.md and specs/001-task-reminder/spec.md.
- Progress: specs/001-task-reminder/tasks.md.
- Evidence: tests/acceptance-map.md and artifacts/test-results.xml.
- Run instructions: specs/001-task-reminder/quickstart.md; deployment notes: ops/README.md.
- Modern Web Guidance: .agents/skills/modern-web-guidance/SKILL.md. Baseline: Widely available.
  Retrieve only relevant guides; avoid repeatedly rereading the whole repository.

## Implemented

Accounts/recovery/Google fixtures; project-scoped roles, invitation lifecycle, groups;
versioned tasks and filters; private reminder outbox with bounded transport, retry,
reconciliation and signed events; website polling/pagination; accessible responsive forms.
PostgreSQL integrity checks are scoped to affected records. Local restore and capacity
rehearsals pass. Chromium, Firefox and WebKit cover core journeys.

## Verification

Final integrated suite: 161 passed, including Modern Web Guidance changes, three browser
engines and an eight-page axe-core audit with no A/AA violations. Raw evidence is in artifacts/.
Fake email: 100/100 accepted in [0,60] seconds. Capacity: 50 visible tabs, 10,000 fixture tasks.
Production security configuration checks pass; no deployment occurred.
Never treat fake-provider, viewport or automated-typing samples as live/manual evidence.

## Pending external work

Google OAuth and Resend credentials; real sending/webhooks and Google return timing;
physical phones/home-screen/screen-reader checks; three-person task/invitation timing trials;
Linux ingress/container rehearsal and production backup scheduling.
No need to ask for credentials again until the user has them.

## Environment

Actual folder is task-reminder; old reminder-site cwd no longer exists.
Windows: .venv/Scripts/python.exe; local PostgreSQL 127.0.0.1:55432.
.env contains local secrets: never print it. Fake outbox is loopback development only.
Git initialized on main with origin https://github.com/vuton-code/task-reminder.git.
Public repository approved; initial local commit preparation in progress. No push or deployment.
Pilot migration authority and checklist: specs/002-online-migration/.


## UI pass after manual testing

Display name: Projects Management Hub (approved by user). Account name/email and initial avatar
are visible on mobile/desktop; project cards/navigation show the current role. Task creation
shows Assign to with permission-scoped choices. Reminder cards and polling show scheduled time,
timezone, assignee and latest assignment time. Historic unknown assignment times are labeled.
Invitation errors and local outbox acceptance wording are clearer.

Owner-only deletion is under People, with exact-name confirmation and CSRF-protected POST.
It removes related tasks, groups, memberships, invitations and project email records under the
same project lock used by delivery. It does not delete user accounts or other projects.
The local database was backed up to .runtime/before-ui-update.dump and migrated with
 tasks.0002_task_assigned_at. Website and worker were restarted; HTTP 200 and worker healthy.

User reported 19 core manual checks passed. Password reset invalidated both browsers and the
old password; reset-link reuse was not reported. See specs/001-task-reminder/ui-improvements.md.
Live Google/Resend, formal human timing, physical devices and deployment remain pending.

Verification: full run 171 passed with three new test-locator failures; corrected locator.
Refreshed-assets browser rerun: 14 passed with one Preferences touch-target audit failure.
After increasing the target, all four affected browser/accessibility checks passed (25s).
All 174 collected checks have now passed across the full run and focused reruns.
Evidence: artifacts/ui-regression.xml, ui-browser-regression.xml, ui-final-checks.xml;
artifacts/ui-desktop.png and ui-mobile.png visually reviewed. Django check clean; no migration drift.

Reminder display follow-up: versioned CSS/reminder-script URLs to refresh old browser assets. Due cards include assignee and task creation timestamp.
