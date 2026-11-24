# Acceptance evidence

Updated 2026-11-15. Local implementation is verified with PostgreSQL, provider fixtures and
real browser engines. Public release still requires the external/manual gates below.
Tests and migrations are consolidated; proposed task-list filenames are not one-to-one
with the actual modules. Final integrated suite: 161 passed in 158.89 seconds. Latest totals and raw evidence are in artifacts/test-results.xml
and artifacts/automated-results.json.

## Requirement coverage

| Requirements | Evidence under tests/ |
|---|---|
| FR-001 | test_lifecycle_edges.py, test_http_complete.py, test_foundation.py |
| FR-002–004 | test_security.py, test_security_complete.py, test_http.py, e2e/test_collaboration.py |
| FR-005–007 | test_permission_matrix.py, test_foundation.py, test_database_integrity.py |
| FR-008–010 | test_workflows.py, test_lifecycle_edges.py, test_remaining_permissions.py, test_race_matrix.py |
| FR-011–012 | test_remaining_permissions.py, test_concurrency.py, test_permission_matrix.py, test_race_matrix.py |
| FR-013 | test_groups.py, test_permission_matrix.py, test_database_integrity.py, e2e/test_collaboration.py |
| FR-014–016 | test_workflows.py, test_http_complete.py, test_race_matrix.py, e2e/test_personal_tasks.py |
| FR-017–019 | test_reminder_reliability.py, test_remaining_permissions.py, test_race_matrix.py |
| FR-020 | test_operational_complete.py, test_http.py, e2e/test_collaboration.py |
| FR-021 | test_timing.py, test_http_complete.py, e2e/test_capacity.py |
| FR-022 | test_completion_gaps.py, test_transport_complete.py, test_provider_retry.py, test_race_matrix.py |
| FR-023 | This map, tasks.md, automated-results.json; release remains gated |
| FR-024–025 | test_google.py, test_google_protocol.py, test_google_complete.py |
| FR-026–028 | test_google_complete.py, test_security_complete.py, e2e/test_google_fixture.py |

## Every story scenario

Each number refers to the numbered acceptance scenario in spec.md. All listed automated
checks pass locally; provider/human/device portions remain pending where stated.

| Scenario | Concrete verification |
|---|---|
| US1.1 | Registration, mismatched confirmation, duplicate identity, verification GET/expiry, password login in test_lifecycle_edges.py and test_http_complete.py |
| US1.2 | Owner membership creation and database constraint in test_database_integrity.py; project navigation in e2e/test_personal_tasks.py |
| US1.3 | Browser save/persistence in Chromium, Firefox and WebKit; timezone and DST boundaries in test_lifecycle_edges.py |
| US1.4 | Completion/rescheduling in test_workflows.py and test_reminder_reliability.py; browser completion |
| US1.5 | HTTP conflict retains entered title; invalid registration preserves form in test_http_complete.py; error announcement in e2e/test_guidance.py |
| US2.1–3 | Verified recipient/preview, unauthorized identity and pending lifecycle in test_workflows.py, test_lifecycle_edges.py and e2e/test_collaboration.py |
| US2.4–5 | Owner/manager cancellation and expiry/replay in test_remaining_permissions.py and test_lifecycle_edges.py |
| US2.6–7 | 24 role/action combinations and revocation in test_permission_matrix.py; independent project authority in test_foundation.py |
| US2.8–9 | Departure, cleanup, owner transfer and blocked owner leave in test_remaining_permissions.py, test_permission_matrix.py and e2e/test_collaboration.py |
| US2.10 | Competing transfers and invitation accept/cancel/duplicate acceptance in test_concurrency.py and test_race_matrix.py |
| US3.1–2 | Shared task visibility and task completion authority matrix; personal browser journey |
| US3.3–4 | Reassignment recipient and revoked assignment permission in test_remaining_permissions.py and test_permission_matrix.py |
| US3.5–6 | Owner group CRUD, non-owner denial, same-project constraints and role invariance in test_groups.py, test_permission_matrix.py and e2e/test_collaboration.py |
| US3.7 | Departed assignee becomes unassigned and group membership disappears; queue suppression and reassignment tests |
| US4.1–2 | test_timing.py: 100 due reminders and 100 returning visits at each of two Chromium viewport sizes; physical devices pending |
| US4.3 | 100/100 fake-provider acceptance; escaped title-only content in test_operational_complete.py; live provider pending |
| US4.4–5 | Preference and five mutation/dispatch race pairs in test_reminder_reliability.py and test_race_matrix.py |
| US4.6 | Access-checked task links and denied departed-member browser requests |
| US4.7 | Signed bounce-before-sent events preserve both outcomes; rejection/failure/latency metrics |
| US4.8 | Worker crash after handoff, stable-key replay, read-only reconciliation, held state and paged overdue sweep |
| US4.9 | Completion/reschedule invalidation and current-state due queries |
| US5.1–2 | First-five tolerance, account/source limits, reset windows, recovery during delay and independent limits |
| US5.3–4 | Single-use proof, exact expiry, invalidated sibling proofs and ineligible recovery |
| US5.5–6 | Two-browser logout/reset and mixed Google/password session revocation |
| US5.7 | Argon2 unique hashes, sensitive URL log filter, private responses and reviewed token-redacting proxy configuration |
| US6.1–2 | Automatic profile creation, stable subject, concurrent first sign-in and browser fixture |
| US6.3–4 | Collision denial, recent password proof, explicit verified-email linking and mixed sessions |
| US6.5 | Invitation continuation remains preview-only; shared verified-email acceptance checks |
| US6.6 | Real signed-token library validation, wrong session/nonce, expiry, cancellation and replay |
| US6.7 | External-email verification proof required; provider assertions do not auto-verify external addresses |
| US6.8–9 | Website logout, reset of all mixed sessions, Google-only recovery never creates password |
| US6.10 | Local callback/browser flow passes; 100 live Google-return samples remain pending |

