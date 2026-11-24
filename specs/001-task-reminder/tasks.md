---
description: "Implementation tasks for the first usable task-reminder release with Google sign-in"
---

# Tasks: First Usable task-reminder

**Input**: Design documents in `specs/001-task-reminder/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [HTTP contract](contracts/http.md),
[email-worker contract](contracts/email-worker.md), and [quickstart.md](quickstart.md).
**Governance**: Constitution v1.0.0.
**Tests**: Required by FR-023, all acceptance scenarios, and SC-001–010.
Write each story's behavioral tests first, demonstrate the expected failure, then implement
and pass them. Pending live/manual evidence remains explicitly pending.
**Organization**: Shared prerequisites, P1 stories US1/US2/US4/US5/US6, P2 story US3,
then full-release verification. The ordering respects specification priorities.

## Format: `[ID] [P?] [Story] Description`

[P] indicates independent files within a ready phase, not permission to bypass dependencies.
Story labels retain their original spec.md numbers. Every task names its deliverable paths.
Task completion requires the stated behavior and its verification, not just file creation.

## Path Conventions

All code paths below are repository-relative to task-reminder, following plan.md.
Design documentation lives in `specs/001-task-reminder/`.
Test reports live in `artifacts/` during implementation and contain sanitized evidence.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the planned application skeleton and reproducible development environment.

- [X] T001 Create the Django project and accounts/projects/tasks/reminders app skeleton with app registration in `manage.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, and each app's `apps.py`.
- [X] T002 Declare Python 3.13 and compatible maintained Django 5.2, psycopg, Argon2, django-allauth, httpx, Svix, cryptography, Gunicorn, pytest-django and Playwright dependencies in `pyproject.toml`; resolve and record exact versions in `requirements.lock`.
- [X] T003 [P] Configure web, worker, and PostgreSQL 17 services, health dependencies, migrations workflow, and required environment variables including Google credentials in `Dockerfile`, `compose.yaml`, `.env.example`, and `.gitignore`.
- [X] T004 Configure isolated PostgreSQL tests, clock controls, role fixtures, and Playwright live-server fixtures in `tests/conftest.py` and test settings in `config/settings.py`; ensure tests cannot target production data.
- [X] T005 [P] Create the requirement/story-to-test evidence skeleton for FR-001–028, all acceptance scenarios, and SC-001–010 in `tests/acceptance-map.md`; record missing evidence rather than claiming runtime success.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared persistence, authorization, session, and email primitives required by all stories.
Complete this phase before story work. Generic email infrastructure supports verification and
invitations here; task-reminder scheduling belongs to US4.

