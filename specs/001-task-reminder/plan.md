# Implementation Plan: First Usable task-reminder

**Branch**: No Git branch verified. Setup resolved feature identifier `001-task-reminder`.
**Date**: 2026-11-13
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-task-reminder/spec.md`

## Summary

Build a responsive Django application with server-rendered pages, small JavaScript modules,
PostgreSQL, and a separately supervised reminder worker. Use one shared authorization service
for project actions and reminder eligibility. Durable email jobs and provider idempotency
support recovery from retries. Current-state queries provide in-website reminders.

The first version includes accounts, independent project memberships, invitations, groups,
tasks, optional email, and in-website reminders. It follows constitution v1.0.0 and the
28 functional requirements and ten success criteria in the specification.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2 LTS, PostgreSQL 17; use latest compatible security
patches and lock exact dependencies during implementation.

**Primary Dependencies**: Django templates/forms/auth/sessions, django-allauth Google provider,
psycopg 3, argon2-cffi,
httpx for Resend, Svix for webhook verification, cryptography for encrypted sensitive outbox
payloads; Gunicorn for Linux hosting. Plain JavaScript and CSS; self-hosted Inter typography.

**Storage**: PostgreSQL for application state, sessions, rate counters, durable outbox, and
delivery outcomes. No in-memory-only schedule or authorization state.

**Testing**: pytest, pytest-django, real PostgreSQL transaction tests, Playwright browser tests,
controlled clock/provider fakes, and manual timed trials.

**Target Platform**: Linux application and worker processes behind HTTPS plus managed
PostgreSQL; Docker Compose for reproducible local development on Windows or Linux.
Desktop Chrome/Edge/Firefox and real iOS Safari/Android Chrome current stable releases at
implementation. Record exact tested browser/OS versions. Home-screen launches receive
responsive website behavior, without offline caching of private data.

**Project Type**: Single web application with a background worker from the same codebase.

**Performance Goals**: Constitution targets of 9/10 task entries within 20 seconds, 9/10
invitation acceptances within 15 seconds, 99/100 emails accepted in [0,60] seconds,
99/100 active-tab reminders visible in [0,10] seconds, and 99/100 returning visits within
five seconds. Poll active tabs every two seconds and workers every second. All privacy
checks must pass independently of percentages.

**Constraints**: Email titles are permitted private content; membership and schedule must be
current at dispatch. A five-second outbound request timeout bounds lock contention.
Unknown provider outcomes remain unresolved until reconciled. Resend idempotency retention
is 24 hours, so retries beyond that window cannot rely on its key alone.

**Scale/Scope**: Initial validation fixture of 100 accounts, 20 projects, up to 50 members
per project, 10,000 tasks total, and 50 simultaneously active tabs. These are test conditions,
not product limits. Spread the standard 100 email sample across ten minutes and separately
test a 100-reminder burst to expose provider throttling and backlog. Record capacity limits.

**Deployment arrangement**: Container-ready web process and always-on worker, managed
PostgreSQL, and Resend transactional email. Choose the actual hosting account at deployment.
Provider domain verification, credentials, and an always-on worker are operational prerequisites.
No hosting purchase or deployment is part of this planning command.

## Constitution Check

| Principle | Pre-research gate | Post-design gate and evidence |
|---|---|---|
| Project authority | Pass: role matrix is explicit | Pass: project-scoped queries, service-level authorization, owner pointer, transaction tests |
| Trustworthy invitations | Pass: identity and lifecycle specified | Pass: hashed tokens, verified email match, project/invitation locking, replay rejection |
| Secure account access | Pass: recovery and limits specified | Pass: Argon2, server sessions, auth generation, Google identity validation, explicit linking, rate limits, single-use proof rows |
| Current private reminders | Pass: recipients and lifecycle defined | Pass: current-state query, serialized dispatch boundary, durable attempts, access-checked links |
| Demonstrated quality | Pass: acceptance criteria precede implementation | Pass: FR/SC traceability and validation guide cover all release gates |

There are no constitution exceptions. These gates assess design conformity. Runtime targets
remain to be demonstrated after implementation.

## Project Structure

### Documentation (this feature)

```text
specs/001-task-reminder/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/
    http.md
    email-worker.md
  checklists/requirements.md
```

The next command generates tasks.md.

### Source Code (repository root)

```text
manage.py
pyproject.toml
requirements.lock
compose.yaml
Dockerfile
.env.example
config/
  settings.py
  urls.py
  wsgi.py
accounts/
  models.py
  forms.py
  views.py
  services.py
  middleware.py
projects/
  models.py
  forms.py
  views.py
  services.py
  permissions.py
tasks/
  models.py
  forms.py
  views.py
  services.py
reminders/
  models.py
  views.py
  services.py
  providers.py
  management/commands/
    run_reminder_worker.py
    seed_demo.py
    benchmark_reminders.py
templates/
static/
  css/
  js/
tests/
  accounts/
  projects/
  tasks/
  reminders/
  contracts/
  e2e/
