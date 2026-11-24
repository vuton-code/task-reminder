# Migration specification: GitHub + Supabase pilot

Date: 2026-11-22
Updated: 2026-11-23
Status: Draft migration specification; website-only reminders, Google-only sign-in and draft-and-copy invitations approved for the pilot.
Product: Projects Management Hub (repository identity: task-reminder).

## Objective and authority
Build a working online pilot using GitHub Pages for static website hosting and Supabase for
backend services and PostgreSQL. Preserve the working local Django application throughout.
This is a migration, not a direct Django deployment to Pages. No application changes, remote
resources, purchases or publication are authorized by this document alone.

The approved constitution remains at ../../.specify/memory/constitution.md. Product rules and
verification conditions are inherited from ../001-task-reminder/spec.md, with the latest UI
changes in ../001-task-reminder/ui-improvements.md. This document records explicitly approved
pilot exceptions: email task reminders and local password sign-in/recovery are deferred; invitation
email drafts are shared manually and expire seven days after creation. It does not amend the constitution or claim
that the full product's email requirements have passed. A later full release must implement
those requirements or receive a separately approved constitutional amendment.

## Approved decisions
- Use GitHub and Supabase for the online version; no Render or Koyeb migration selected.
- Target free tiers for the current pilot, subject to quotas and platform suitability.
- Confirmed 2026-11-23: personal use and a small group of testers; no paid access or commercial use.
- Keep the frontend portable to Render for a future commercial phase, retaining Supabase.
- Google-only sign-in: no website username/password registration or password-reset flow for the pilot.
  Google establishes verified identity; users recover Google access through Google.
- Generate invitation email drafts with Copy email and Copy link buttons; the inviter sends them
  manually from their own email app. No application email-delivery service is required for this scope.
- Show due reminders when a user signs in or returns while already signed in.
- Automatically show newly due reminders while the website is open in an active, connected tab.
- Defer email task reminders for this pilot. Do not create email reminder jobs or present an
  enabled email-reminder setting as if delivery were available.
- No SMS, closed-site push, native app, offline editing or recurring reminders are added.

## Website-reminder requirements and acceptance criteria
| ID | Rule | Concrete verification |
| --- | --- | --- |
| WR-01 | Only the current assignee with active project membership sees a task in My reminders. Other project members can still see the task in the project. | Use owner, manager, member and outsider accounts; test direct API requests and the UI. |
| WR-02 | A reminder becomes due at its stored instant, never early. Scheduling uses authoritative server time; date display uses the user's timezone. | Test future/due boundaries, incorrect client clocks and daylight-saving transitions. |
| WR-03 | Due reminders appear automatically in an active, connected tab without manual reload. | At least 99/100 scheduled reminders appear within 0–10 seconds inclusive; early, late and missing results fail. |
| WR-04 | Opening the website while signed in or completing Google sign-in shows current due reminders. | At least 99/100 connected visits show the correct set within five seconds. Include empty, completed and departed-project cases. |
| WR-05 | Completing a task removes its active reminder; rescheduling replaces the old schedule. | Complete before/after due time, reschedule into the future, and verify across open sessions. |
| WR-06 | Reassignment moves reminder eligibility to the new assignee. Leaving, removal and project deletion revoke access and remove its reminders. | Test changes before and after due time, using previously opened tabs and direct API calls. No stale reminder survives successful reconciliation. |
| WR-07 | Repeated polls, refreshes and reconnects do not duplicate a reminder. | Retry requests and reconnect multiple tabs; one active entry per current task occurrence. |
| WR-08 | Hidden/offline tabs catch up when active connectivity returns. No promise is made about notification arrival while the browser is closed or suspended. | Close/reopen, background/resume and disconnect/reconnect; distinguish these samples from active-tab timing. |
| WR-09 | Reminders persist until completion, schedule/assignment changes or loss of access; opening a link alone does not dismiss them. | Open task and return; verify current state and permissions again. |
| WR-10 | Reminder cards show due time, creation time and Assigned by with the original creator when known. Reassignment does not change creator or creation time. | Compare initial render and refreshed data; keep timezone abbreviations, omit unknown assignment time and standalone IANA timezone line. |
| WR-11 | Signed-out or revoked sessions cannot fetch reminder data. Previously rendered content is cleared on detected revocation; disconnected displays indicate stale data. | Replay requests from ended sessions and test failed refreshes, without treating client hiding as authorization. |
| WR-12 | Email task reminders are unavailable in the pilot. | Confirm UI has no misleading enabled email option, no scheduled email dispatch jobs and no task email sends. Existing local email configuration remains unchanged. |

