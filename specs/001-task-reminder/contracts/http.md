# HTTP and Browser Contracts

## Common Rules

Same-origin HTTPS with Django session cookies. Every mutation uses CSRF protection, including
sign-in and logout. Form POSTs use Post/Redirect/Get after success; GET never changes domain
state except the explicitly state-validated Google authorization callback below. Sensitive pages and JSON use Cache-Control: private, no-store.

For forms, invalid fields return 422 and preserve input; conflicts return 409. Unauthenticated
HTML requests redirect to sign-in with a validated same-origin return path. JSON returns 401.
Project objects outside current membership return 404. Insufficient authority within a visible
project returns 403. Throttles return 429 with Retry-After. Unexpected failures show a safe
message and correlation ID.

POST create/accept/transfer requests include a client mutation UUID. Reusing it with different
input is 409. Task/group/member mutations include expected_version where relevant. IDs in paths
and bodies are always validated against the same project. Never trust hidden form role fields.

## Routes

| Method and path | Input | Result and authority |
|---|---|---|
| GET/POST /accounts/register | username, email, password, confirmation | Create unverified account; send verification; generic collision guidance avoids account discovery |
| GET /accounts/verify/{token} | token | Confirmation page; no consumption on link scanning |
| POST /accounts/verify/{token} | CSRF | Consume valid proof, mark email verified |
| POST /accounts/verification/resend | authenticated unverified account | Generic response; rate limited new proof |
| GET/POST /accounts/login | username, password, return path | Session created on success; safe generic error otherwise |
| POST /accounts/logout | CSRF | Current session deleted; redirect to sign-in |
| GET/POST /accounts/recovery | email | Same public response for existing and unknown email |
| GET /accounts/reset/{token} | token | Password-reset form, no token consumption |
| POST /accounts/reset/{token} | password, confirmation | Atomic reset and all-session invalidation; return to sign-in |
| GET/POST /accounts/preferences | email_enabled, display_timezone | Update own preference; no project authority |
| GET /projects | session | List current memberships only |
| POST /projects | name, mutation_key | Verified account creates owned project |
| GET /projects/{project}/tasks | optional status/assignee filters | All tasks visible to project members |
| POST /projects/{project}/tasks | title, description?, reminder_at?, timezone, assignee_id?, mutation_key | Own task for members; another current member requires assignment permission |
| GET /projects/{project}/tasks/{task} | session | Current task state, member required |
| POST /projects/{project}/tasks/{task}/edit | expected_version, title, description, reminder_at, timezone | Assignee, owner, or assignment-enabled manager |
| POST /projects/{project}/tasks/{task}/complete | expected_version | Same authority as edit; completion cancels reminders |
| POST /projects/{project}/tasks/{task}/assign | expected_version, assignee_membership_id | Owner or assignment-enabled manager; current same-project target |
| GET /projects/{project}/members | optional group_id | Current members; member required |
| POST /projects/{project}/members/{member}/role | role, can_invite, can_assign, expected_version | Owner only; owner role uses transfer route |
| POST /projects/{project}/members/{member}/remove | mutation_key | Owner only; cannot remove current owner |
| POST /projects/{project}/leave | mutation_key | Current non-owner membership leaves |
| POST /projects/{project}/transfer | target_membership_id, expected_version, mutation_key | Owner only; active manager target |
| POST /projects/{project}/invitations | email, mutation_key | Owner or invitation-enabled manager |
| GET /projects/{project}/invitations | session | Owner sees all; authorized manager sees their own |
| POST /projects/{project}/invitations/{invitation}/cancel | mutation_key | Owner or authorized sender |
| GET /invitations/{token} | token | Project name and inviter only; no task/member metadata |
| POST /invitations/{token}/accept | mutation_key | Signed-in matching verified email; join as member |
| GET /projects/{project}/groups | session | Project member |
| POST /projects/{project}/groups | name, mutation_key | Owner only |
| POST /projects/{project}/groups/{group}/edit | name, expected_version | Owner only |
| POST /projects/{project}/groups/{group}/delete | expected_version | Owner only; preserve members/tasks |
| POST /projects/{project}/groups/{group}/members | member IDs, expected_version | Owner only; active same-project memberships |
| GET /reminders | session | Cross-project due-reminder page for current assignee |
| GET /reminders/due | session, JSON Accept header | Current eligible reminders, never an authority cache |
| POST /webhooks/resend | exact raw body and signed provider headers | Signature verification; event deduplication; session/CSRF exempt only for this endpoint |

