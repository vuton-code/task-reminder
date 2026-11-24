# Quickstart and Validation Guide

The local Django application is implemented and has been exercised against PostgreSQL.
The validation commands below include both implemented local tests and release checks that
still require external credentials, real devices, and human participants.
Consolidated test modules are under tests/test_*.py and tests/e2e/.

## Prerequisites

- Docker Desktop with Compose and Linux containers, or Docker Engine with Compose on Linux.
- Available local ports 8000 and 5432.
- For live email trials, a verified Resend domain, sending credential, webhook signing secret,
test recipient addresses controlled by the tester, and an HTTPS callback address.
- Record browser/OS versions and use a real iOS Safari and Android Chrome device for phone
acceptance. Automated WebKit alone does not prove iOS home-screen behavior.

## Local Setup Contract

From the repository root, after implementation:

```powershell
Copy-Item .env.example .env
docker compose up -d db
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_demo
docker compose up web worker
```

The example environment defines DJANGO_SECRET_KEY, DATABASE_URL, APP_BASE_URL,
ALLOWED_HOSTS, EMAIL_BACKEND_MODE=fake, RESEND_API_KEY, RESEND_WEBHOOK_SECRET,
EMAIL_FROM, OUTBOX_ENCRYPTION_KEY, and TRUSTED_PROXY_CIDRS. Development mode permits
local HTTP only. Production uses secure cookies and HTTPS.

seed_demo creates isolated fixture users with owner/manager/member roles in two projects,
prints generated development-only credentials, and provides a fake outbox viewer restricted
to local development. It does not seed a production environment. The fake transport allows
verification and reset links to be exercised without sending external email.

Open http://localhost:8000. Worker and website share the same database. Re-running seed_demo
must update the named demo fixture predictably without duplicating memberships or tasks.

## Automated Checks

```powershell
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web pytest --ignore=tests/e2e --ignore=tests/test_timing.py
docker compose run --rm web python -m playwright install --with-deps chromium firefox webkit
docker compose run --rm web pytest tests/e2e tests/test_timing.py
```

Use PostgreSQL for integration tests. Transaction tests exercise separate connections and
real lock races. The browser test fixture starts a test web server and worker against an
isolated test database. Clock-controlled tests prove exact expiry and timing boundaries.

Expected outcomes include all role-matrix denials, forwarded invitation rejection, reset
single-use and all-session revocation, no task leaks after departure, conflict detection,
and deduplicated retries. Refer to contracts/http.md and contracts/email-worker.md.

## End-to-End Scenarios

1. Register, verify email, sign in, create two projects, and save a self-assigned task.
Refresh and confirm persisted values and timezone.
2. Invite an existing verified account to the second project. Before acceptance inspect
only project name/inviter. Accept as member; verify independent role in each project.
3. Promote to manager with only invitation permission. Exercise own invitation cancellation,
denied reassignment, denied role change, and denied cancellation of another sender's invitation.
4. Grant assignment permission; assign work. Create a group as owner and confirm group
membership changes no permissions. Leave the project and verify immediate denied access.
5. Transfer ownership to an existing manager, then leave as former owner. Race competing
transfers and verify exactly one owner remains.
6. Enable email; schedule a reminder; observe fake acceptance and active-tab visibility.
Complete, reschedule, reassign, disable email, and remove the assignee in separate trials
immediately before dispatch. Check suppression and new-recipient behavior.
7. Open an old reminder link after departure. Verify sign-in/access checks and no private task.
8. Sign in on two devices. Ordinary logout ends one session. Password reset ends both.
Test thresholds and expiry using the specified clock-controlled cases.
9. Restart the worker at each handoff stage using the fake provider's fault controls.
Replay webhook events and advance the clock beyond idempotency retention. Verify no blind resend.

## Measured Acceptance

```powershell
docker compose run --rm web python manage.py benchmark_reminders --mode fake --count 100 --output artifacts/reminder-results.json
```

The command prepares schedules, starts controlled observation, and records raw UTC timestamps,
eligibility, outcomes, suppressions, and summary counts. Use fake runs for regression only.

After configuring live email and an authenticated signed webhook receiver:

```powershell
docker compose run --rm web python manage.py benchmark_reminders --mode live --count 100 --output artifacts/live-reminder-results.json
```

Live mode must require an explicit configured allowlist of controlled test recipients. It must
not send to ordinary project members. Record accepted timestamps separately from observed
responses and later delivery events. Require 99/100 acceptance in [0,60] seconds.

Observe 100 active-tab reminders per supported device category, require 99/100 in [0,10]
seconds. Observe 100 returning visits per category, require 99/100 within five seconds.
Include exclusion cases for completed tasks and departed projects. Record server/client
clock offset and raw samples, including early, late, and missing results.