- [X] T006 Create Account, AccountProof, RateBucket and database-session integration in `accounts/models.py` and `accounts/migrations/0001_initial.py`: Account has normalized username/email, email_verified_at, password hash or unusable-password marker, auth_generation, email_enabled=false and display_timezone; enforce “Unique case-folded username and email; Google-only usernames are internally generated; verification required for project creation/acceptance; no account deletion flow in v1”.
- [X] T007 Implement proof fields purpose=verify/reset, token_digest, issued_at, expires_at and consumed_at in `accounts/models.py` and shared proof/normalization helpers in `accounts/services.py`; enforce “Unique digest; verify expires in 24h, reset in 30m; valid only when now < expiry and unconsumed”, shared email normalization without dot/plus rewriting, and digest-only token storage.
- [X] T008 Implement Project and Membership schemas in `projects/models.py` and `projects/migrations/0001_initial.py`, including project name, owner_account_id, version/created_at and membership role=member/manager, independent flags, version/joined_at/left_at; enforce “Non-null owner; owner must have active membership; owner authority derives from this pointer”, “Partial unique active (project,account); fresh invitation creates new membership identity after departure; member flags false”, and “Project names are 1–100 trimmed characters”.
- [X] T009 Implement project-scoped lookups and the full spec permission matrix in `projects/permissions.py`; resolve owner from project pointer, reject cross-project IDs, and add positive/negative matrix tests in `tests/projects/test_permissions.py`.
- [X] T010 Implement CSRF, secure cookies, no-store responses, safe redirects, session rotation, Argon2, auth-generation middleware and sensitive URL/body redaction in `config/settings.py`, `accounts/middleware.py`, and `config/logging.py`; enforce “Active generation must equal current account generation on every authenticated request” and test settings/log output in `tests/accounts/test_security_defaults.py`.
- [X] T011 Implement atomic RateBucket updates, trusted-proxy source extraction and exact spec sign-in/recovery thresholds in `accounts/rate_limits.py`; enforce “Atomic updates; exact spec thresholds; identifiers keyed-hashed for storage where feasible”; test first-five tolerance, subsequent delays, reset windows, spoofed headers and distributed/shared sources in `tests/accounts/test_rate_limits.py`.
- [X] T012 Implement MutationReceipt and version-conflict helpers in `projects/models.py`, `projects/migrations/0002_mutation_receipt.py`, and `projects/services.py`; enforce “Unique actor/operation/key; different input with reused key is a conflict”, recheck authorization on replay, and test concurrent duplicate mutations in `tests/projects/test_mutation_receipts.py`.
- [X] T013 Create OutboundMessage, DeliveryAttempt and DeliveryEvent schemas and indices in `reminders/models.py` and `reminders/migrations/0001_initial.py`, with all fields in data-model.md; enforce “Unique logical purpose/occurrence and unique idempotency key; frozen payload after first attempt”, “Append-only attempts; no credentials, plaintext tokens, or task descriptions”, and “Unique provider event ID; preserve event history and out-of-order arrival”.
- [X] T014 Implement fake and Resend transport adapters, accepted/rejected/unknown results, encrypted temporary token payloads, five-second request deadline and stable idempotency keys in `reminders/providers.py`; cover lost-response, duplicate-response and provider-status behavior in `tests/contracts/test_email_provider.py`.
- [X] T015 Implement the shared durable outbox service and one-second supervised worker in `reminders/services.py` and `reminders/management/commands/run_reminder_worker.py`; use SKIP LOCKED, 30-second leases, durable pre-handoff markers, contract retry delays, read-only reconciliation and held state beyond the 24-hour window; test restart/claim/retry behavior in `tests/reminders/test_outbox.py`.
- [X] T016 Implement signed raw-body webhook verification, event deduplication, opaque message correlation and out-of-order outcome preservation in `reminders/views.py`, `config/urls.py`, and `tests/contracts/test_email_webhooks.py`; ensure only this provider endpoint is CSRF-exempt.
- [X] T017 Create the responsive accessible page shell, self-hosted Inter assets, labeled controls, error messages, safe text rendering, and local-only fake-outbox viewer in `templates/base.html`, `static/css/app.css`, and `reminders/views.py`; verify the viewer is disabled outside development.

**Checkpoint**: Migrations, session checks, permission matrix and durable email transport pass.

## Phase 3: User Story 1 - Manage My Own Project and Tasks (Priority: P1)

**Goal**: Register, verify, create a project, and save/update/complete personal tasks.
**Independent Test**: A fresh password account creates a project and self-assigned task,
refreshes to confirm persistence, reschedules, and completes it.
**Coverage**: FR-001, FR-005–006, FR-014–016; Story 1; SC-001.

### Tests for User Story 1

- [X] T018 [P] [US1] Write registration/verification/project/task HTTP acceptance tests, including invalid input, CSRF and verification expiry boundaries, in `tests/contracts/test_personal_workflow.py`.
- [X] T019 [P] [US1] Write the personal project/task browser journey and duplicate-save/version-conflict cases in `tests/e2e/test_personal_tasks.py`.

### Implementation for User Story 1