All token-bearing routes must redact token path segments from access logs and set
Referrer-Policy: same-origin. Verification and recovery tokens are never put in analytics.
Invitation emails intentionally disclose only project name and inviter before joining.

## Reminder JSON

Success 200 returns an object with server_time (UTC ISO-8601), items (array), and next_cursor
(null or opaque pagination cursor). Each item includes occurrence_key, project_id, task_id,
title, scheduled_at, task_version, and relative task_url. The first page includes the earliest
100 due reminders, with authenticated pagination for more. Empty state is an empty array.
Each page recomputes current access. The UI replaces matching items by occurrence_key.

Client polling occurs every two seconds only while visible and connected; immediate fetch
on focus/reconnection. A 401 clears private content and requests sign-in. A 403/404 clears
the inaccessible project content. Out-of-order responses cannot overwrite newer data.
A failed fetch preserves an explicit stale status and never grants access to a task.

## Interaction and Accessibility

Use labeled keyboard-operable forms, visible errors, and focus management after save.
Task-entry success shows the saved title, assignee, and reminder time/timezone.
Invitation confirmation identifies project and inviter and requires explicit acceptance.
Success/failure messages use appropriate live regions without repeating every poll.
Support narrow phone layouts and a home-screen launch manifest. Private content is never
stored in a service-worker cache. The application must remain usable with ordinary navigation
when progressive form enhancements fail.

## Google Sign-in and Account Connection

| Method and path | Input | Result and authority |
|---|---|---|
| POST /accounts/google/login/ | CSRF, safe next path, process=login | Begin session-bound Google flow with fresh state, nonce, and PKCE |
| GET /accounts/google/login/callback/ | code, state or provider error | Validate one-use flow and provider identity; create/reuse account or request explicit existing-account connection |
| POST /accounts/reauthenticate | current local password, CSRF | Record account/session-bound proof valid for five minutes; use existing sign-in limits |
| POST /accounts/google/login/ with process=connect | CSRF, current session with recent proof | Connect intent is bound to the current account; callback must match that account and verified email |
| GET /accounts/connections | current session | Show connected Google identity and sign-in methods; no disconnect control in v1 |

Use allauth provider routes for login/callback and a custom adapter for application rules.
Do not expose an unchecked alternate token-login endpoint. Existing auth forms remain routed
through their application services so allauth cannot introduce a second reset/linking policy.

State/nonce mismatch, invalid signature/issuer/audience, expired identity, expired flow,
and replay return a safe failure and fresh sign-in option. Cancellation creates no account.
The callback may redirect only to a server-validated same-origin path. Invitation return
paths lead to the acceptance page and never automatically join the project.

A collision prompts sign-in to the existing account followed by an explicit connection.
A Google-only account keeps an unusable password; local recovery gives the same public response
as other requests and may send private guidance to use Google recovery without a reset token.

Ordinary logout ends the website session; it does not sign the user out of Google.
The session's auth_generation is checked for password and Google logins alike.
OAuth codes, tokens, state, nonce, and connection proofs are redacted from logs.

Implementation note: same-origin referrer policy preserves browser Origin/Referer behavior
needed for CSRF-protected form POSTs while withholding paths on cross-origin navigation.
OAuth flow state is application-owned and session-bound; signed identity validation uses
the maintained allauth provider library. No alternate token-login endpoint is exposed.