For task entry and invitation acceptance, conduct ten manual trials per supported device
category with at least three people and fixed prompts. Require respectively 9/10 within
20 seconds and 9/10 within 15 seconds. Do not substitute automated typing for these trials.

Use the plan's 50-active-tab fixture and separately run the 100-reminder burst to reveal
capacity limits. A failed trial requires a recorded diagnosis and a new complete run,
without deleting the original evidence.

## Release Evidence

Maintain a mapping for FR-001–028, all story scenarios, and SC-001–010 in the implementation's
test reports. Include exact versions, environment, raw timings, security/storage/log review,
and results. Every isolation/security/lifecycle check must pass. Restore a backup into an
isolated environment and verify membership and accepted-send identities before deployment.

Operational credentials and live verification are required before release; they do not
prevent local implementation or fake-provider testing.

## Google Sign-in Validation

After implementation, configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the local
environment. Register an OAuth web client and consent settings in Google Cloud. Configure
the exact development redirect http://localhost:8000/accounts/google/login/callback/ and
the equivalent HTTPS staging redirect. Keep credentials outside source control.
Use explicitly authorized test accounts while the consent application is in testing.

Local automated tests use signed provider fixtures and mocked code exchange. Test valid and
invalid state/nonce, issuer, audience, signature, expiry, replay, cancellation, changed email,
email collision, concurrent profile creation, and recent-password connection requirements.
Use provider library validation in tests, not a fake that bypasses validation entirely.

On staging, sign in with a new controlled Google account and verify no username/password
registration step; return and confirm the same profile. Connect a matching existing password
account after reauthentication. Verify no collision auto-merge and no invitation auto-accept.
Exercise a mismatched invitation email and an external Google email requiring website proof.
Repeat logout and password-reset tests across Google-authenticated and password sessions.

For SC-010, record 100 successful Google-return visits per supported device category and
require 99 within five seconds from receipt of the provider result to correct due reminders.
Record provider-screen time separately. Include real phone and home-screen launches.
Google credentials and authorized test accounts are prerequisites for live verification only.

## This Windows Workspace

Python 3.13 is installed in .venv and PostgreSQL 17 binaries/data are under the ignored
.runtime directory. The local database listens only on 127.0.0.1:55432.
The existing .env contains generated local secrets. Keep its contents private.

If the local PostgreSQL process is stopped, start it from the repository root:

```powershell
& .runtime/postgresql/pgsql/bin/pg_ctl.exe -D .runtime/pgdata -l .runtime/postgres.log -o "-h 127.0.0.1 -p 55432" start
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Run the worker in a second terminal:

```powershell
.venv/Scripts/python.exe manage.py run_reminder_worker
```

Visit http://localhost:8000. Local verification/invitation messages are available at
http://localhost:8000/dev/outbox when DEBUG=true and EMAIL_BACKEND_MODE=fake.
Register an account, open its verification message there, and continue to the project list.
The worker must run to mark invitation email as accepted.

Run local checks with:

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe -m pytest -q
```

To stop the local database after stopping web/worker processes:

```powershell
& .runtime/postgresql/pgsql/bin/pg_ctl.exe -D .runtime/pgdata stop
```

Google and live email remain unconfigured. The Continue with Google button explains this
until GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set. Keep EMAIL_BACKEND_MODE=fake until
a verified sending domain, RESEND_API_KEY, EMAIL_FROM, and RESEND_WEBHOOK_SECRET are configured.
Configure BENCHMARK_RECIPIENTS explicitly before a live benchmark. External credentials are
not required for the local application or provider-fixture tests.

Implementation uses Referrer-Policy: same-origin so browser form POSTs retain their origin
for CSRF validation while cross-origin navigation omits private paths. Token URLs and OAuth
query values are redacted by config/logging.py.

## Additional local validation tools

Install all three browser engines and the pinned accessibility auditor before the full suite:

```powershell
.venv/Scripts/python.exe -m playwright install chromium firefox webkit
New-Item -ItemType Directory -Force .runtime/a11y | Out-Null
pnpm.cmd --dir .runtime/a11y add axe-core@4.14.0
.venv/Scripts/python.exe -m pytest -q --junitxml=artifacts/test-results.xml
```

The test settings refuse non-development/remote databases and always use test_task_reminder.
The complete suite includes 50 visible tabs and 10,000 fixture tasks. Focused tests can be
run during edits. Review IMPLEMENTATION_STATUS.md and tests/acceptance-map.md before repeating
large checks. See ops/README.md for backup restore and deployment configuration.
Modern Web Guidance is installed under .agents/skills/modern-web-guidance with a Widely
available browser baseline. User credentials and private data are never part of guidance queries.