- [X] T020 [US1] Implement password registration, verification/resend and login through shared proof/outbox/session services in `accounts/services.py`, `accounts/forms.py`, `accounts/views.py`, and `templates/accounts/`; handle duplicate identity, generic errors, and unusable-password accounts.
- [X] T021 [US1] Implement atomic project creation with active owner membership, project selection and the deferred owner-membership constraint in `projects/services.py`, `projects/views.py`, `projects/forms.py`, and `projects/migrations/0003_owner_membership_constraint.py`.
- [X] T022 [US1] Implement Task fields and indices in `tasks/models.py` and `tasks/migrations/0001_initial.py`: “assignee_membership nullable”, “status=open/completed”, “reminder_at nullable”, version/schedule_generation/assignment_generation; enforce “Title 1–200 trimmed characters; description at most 10,000; assignee must be active in same project; version required for edits” and same-project database constraints.
- [X] T023 [US1] Implement self-assigned create/edit/complete/reschedule transactions, idempotency receipts, expected-version conflicts and UTC/timezone validation in `tasks/services.py` and `tasks/forms.py`; reject nonexistent local times and require an explicit choice for ambiguous times.
- [X] T024 [US1] Implement task list/detail/create/edit/complete routes and quick-entry progressive forms in `tasks/views.py`, `config/urls.py`, `templates/tasks/`, and `static/js/tasks.js`; preserve input on errors and show saved reminder time with timezone.
- [ ] T025 [US1] Run Story 1 tests and the specified 10-attempt manual task-entry trials per device category with at least three people; record raw timings and SC-001 results in `artifacts/us1-task-entry.json` and update `tests/acceptance-map.md`.

**Checkpoint**: The personal-task slice works independently. Google onboarding is added in US6.

## Phase 4: User Story 2 - Invite People and Govern Each Project (Priority: P1)

**Goal**: Join projects deliberately and enforce independent membership authority.
**Independent Test**: With two projects and three accounts, accept an invitation into the
second project and exercise the full role, cancellation, departure and ownership matrix.
**Coverage**: FR-005–012, FR-016; Story 2; SC-002, SC-006–007.

### Tests for User Story 2

- [X] T026 [P] [US2] Write invitation identity, acceptance, expiry, cancellation, forwarding and replay contract tests in `tests/contracts/test_invitations.py`.
- [X] T027 [P] [US2] Write PostgreSQL transaction tests for competing acceptance/cancellation, owner transfers, manager permission changes and departure in `tests/projects/test_membership_concurrency.py`.

### Implementation for User Story 2

- [X] T028 [US2] Implement Invitation schema and migrations in `projects/models.py` and `projects/migrations/0004_invitation.py` with project/inviter/recipient_email/token_digest/sent_at/expires_at/status/accepted_membership_id; enforce “Unique digest; pending/accepted/cancelled; expiry derived from now >= expires_at; expiry seven days after successful send acceptance”, including the prepared pre-send state described in data-model.md.
- [X] T029 [US2] Implement authorized invite preparation/send acceptance, fresh-invite creation, immediate cancellation, verified-email acceptance and replay handling in `projects/invitations.py`; lock project then invitation and preserve existing accounts/memberships across projects.
- [X] T030 [US2] Implement owner-only role/flag changes, active-manager ownership transfer, former-owner manager flags, removal and voluntary departure in `projects/services.py`; preserve exactly one owner, clear departed task assignments and invalidate pending email work atomically in the documented lock order.
- [X] T031 [US2] Implement invitation preview/accept and member/role/invite/cancel/leave/transfer forms and routes in `projects/views.py`, `projects/forms.py`, `config/urls.py`, and `templates/projects/`; expose only project name/inviter before acceptance.
- [X] T032 [US2] Run the project isolation matrix through direct requests and browser flows, including task links after departure, in `tests/projects/test_isolation.py` and `tests/e2e/test_project_membership.py`.
- [ ] T033 [US2] Run Story 2 tests and manual invitation trials with at least three people, 10 attempts per device category and the 15-second target; record SC-002/006/007 results in `artifacts/us2-invitations.json` and `tests/acceptance-map.md`.

## Phase 5: User Story 4 - Receive Relevant Reminders (Priority: P1)