Use the original per-device sampling conditions and retain failures; no automated test or local
Django result substitutes for evidence from the migrated pilot. Google-return timing remains
99/100 within five seconds after provider return; Google is the pilot sign-in method. The user skipped the extra
manual creator-after-reassignment test; do not record it as passed.

## Google-only identity: acceptance criteria
| ID | Rule | Verification |
| --- | --- | --- |
| GA-01 | Continue with Google creates or returns to one application profile per Google identity without asking for a local password or username. | First and repeat sign-in, concurrent callbacks and multiple-project access create no duplicate profiles. |
| GA-02 | Project creation and invitation acceptance require a provider-verified email. No email verification state supplied by the browser is trusted. | Reject unverified or mismatched identities and tampered callback results; grant no project access. |
| GA-03 | Sign-out immediately revokes the current application session; other devices can remain signed in. | Replay the ended session against APIs and compare with a second active session. |
| GA-04 | Recovery directs users to Google; no local password-reset, magic-link or password-registration endpoint is enabled. | Inspect UI and direct endpoints; failed/canceled Google sign-in permits a fresh attempt without creating membership. |
| GA-05 | Identity and project authority remain separate. | An authenticated outsider and a manager of another project cannot read or modify unauthorized project data. |

## Draft-and-copy invitations: acceptance criteria
Only the owner and managers with invitation permission may create an invitation for a specified
Google account email. The website generates a draft automatically; it does not send email.

Draft example (values are safely rendered as text):

To: [invited email]
Subject: You're invited to join [Project name]

[Inviter name] invited you to join [Project name].
Open [invitation link], sign in with the Google account for [invited email], and accept to join.
This invitation expires on [explicit date, time and timezone].

| ID | Rule | Verification |
| --- | --- | --- |
| IN-01 | Show recipient, subject, message and link after authorized creation. Copy email copies the subject and complete message; Copy link copies only the URL. Recipient remains visible/selectable. | Paste each button's output into a plain-text editor and compare with the displayed draft, including line breaks, intended address and expiry. |
| IN-02 | Show a copied confirmation only after clipboard success. Provide selectable text and a clear fallback if copying is unavailable. Never report email sent. | Test success, clipboard denial and keyboard/mobile copying; verify no outbound application email is sent. |
| IN-03 | Expire exactly seven days after server-recorded creation. Copying, reopening or manually sending the draft does not extend validity. | Test just before, at and after expiry, repeated copies and delayed manual sending. Fresh invitations get new tokens and creation times. |
| IN-04 | Acceptance requires sign-in with the matching verified Google email and an explicit Accept invitation action. Forwarding grants no access to a different account. | Match/mismatch, unauthenticated and unverified cases; preview exposes only project name and inviter, not task/member data. |
| IN-05 | Membership begins on valid acceptance as a regular member. Existing accounts retain other memberships. | Accept using an existing Google account; retries do not duplicate membership or restore removed membership. |
| IN-06 | Owners cancel any pending invitation; authorized managers cancel only their own. Cancellation is immediate. | Cancel before acceptance and race acceptance/cancellation; previously copied links fail once cancellation commits. |
| IN-07 | Invitation creation/retry is permission-checked and does not silently duplicate invitations. Tokens are unguessable and excluded from public lists/logs. | Direct unauthorized requests, repeated submissions and token exposure checks. Credential storage and authorized draft retrieval belong in the technical plan. |

The acceptance timing target remains 9/10 within 15 seconds for recipients already signed in with
the correct verified account. Draft creation/copying/manual sending is a separate workflow, not
part of that timing sample. Local Django invitation delivery stays unchanged.

## Other feature parity
- Accounts: Google-only verified identity for the pilot; preserve immediate current-session sign-out
  and separate project authorization. Local password features remain deferred, not passed.
- Projects: independent membership, one owner, independently delegated invitation/assignment
  permissions, owner-only role changes, removal and transfer to an existing manager.
- Invitations: recipient's verified email only; acceptance creates regular membership; seven-day
  expiry from creation for this pilot, immediate cancellation, no forwarded/replayed access after removal.