## Success criteria

| Criterion | Result |
|---|---|
| SC-001–002 | Manual trials with three people remain pending; automated typing is not substituted |
| SC-003 | Fresh fake benchmark passes 100/100; real service acceptance remains pending |
| SC-004–005 | Local active/returning samples pass; real phone/home-screen checks remain pending |
| SC-006–009 | Automated isolation, invitation, account and reminder matrices pass locally |
| SC-010 | Protocol/account/browser fixtures pass; live provider and return timing remain pending |

The active-tab test observes a 100-reminder burst with one observation timestamp, rather
than 100 independent scheduled instants. Raw observations are retained. Local capacity:
100 fixture accounts, 20 fixture projects, 10,000 tasks, 50 visible tabs, 100 sampled requests.
Capacity and fixtures are test conditions, not promised production limits.

## Operations and accessibility

- Fresh test-database migrations, existing local migrations, model drift and Django checks pass.
- Production-configured Django --deploy check passes without contacting external providers.
- Local backup restores into a new database; all eight domain/delivery tables match by count
  and hash. artifacts/restore-results.json retains the evidence.
- axe-core audit covers eight public/authenticated pages; artifacts/accessibility-audit.json.
- Core tasks and validation run in Chromium, Firefox and WebKit. Desktop/narrow screenshots
  are retained. Automated checks do not establish screen-reader or real-phone usability.
- No implementation extension hooks are configured.
- Docker/Gunicorn/nginx templates are prepared; Linux deployment execution is unverified.

Modern Web Guidance was installed from GoogleChrome/modern-web-guidance for this project.
Forms, accessible-error-announcement and accessibility guides informed autofill,
validation timing, password visibility, titles, navigation labels, tap targets and contrast.


## UI pass: Projects Management Hub

See `specs/001-task-reminder/ui-improvements.md` for criteria. Coverage:
- `tests/test_ui_improvements.py`: per-project role display, self-only assignment choices,
  forged assignment rejection, assignment timestamps, reminder metadata, invitation messages,
  owner-only confirmed deletion with CSRF, cleanup and cross-project isolation.
- `tests/e2e/test_ui_improvements.py`: account visibility, assignment controls, reminder polling,
  focus retention, responsive layout, axe checks, and no-JavaScript deletion in three engines.
- User reported all 19 core manual workflows passed. Reset-link reuse was not reported;
  automated reset coverage remains separate from user evidence.