**Goal**: Show due website reminders and send optional email according to current state.
**Independent Test**: Use prepared membership/task fixtures; compare known scheduled times
to email acceptance and visible reminders, then mutate state before dispatch.
**Coverage**: FR-017–022; Story 4; SC-003–005, SC-009.
Assignment UI arrives in US3; assignment/removal fixtures permit independent testing now.

### Tests for User Story 4

- [X] T034 [P] [US4] Write clock-controlled due-list, timing-boundary and reminder mutation contract tests in `tests/contracts/test_reminders.py`.
- [X] T035 [P] [US4] Write real PostgreSQL dispatch-versus-departure, reschedule, completion, reassignment and preference races plus lost-response/crash/retry tests in `tests/reminders/test_dispatch_races.py`.

### Implementation for User Story 4

- [X] T036 [US4] Implement EmailOccurrence with task, schedule_generation, assignment_generation, recipient_membership and due_at in `reminders/models.py` and `reminders/migrations/0002_occurrence.py`; enforce “Unique tuple for task/generations/recipient; immutable identity” and reference it from OutboundMessage.
- [X] T037 [US4] Implement current-state eligibility, occurrence creation, overdue sweep and atomic mutation invalidation in `reminders/services.py` and `tasks/services.py`; use current verified email, membership, assignee, completion, schedule and preference; reconcile unknowns without replaying stale payloads.
- [X] T038 [US4] Integrate project/account/task/message lock ordering and bounded provider handoff into `reminders/services.py`; implement contract suppression, durable attempt marker, fixed payload, identical-key replay within 24 hours, and held outcomes after expiry.
- [X] T039 [US4] Implement account-wide email preference and timezone settings in `accounts/forms.py`, `accounts/views.py`, `accounts/services.py`, and `templates/accounts/preferences.html`; lock account changes and ensure enabling email never resends an accepted occurrence.
- [X] T040 [US4] Implement access-checked due reminders with server_time, occurrence_key, task_version, safe task URL and 100-item authenticated pagination in `reminders/views.py`, `templates/reminders/`, and `config/urls.py`; derive eligibility from live task/membership joins.
- [X] T041 [US4] Implement two-second visible/connected polling, initial-page due reminders, immediate focus/reconnection/mutation refresh, stale indicators and out-of-order response protection in `static/js/reminders.js` and `templates/base.html`; clear inaccessible private content on session/access errors.
- [X] T042 [US4] Implement sanitized reminder email templates and access-checked current-state links in `templates/email/task_reminder.txt`, `templates/email/task_reminder.html`, and `tests/reminders/test_email_privacy.py`; allow task title and generic text only.
- [X] T043 [US4] Implement fake/live benchmark command with controlled recipient allowlist, raw timestamps, acceptance evidence and separated suppression/failure counts in `reminders/management/commands/benchmark_reminders.py`; add active/returning browser sampling in `tests/e2e/test_reminder_timing.py`.
- [X] T044 [US4] Run Story 4 deterministic and fake-provider tests and record SC-003–005/009 local results plus explicitly pending live samples in `artifacts/us4-reminders.json` and `tests/acceptance-map.md`.

## Phase 6: User Story 5 - Recover and End Account Access Safely (Priority: P1)

**Goal**: Reset forgotten local passwords and revoke the correct website sessions.
**Independent Test**: Two devices sign in; ordinary logout ends one session, and successful
reset ends all sessions. Replay and expiry fail, and recovery stays available during delays.
**Coverage**: FR-002–004; Story 5; SC-008.

### Tests for User Story 5

- [X] T045 [P] [US5] Write reset issue/expiry/single-use/unknown-account tests and Google-only unusable-password recovery cases in `tests/accounts/test_recovery.py`.
- [X] T046 [P] [US5] Write two-device logout/reset and exact account/source throttle behavior tests in `tests/e2e/test_sessions.py` and `tests/accounts/test_session_revocation.py`.

### Implementation for User Story 5