- Groups: owner-managed collections within one project; no permission changes.
- Tasks: all members view project tasks; members create for themselves/edit assigned tasks;
  owners and authorized managers assign others. Preserve version-conflict and retry protection.
- Project deletion: owner-only explicit confirmation, removal of project data/access, no impact
  on other projects or accounts; preserve current UI behavior.
- UI: Projects Management Hub without subtitle, visible account identity, project role labels,
  permitted assignment choices and readable invitation errors; mobile and keyboard accessibility.
Task entry remains 9/10 within 20 seconds; invitation acceptance 9/10 within 15 seconds under
the original conditions. Every project-isolation check must pass.

## Backend and deployment boundaries
The browser receives static code and public Supabase configuration only. Secrets, service-role
keys, local backups, real user data and the development outbox must never enter GitHub Pages.
Enforce current project authorization with Row Level Security and atomic server-side operations.
Test raw table writes, RPCs, views and subscriptions, including attempts to forge owner, creator,
role, membership or verification fields. Browser UI restrictions are not security controls.
Keep tokens and invitation secrets protected; no public profile-to-email lookup.

Website-only reminders do not need a continuous email worker or scheduled email function.
Use authorized due queries and periodic refresh/reconciliation; Realtime is optional acceleration,
not the only recovery mechanism. Exact schema, polling interval, frontend framework and routing
are technical-plan decisions. Support repository subpaths, direct links and OAuth callbacks.

## Open decisions and feasibility gates
1. Personal/noncommercial tester use is confirmed. Validate the final Pages deployment against
   platform constraints; move hosting before commercial use. Google credentials are entered only at Google.
2. Configure Google OAuth and exact callback/redirect allowlists. Verify provider identity, email
   verification and immediate server-side session revocation. No silent migration or identity merge
   with existing Django users based only on matching email; imported accounts need a reviewed mapping.
3. Choose fresh pilot accounts/data (recommended) or an explicitly approved data migration.
   Do not import local passwords into the Google-only pilot. Preserve unknown historic creators.
4. Confirm repository visibility, project region, free-tier quotas and restore procedures. Free
   Supabase inactivity pausing is a pilot limitation, not proof that reminder targets are met.
The previous email-delivery decision is resolved for this pilot: Google handles identity/recovery,
invitation drafts are sent by the inviter, and task reminders are website-only. No hosted application
email sender is needed for these approved flows. No remaining gate is marked complete here.

## Staged checklist
- [x] Approve website-only pilot reminders, including automatic updates while open.
- [x] Record migration scope and acceptance criteria in this draft.
- [x] Approve Google-only sign-in and Google-managed account recovery for the pilot.
- [x] Approve invitation email drafts with Copy email and Copy link; manual sending.
- [x] Confirm personal/noncommercial use and future Render portability.
- [ ] Confirm repository visibility, region and staging-data decisions.
- [x] Prepare the technical plan from the approved pilot decisions.
- [ ] Review remaining technical feasibility checks before implementation/deployment.
- [ ] Prepare sanitized GitHub repository and isolated Supabase staging configuration.
- [ ] Implement and test identity, session revocation and project isolation first.
- [ ] Migrate projects, invitations, groups, tasks and owner-only deletion.
- [ ] Migrate website reminders and latest UI refinements.
- [ ] Verify desktop/mobile accessibility, direct API security, timings and rollback.
- [ ] Review the working pilot, then publish with its approved limitations documented.
Email-task-reminder implementation and provider-acceptance testing stay deferred, not passed.

## Data protection and rollback
Keep the local app and database intact; no production export or remote migration in this stage.
Prepare a separate test dataset. If migration is requested later, map identities explicitly, check
counts and relationships, retain original timestamps, and prevent duplicate senders.
Version schema and frontend artifacts together. Demonstrate export/restore in isolation and plan
for writes made online; restoring an old frontend alone cannot roll back database changes.

## Evidence and sources
Documentation-only change; no new application tests or deployment claimed.
Platform references reviewed in this conversation on 2026-11-22:
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://supabase.com/pricing
- https://supabase.com/docs/guides/auth/auth-smtp
- https://supabase.com/docs/guides/auth/sessions
- https://supabase.com/docs/guides/auth/auth-identity-linking
