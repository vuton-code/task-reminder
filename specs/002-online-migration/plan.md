# Technical plan — GitHub + Supabase pilot

Date: 2026-11-23
Status: Ready for implementation task breakdown; deployment and live validation pending.
Authority: [pilot specification](spec.md), constitution v1.0.0 and inherited feature rules.
This plan applies the user's approved pilot exceptions; it does not change the constitution.
Noncommercial tester use is confirmed. No application code or remote environment changes in this step.

## 1. Architecture and portability

Use a Vite + TypeScript + React static frontend, Supabase JavaScript client, Supabase Auth
(Google only), and PostgreSQL with Row Level Security (RLS) and transactional RPC functions.
Pin supported stable dependency versions and commit a lockfile during implementation. Reuse the
current visual design, CSS, fonts and workflow copy; Django templates/services are reference
behavior, not browser code. Use native accessible controls and apply Modern Web Guidance when
implementing UI. JavaScript is required for the pilot: show a clear no-JavaScript message rather
than a broken form. This explicitly replaces Django's server-rendered navigation architecture.

Browser -> GitHub Pages static assets
Browser -> Supabase Auth -> Google -> Supabase callback -> browser PKCE callback
Browser -> Supabase Data API -> RLS reads / transactional RPC mutations

No Edge Function, Cron job, Realtime dependency or persistent worker is needed for website-only
reminders. Add server functions only if the authentication feasibility checks require them; do
not ship privileged browser code as a shortcut. GitHub Actions builds/tests/deploys, never schedules
reminders. Retain the local Django app and database untouched in parallel.

Host-independent frontend layout:
- web/: source, public assets, tests, package manifest/lockfile and Vite configuration.
- supabase/: local configuration, numbered SQL migrations, synthetic seed data and SQL tests.
- specs/002-online-migration/: specification, plan, later task list and verification evidence.
- .github/workflows/: scoped CI and Pages deployment workflows, added only at implementation.

Build once with npm ci and npm run build; publish only web/dist. Use a configurable BASE_PATH
for /repository/ on Pages and / on Render, plus PUBLIC_APP_URL, SUPABASE_URL and publishable key.
These values are public. No secret or service-role key may use a frontend build variable.
All hosting differences live in configuration/workflows, not domain components.

## 2. Routing and authentication