- [X] T047 [US5] Implement generic recovery requests, separately limited recovery email, reset proof consumption, password update, outstanding-proof invalidation and auth-generation increment atomically in `accounts/services.py`; Google-only accounts receive recovery guidance without a local reset token.
- [X] T048 [US5] Implement reset/recovery/logout routes and templates in `accounts/views.py`, `accounts/forms.py`, `config/urls.py`, and `templates/accounts/`; ensure logout is CSRF-protected and reset never preserves the resetting session.
- [X] T049 [US5] Verify storage parameters and credential/token redaction across app/proxy logging, and test reset races with ended-session requests in `tests/accounts/test_security_review.py`; record reviewed configuration and SC-008 evidence in `artifacts/us5-security.json`.
- [X] T050 [US5] Run all Story 5 scenarios including delay boundaries, recovery during throttling and access from old sessions; update `tests/acceptance-map.md` with results and remaining real-device verification.

## Phase 7: User Story 6 - Start and Return with Google (Priority: P1)

**Goal**: Start without choosing local credentials, return to the same account, and explicitly
connect Google to an existing password account.
**Independent Test**: New and returning Google identities plus an existing matching-email
password account exercise signup, connection, invitations, cancellation, and logout.
**Coverage**: FR-024–028; Story 6; SC-006, SC-008, SC-010.

### Tests for User Story 6

- [X] T051 [P] [US6] Write signed provider-fixture tests for signature/issuer/audience/expiry/state/nonce/PKCE, cancellation/replay and concurrent first login in `tests/accounts/test_google_protocol.py`; run actual provider-library validation.
- [X] T052 [P] [US6] Write account-collision, explicit recent-password connection, authoritative email, invitation continuation and session-revocation tests in `tests/accounts/test_google_accounts.py`.

### Implementation for User Story 6

- [X] T053 [US6] Configure django-allauth's Google provider, minimal scopes, exact callbacks, PKCE, and disabled email authentication/auto-connect/token retention in `config/settings.py` and `.env.example`; use SocialAccount as the sole identity record and enforce “Unique (provider,uid); one Google identity per application account in v1; never linked through email match alone” through `accounts/migrations/0002_google_constraints.py`.
- [X] T054 [US6] Implement session-bound one-use login/connect flow state, nonce, PKCE verifier, safe return path and recent-password proof in `accounts/google_flow.py` and `accounts/views.py`; enforce “One-use server-side state with ten-minute expiry; temporary secrets excluded from logs and removed on consumption/expiry” and five-minute account-bound reauthentication.
- [X] T055 [US6] Implement transactional new-profile creation, generated internal username/unusable password, stable-sub returning login and collision-to-explicit-connect behavior in `accounts/adapters.py`; recheck identity uniqueness, verified-email match and recent password proof under account locks.
- [X] T056 [US6] Implement authoritative Gmail/Workspace email verification, external-address email proof, and changed-email suppression/reverification in `accounts/adapters.py` and `accounts/services.py`; never silently replace stored email or membership and never add a password through recovery.
- [X] T057 [US6] Implement Continue with Google, connection status and connection initiation UI plus callback routing in `templates/accounts/login.html`, `templates/accounts/register.html`, `templates/accounts/connections.html`, and `config/urls.py`; restore invitation preview after login without auto-acceptance.
- [X] T058 [US6] Integrate Google sessions with account auth-generation checks and ordinary logout, and run mixed-password/Google reset-revocation regressions in `tests/accounts/test_google_accounts.py` and `tests/e2e/test_google_login.py`.
- [X] T059 [US6] Document local/staging Google credential and consent setup in `specs/001-task-reminder/quickstart.md`, run fixture-based Story 6 tests, and record SC-010 local results with live-provider/mobile checks pending in `artifacts/us6-google.json` and `tests/acceptance-map.md`.

## Phase 8: User Story 3 - Assign Work and Organize Groups (Priority: P2)

**Goal**: Delegate project work and organize existing members without changing authority.
**Independent Test**: Prepared project roles assign/reassign work and manage groups; regular
members retain only their specified task-edit authority.
**Coverage**: FR-013–016 and reminder integration; Story 3; SC-006, SC-009.