```

**Structure Decision**: Django apps follow the account, project, task, and reminder boundaries.
Services contain transactional mutations shared by forms and worker code. Views own request
validation and response formatting. Domain authorization is exercised on every request.
Avoid an additional frontend deployment, separate queue service, or public API layer for v1.

## Design and Execution Phases

### Phase 0 — Research

[research.md](research.md) records dependency decisions, sources, alternatives, and limits.
All technical choices required to generate tasks are resolved.

### Phase 1 — Data and Interfaces

[data-model.md](data-model.md) defines constraints, state transitions, concurrency ordering,
and lifecycle details. [HTTP contracts](contracts/http.md) define browser behavior and
request formats. [Email and worker contracts](contracts/email-worker.md) define the
dispatch boundary and recovery protocol. [quickstart.md](quickstart.md) defines the
implementation's required runnable verification commands.

### Authorization and Account Security

Use an account model from the first migration. The project owner pointer is authoritative;
memberships hold member/manager roles and independent invitation and assignment flags.
Resolve effective owner authority from that pointer. Do not use Django global groups for
project authority. Scope every object lookup by project and current membership.

Use database sessions with Secure, HttpOnly, SameSite=Lax cookies, CSRF protection for all
browser mutations, TLS, allowed hosts, autoescaped text, and private/no-store responses.
Each session records the account auth generation. Reset increments it atomically; middleware
rejects older generations on every request. Ordinary logout deletes only the current session.
Password hashing uses Django Argon2 support with deployment-tuned parameters at least meeting
current OWASP guidance. Password/reset/verification fields and token-bearing URL paths must
be redacted at application and proxy logs; token pages use same-origin referrer policy and no third-party assets.

Use exact failure thresholds from spec.md. Rate counters are durable and atomic.
A source is the remote IP normalized to a full IPv4 or IPv6 address from the trusted ingress.
Ignore client-supplied forwarding headers unless the direct peer is an explicitly configured
trusted proxy. Record shared-source and distributed-source tests. The recovery counters
are separate. Use identical recovery responses and dummy password work for unknown accounts.

### Google Sign-in

Use django-allauth's Google authorization-code flow with PKCE enabled. A maintained adapter
validates signed identity results and connects them to the existing account model.
Keep email-only authentication/auto-connect disabled; explicitly linked provider subject is
the login key. Request only openid, email, and profile scopes. Tokens are not retained for
background Google access. Store no Google password.

Use the allauth SocialAccount row as the sole provider identity record with provider plus
Google sub uniqueness. Initial signup transaction creates the application account and identity
together. Assign an internal random username and an unusable password for Google-only users,
so the user sees no separate username/password registration step. Resolve email collisions
by requesting sign-in to the existing account and explicit connection.

Connection requires a session with local password reauthentication within five minutes,
matching verified email, a CSRF-protected initiation, and a session-bound connect intent.
Rotate the local session at login and retain the account auth-generation check for every
sign-in method. A Google-only recovery request must not set a local password.

Validate issuer, audience, expiry, signature, state, and nonce through the provider library.
Use exact configured redirect URIs, server-side one-use flow state with a ten-minute expiry,
and safe local return paths. Reject replay and account-swapping attempts.
An OIDC callback is the protocol-specific exception to the rule against GET state changes;
its one-use state/nonce replaces the ordinary form-CSRF mechanism.

Accept email verification from a validated Google assertion only for verified Gmail addresses
or verified Workspace addresses with a hosted-domain claim. Other addresses require the
website's existing email proof before project creation or invitation acceptance. Never infer
Workspace control from an email suffix alone. Existing identity lookup uses sub even if its
reported email changes; keep the application email stable, mark it for re-verification on
a mismatch, and suppress email until reverified. Email changes are outside v1.

Google Cloud client credentials and consent configuration are needed for live testing.
Local tests use provider fixtures; staging validates real redirect, consent, and mobile
browser behavior. See research.md and contracts/http.md for provider references and routes.

### Reminder and UI Behavior

A server-rendered task list offers title, optional reminder time, and save without navigating
away. The browser displays an explicit timezone. Require confirmation of an ambiguous local
time and reject nonexistent times. All server comparisons use UTC instants.

Load due reminders in the initial authenticated page response, then fetch the current due
list every two seconds while visible and connected, with an immediate refresh on focus,
reconnection, and local task mutation. Replace the old list rather than appending duplicates.
Clear private panels on session/access errors. Never rely on a stale cached reminder as proof
of access. Render task titles as text and preserve input on validation/conflict errors.

A due-list query joins incomplete tasks to current membership and assignment. Website
visibility is independent of worker/provider health. The worker materializes email occurrences
and rechecks every condition at dispatch. After confirmed acceptance, preference toggles or
refreshes do not resend the same occurrence.

### Verification and Traceability

| Requirements | Verification work |
|---|---|
| FR-001–004 | Registration, verification, hashing/log review, limits, reset boundaries, two-device logout/reset |
| FR-005–012 | Project membership matrix, invitation lifecycle, concurrent ownership/acceptance/removal |
| FR-013 | Owner-only group changes, cross-project membership rejection, visibility invariant |
| FR-014–016 | Task forms, persistence, assignee authorization, optimistic conflicts, duplicate-save replay |
| FR-017–022 | Preference and mutation matrix, due-list refresh, worker crash/retry, webhook ordering, privacy |
| FR-023 | Every SC and story scenario mapped to recorded release evidence |
| FR-024–028 | Google signup/return/linking, collision and invalid callback cases, verified invitations, logout/recovery |

Run real PostgreSQL tests for all locking scenarios. Fakes prove deterministic timing
boundaries and failure paths; live provider acceptance and real-browser observations prove
the external timing criteria. Manual usability samples remain separate from browser automation.

## Complexity Tracking

No constitution violations require exceptions. The durable outbox and dispatch locking are
needed to meet retry and privacy requirements. Monitor dispatch lock latency and worker backlog
before increasing throughput.

Implementation note: same-origin referrer policy preserves browser Origin/Referer behavior
needed for CSRF-protected form POSTs while withholding paths on cross-origin navigation.
OAuth flow state is application-owned and session-bound; signed identity validation uses
the maintained allauth provider library. No alternate token-login endpoint is exposed.