Use hash routes (/#/projects, /#/projects/:id/tasks, /#/invite/:token) so direct links and reloads
work on Pages without a custom 404 redirect. The root document handles the OAuth ?code= callback
before dispatching hash routes. Use Supabase's PKCE flow and official client library. Configure
Google's callback to Supabase; allowlist exact local/Pages return URLs in Supabase. Avoid wildcard
production redirects. Remove callback codes from the address after exchange.

Before login, keep only the validated relative return route/invitation token in sessionStorage;
never store an arbitrary redirect destination. Resume the invitation preview after authentication,
then require explicit acceptance. Keep callback processing idempotent. Use only basic Google
identity scopes, not Gmail access. Configure Google test audience and approved testers as needed.

Disable password/email, anonymous and other providers for the hosted pilot. There is no local
registration, magic-link, password-reset or identity-linking screen. Recovery directs to Google.
Provision one profile per auth user id transactionally on first valid Google session. Do not import
Django users or merge them by email. Fresh synthetic pilot accounts are the planning default,
subject to confirmation before remote setup.

Authoritative identity checks use the authenticated UUID plus server-owned Google identity and
verified email records; never trust editable user_metadata or client-supplied verified flags.
Technical spike must prove which managed Auth fields retain provider verification and reject
unverified/changed email, missing Google identity and spoofed profile fields. If that cannot be
proven with documented behavior, stop identity implementation and resolve it explicitly.

Immediate sign-out: use signOut({scope: 'local'}), clear application caches, and reject old tokens
on the server. A private, narrowly scoped SECURITY DEFINER helper checks that JWT session_id
belongs to auth.uid() and still exists in auth.sessions. Every exposed read policy and mutation
uses this check. Lock down helper ownership, search_path and execution grants; expose no session
rows. Test captured JWT replay after logout, including a separate still-valid session. Supabase
refresh-token revocation alone is insufficient. Show a retryable error if server logout fails;
do not falsely claim that remote access ended. Auth table dependencies require integration tests
against managed staging and an upgrade check.

## 3. Data model

All timestamps are timestamptz in UTC; all resource IDs are UUIDs. Use server defaults.

| Entity | Main fields and invariants |
| --- | --- |
| profiles | auth user id, display name, display timezone; no client-controlled verified email/role |
| projects | id, name, owner user id, version, created_at; exactly one active owner membership |
| memberships | id, project/user ids, member/manager role, can_invite, can_assign, joined_at, left_at, version; unique active project/user |
| groups / group_memberships | project-scoped names and active memberships; no permission effect |
| tasks | project, title, description, active assignee membership or null, status, reminder_at, immutable created_by/created_at, assigned_at, version, schedule/assignment generations |
| invitations (private) | project, inviter, normalized recipient email, token digest/encrypted token, created_at, expires_at, pending/accepted/cancelled, accepted membership |
| mutation_receipts (private) | actor, operation, idempotency key, payload hash, result id; conflicting replay rejected |

Keep verified email in Auth-owned data; project-member contact display, if needed, goes through a
scoped RPC, never a publicly readable email directory. Invitation secrets and receipts live in a
non-exposed schema. Store only necessary profile information. Index active membership lookups,
project/status tasks and assignee/reminder_at queries. No general email outbox in this pilot.

## 4. Authorization and transactional API

Default-deny RLS on every exposed application table, including tables added later. Authenticated
users may SELECT only their own preferences/profile and authorized project resources. Provide
minimal member display records via scoped reads. No generic INSERT/UPDATE/DELETE privileges on
domain tables: mutations use reviewed RPCs. Views must not bypass policies. Realtime is disabled
for these tables initially to reduce the access surface.

RPC families:
- bootstrap_profile, update_preferences, list_projects/list_members, get_due_reminders.
- create_project, change_member_role, remove_member, leave_project, transfer_ownership, delete_project.
- create/update/delete_group and membership edits.
- save_task, assign_task, complete_task.
- create_invitation, get_invitation_draft, preview_invitation, accept_invitation, cancel_invitation.

Each mutation derives actor from auth.uid(), verifies live session and current project permission,
locks the project row, validates all target IDs belong to it, checks expected versions, applies
changes atomically and increments versions. Use fixed project-then-resource lock order. Privileged
RPCs must implement checks internally even if their owner bypasses RLS; no arbitrary dynamic SQL.
Revoke default PUBLIC/anon execution except the deliberately narrow preview endpoint. Anonymous
preview returns project name/inviter only from a valid opaque token; never member/task data.

Recheck role grants on every request. Group membership never authorizes task access. Creation
sets creator from the actor; edits/reassignment cannot alter creator or created_at. Departure
sets tasks unassigned and removes group memberships. Transfer requires an active manager and
retains the previous owner as manager with both delegated permissions. Project deletion requires
current owner, matching name/version and removes dependent records while retaining accounts and
other projects. Idempotent retries never resurrect deleted resources or removed memberships.

## 5. Invitations without an email service

Creation generates a cryptographically random 256-bit token on the server, stores its SHA-256
lookup digest and an encrypted copy for authorized draft retrieval. Keep the encryption key in
Supabase Vault/private server configuration, never in migrations, logs or browser configuration.
The create RPC returns the token only to the authorized inviter. get_invitation_draft checks that
caller is current owner or the original inviter still holding invitation permission; decrypt only
an eligible pending invitation. Manage key rotation separately; no silent token invalidation.
Use a reviewed pgcrypto/Vault approach and test secret isolation before deploying it.

Expiration is created_at + seven days, compared with database time. A new submission uses a
mutation key; retries return the same invitation/draft rather than duplicate it. Copying doesn't
change expiry. Display subject, recipient, complete message, URL and explicit expiration timezone.
Copy email copies subject + message; Copy link copies only URL. Use Clipboard API on a user gesture,
await success before announcing Copied, and retain selectable text for denied/unavailable clipboard.
Never label a draft Sent. Render all names/text safely as text, not arbitrary HTML.

Fragments keep invite tokens out of hosting request paths; no analytics or external assets on
invitation screens. Do not log RPC bodies containing tokens. Preview/accept invalid tokens with
nonrevealing errors. Bound payload sizes and attempt rates; review an Edge Function rate limiter
if direct RPC exposure proves insufficient, without weakening recipient verification.
Accept locks project/invitation, checks live verified Google email, expiry and cancellation, then
creates one regular membership. An accepted invitation may return its still-active membership;
it cannot create a new one after removal. Existing pending invites remain valid if their inviter
later loses permission, per the original specification, unless canceled or the project is deleted.

## 6. Website reminders and time handling

get_due_reminders derives the current user and returns authorized incomplete tasks with a
non-null assignee and reminder_at <= database statement time. Return server time, occurrence key,
task version, title/link, due/creation/assignment timestamps and creator name where known.
Paginate with a stable (reminder_at,id) cursor; initial My reminders requests the first page.
Polling refreshes the visible page rather than silently dropping later records.

Poll every two seconds only while visible and connected, preventing overlapping requests; abort
or discard stale responses. Reconcile immediately after login, focus/online events and mutations.
Use server eligibility, not a local timer that could display reminders early. Keep one entry per
current occurrence. Preserve focus and DOM for unchanged results. A failed refresh marks displayed
data stale; authenticated access denial clears it. Successful removal/completion/reassignment
reconciliation removes obsolete entries. No private offline cache or service-worker data store.

Format dates with Intl.DateTimeFormat and saved IANA timezone; show timezone abbreviation on each
date, not a separate America/Los_Angeles line. Use a maintained timezone library or tested helper
for datetime-local conversion that rejects nonexistent times and requires a choice for repeated
times. Do not rely on browser-local timezone or unqualified Date parsing. Assigned by always means
original creator. Unknown historical values are omitted, never invented.

## 7. CI, hosting and operations

Separate source from local runtime data. Review .gitignore and history before first push; exclude
.env, .runtime, database dumps, local messages, personal screenshots and authentication state.
Repository visibility remains a setup decision; Pages availability on the user's GitHub plan must
be checked before selecting public versus private. No automatic repository publication in planning.

CI: locked install, typecheck/lint, component tests, SQL/RLS/RPC tests against isolated Supabase,
then Playwright Chromium/Firefox/WebKit and axe checks. GitHub-hosted CI can run the Supabase local
stack; do not assume Docker is installed on this Windows machine. Hosted test fixtures remain
separate from real pilot data. Never run destructive test resets against the pilot project.

Build artifact contains static frontend only. Pages workflow uses minimal permissions (contents
read, pages write, id-token write) and a protected deployment environment. Pin action revisions at
implementation. SQL migrations run in a separate reviewed step, not as a side effect of publishing
static assets. Verify migrations/tests before deploying a frontend that depends on them.

Keep a deployment ledger of commit/build, schema version, public configuration and verified URLs.
Provide a no-secrets health/version display for troubleshooting. Monitor Supabase quotas/errors
and failed auth; redact tokens and task details. Estimate load: each active tab at two-second polling
makes roughly 1,800 requests/hour. Measure real payload/egress before expanding testers. Free-tier
limits and cold starts must be reported; do not promise the quality targets until measured.

Export application data/schema securely and demonstrate isolated restore. Auth identity recovery
needs a separate supported procedure; an application-table dump is not a complete Auth backup.
Keep backups outside the public repository. Pilot data is disposable only if the user approves.

## 8. Moving to Render later

Deploy the same web/ static application as a Render Static Site, with BASE_PATH=/ and the new
PUBLIC_APP_URL. Keep the same Supabase project, RPC contracts and IDs: no database/account migration
is required solely for the host move. Domain components must not reference github.io directly.
Changing browser origin requires users to sign in again; do not promise browser-session portability.

Before cutover, allowlist the new Supabase return URL, validate Google login and invitation acceptance,
and build/test both host configurations. Freeze old-site writes during final switching to avoid
clients on incompatible schema versions. Retain an old Pages transition page forwarding hash routes
and pending invitation tokens only to the fixed trusted new origin; never log the tokens. Keep old
redirects long enough for outstanding seven-day invitations and OAuth attempts, then remove them.
An owned domain may simplify future transitions but is not a required pilot purchase.

Validate accounts/projects before disabling the old site. Roll back static artifacts only while
schema changes remain backward-compatible; restore data only through the reviewed recovery plan.
If later adding email, attach an external email provider and durable outbox/worker on Supabase or
Render separately. Do not send from browser code. Commercial release additionally needs monitoring,
backup policy, privacy/terms, capacity evidence and scope review; Render hosting alone is insufficient.

## 9. Implementation sequence and evidence

| Step | Deliverable | Exit check |
| --- | --- | --- |
| 1 | Bootstrap frontend and isolated Supabase schema/config | Build works at / and /repository/; no secrets in dist |
| 2 | Google auth, verified identity and live-session policies | OAuth tampering/return tests; revoked JWT replay denied; second session survives |
| 3 | Project, membership and group RPCs/RLS | All role matrices, direct API attempts and ownership races pass |
| 4 | Task forms and transactional operations | Scoped assignees, immutable creator, timezone and version-conflict tests pass |
| 5 | Draft invitations | Copy/paste fidelity, expiry boundary, wrong Google email, cancellation and replay tests pass |
| 6 | Reminders and UI parity | WR-01–12; automatic appearance/catch-up, mutation races and accessibility pass |
| 7 | Hosted pilot rehearsal | Real Google testers, API isolation, manual timings, quotas, export/restore and version checks |
| 8 | Publish reviewed pilot | User review, documented limitations and rollback evidence |

Retain original thresholds: task entry 9/10 <=20s, invitation acceptance 9/10 <=15s, active reminders
99/100 within [0,10]s, return/Google callback 99/100 <=5s. Use original per-device/three-person manual
conditions and record failures. Google consent time is separate. Local results and mocked OAuth
are not live-provider evidence. Email acceptance and local password tests are deferred pilot scope,
not passed checks. All permission checks must pass; no percentage excuses unauthorized access.

## 10. Remaining setup inputs

Ask individually during setup: repository visibility/name, Supabase project/region, fresh staging
data versus an approved import, and Google OAuth configuration. Never request secrets in chat;
provide dashboard/local secret-field instructions. First technical feasibility gate is server-owned
Google verification plus immediate session revocation under RLS. Do not build the full UI on an
unproven authorization model. Generate implementation tasks next; no hosting purchase is needed now.

## References checked 2026-11-23
- Vite static deployment (Pages base path and Render): https://vite.dev/guide/static-deploy.html
- Supabase Google OAuth: https://supabase.com/docs/guides/auth/social-sign-in/auth-google
- Session_id / live sessions: https://supabase.com/docs/guides/auth/sessions
- Local versus global sign-out: https://supabase.com/docs/reference/javascript/auth-signout
- Approved platform constraints and scope: spec.md