### Tests for User Story 3

- [X] T060 [P] [US3] Write assignment/group authorization, same-project constraints and group-visibility invariance tests in `tests/contracts/test_groups_assignments.py`.
- [X] T061 [P] [US3] Write assignment/version-conflict/reminder handoff and departed-member group cleanup tests in `tests/projects/test_group_task_integration.py`.

### Implementation for User Story 3

- [X] T062 [US3] Implement Group and GroupMembership in `projects/models.py` and `projects/migrations/0005_groups.py`; enforce “Case-folded name unique within project; owner-managed”, “Unique pair; matching project and active membership required”, and “group names 1–80”; include version fields and same-project database constraints.
- [X] T063 [US3] Implement owner-only group create/rename/delete/membership services and departed-member cleanup in `projects/groups.py` and `projects/services.py`; preserve tasks and permissions when deleting a group and use expected-version conflicts.
- [X] T064 [US3] Implement owner/assignment-enabled-manager create/edit/complete/assign/reassign actions in `tasks/services.py`, `tasks/forms.py`, and `tasks/views.py`; update assignment generations and current reminder recipient atomically and reject inactive or cross-project targets.
- [X] T065 [US3] Implement group filters, owner-only group forms and assignee selection in `projects/views.py`, `templates/projects/groups.html`, `templates/projects/members.html`, and `templates/tasks/`; all members can view every project task.
- [X] T066 [US3] Run Story 3 browser and concurrency regressions after adding groups, reassignment and departure integration in `tests/e2e/test_groups_assignments.py`; record results in `artifacts/us3-groups.json` and `tests/acceptance-map.md`.

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Complete all six journeys and gather full-release evidence. Local implementation
can proceed using fakes while external credentials or participants are unavailable.

- [X] T067 Implement repeatable isolated demo/scale fixtures for 100 accounts, 20 projects, 10,000 tasks and 50 active tabs in `reminders/management/commands/seed_demo.py`; protect production environments and avoid duplicate fixtures.
- [X] T068 Implement worker heartbeat/backlog/latency/unknown metrics and stale-heartbeat/oldest-due thresholds in `reminders/health.py` and process health checks in `compose.yaml`; verify alert thresholds in `tests/reminders/test_health.py`.
- [X] T069 Implement safe expiry cleanup for proof/flow secrets, sessions, mutation receipts and encrypted outbound payloads while preserving accepted-send deduplication evidence in `reminders/management/commands/cleanup_expired.py`; define retention and test it in `tests/reminders/test_cleanup.py`.
- [X] T070 Finish keyboard/focus/error/live-region behavior, phone layouts, self-hosted font assets and home-screen manifest in `templates/base.html`, `static/css/app.css`, `static/manifest.webmanifest`, and `tests/e2e/test_accessibility.py`; verify private responses are never service-worker cached.
- [X] T071 Run all migrations/checks and automated tests from `specs/001-task-reminder/quickstart.md`, including fresh-database and existing-data migration runs; map all 28 requirements and every scenario to outcomes in `tests/acceptance-map.md` and `artifacts/automated-results.json`.
- [ ] T072 Configure authorized staging email/Google test credentials and execute live provider acceptance, signed webhooks, real Google onboarding/linking, real phone/home-screen and returning-visit samples; record SC-003–005/010 raw results and provider timing separately in `artifacts/live-results.json`.
- [ ] T073 Complete manual task/invitation timing trials, 50-active-tab and 100-reminder-burst checks, capacity diagnosis and any required full reruns in `artifacts/manual-and-capacity-results.json`; satisfy SC-001–002 without replacing failed samples.
- [X] T074 Rehearse isolated backup/restore of memberships, tasks and accepted-send identities and verify production HTTPS/proxy/worker settings against `specs/001-task-reminder/quickstart.md`; record restore/security evidence in `artifacts/release-readiness.json`.
- [ ] T075 Review all story checkpoints, SC-001–010 and the constitution against `tests/acceptance-map.md`; complete `artifacts/release-readiness.json` only when every required check passes, listing any blocked live/manual prerequisite explicitly.

## Dependencies & Execution Order

### Phase Dependencies

Setup -> Foundation -> US1 -> US2 -> US4 -> US5 -> US6 -> US3 -> full-release checks is the
safe default sequence, particularly because services and route files are shared.
All P1 work precedes the P2 group/assignment UI.

### User Story Dependencies

| Story | Required baseline | Independent completion evidence |
|---|---|---|
| US1 | Setup and Foundation | New verified account, project, persisted self-task and SC-001 |
| US2 | US1 | Prepared projects/accounts, invitation and ownership lifecycle, SC-002/006/007 |
| US4 | US1 and US2 membership mutations | Prepared task/assignment fixtures, due UI and dispatch mutation matrix, SC-003–005/009 |
| US5 | US1 and shared security foundation | Two prepared sessions, recovery boundaries and SC-008 |
| US6 | US1, US2 invitation flow, US5 reauthentication/recovery, US4 due-list UI | Signed provider fixtures plus real provider/device verification, SC-010 |
| US3 | US1/US2 and US4 dispatch integration | Groups, reassignment, departure and privacy regression |
| Release | All six stories | All mapped acceptance and live/manual outcomes |

US4 and US5 have independent domain tests but share account services/views, so coordinate
edits or execute their implementation sequentially. Story tests may use seeded fixtures for
dependencies; “independent” means a clear testable journey, not duplicated infrastructure.

### Within Each User Story

Behavioral/contract tests precede implementation; verify meaningful failures.
Models and migrations precede transactional services; services precede routes/UI.
Run story tests before checking off its final evidence task. Live/manual tests that lack
credentials, devices, or participants remain unchecked while authorized local work continues.

### Parallel Opportunities

Setup container configuration and evidence-map creation can proceed after the skeleton.
Within each story, the two initial [P] test tasks touch different files and can be drafted
together once the baseline is ready. Implementation tasks touching shared models, migrations,
services, settings, or routes execute sequentially. Parallel markers describe opportunities
for implementation and do not themselves request agent delegation.

## Parallel Examples by User Story

| Story | Independent work pair |
|---|---|
| US1 | Personal HTTP contract tests and personal browser journey tests |
| US2 | Invitation contract tests and membership concurrency tests |
| US4 | Reminder response/timing contract tests and dispatch race tests |
| US5 | Recovery tests and session/revocation tests |
| US6 | Provider protocol validation tests and account/linking lifecycle tests |
| US3 | Group/assignment contract tests and group/task integration tests |

## Implementation Strategy

### MVP First

Complete setup, foundation and US1 for the first local demonstration of a usable personal
task workflow. Continue through US2/US4/US5/US6 to include the requested collaboration,
reminders, secure recovery and Google sign-in. US3 completes the specified first release.

### Incremental Delivery

Each story ends with an independent test checkpoint. Preserve existing passing behavior
while adding the next slice. Full release requires all stories and cross-cutting verification.
Building the application does not require publishing it.

### Evidence and Scope

Maintain exact FR/SC mappings in tests/acceptance-map.md and follow quickstart.md.
Provider credentials, real devices and human trials are release prerequisites, not prerequisites
for writing and exercising local implementations with controlled fakes.
No feature is complete merely because its endpoint or model exists.


## Implementation status - 2026-11-15

Local implementation and automated checks are complete. Consolidated source/test paths and
scenario evidence are mapped in tests/acceptance-map.md; results are retained in artifacts/.
T025/T033 require three-person manual timing. T072 requires live providers and real devices.
T073 has passing local 50-tab/100-reminder evidence but human trials remain pending.
T075 remains open until all external/manual release gates pass. Linux deployment is not
performed; production configuration checks and isolated local restore are verified.
Modern Web Guidance is installed and has informed the final accessibility/form refinements.
