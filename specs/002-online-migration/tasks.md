# Implementation checklist — GitHub + Supabase pilot

Created: 2026-11-23
Source: [plan.md](plan.md) and [spec.md](spec.md).
Status: Planned; no implementation tasks below are complete.
Priority: prove authentication and project isolation before building full product screens.

## Execution rules
- Keep the existing Django application, database and configuration intact.
- Follow the approved pilot exceptions: Google-only, manually sent invitation drafts,
  website-only reminders, personal/noncommercial testers.
- Work through phases in order. A checkbox requires the stated evidence, not just code.
- Use synthetic fixtures and an isolated test database. Never reset the live pilot database.
- Store sanitized evidence under artifacts/pilot/ and map each requirement to tests in
  specs/002-online-migration/verification.md. Exclude personal data and secrets from Git.
- Apply Modern Web Guidance when implementing frontend changes. Run focused checks per
  change and a full regression at the pilot release gate; no duplicate implementation-only tests.
- Ask setup questions individually. Never request secret values in chat.
- Local/mocked success is not live Google, hosted timing or real-device evidence.

## Phase 1 — Minimal foundation (before authentication)

- [ ] P001 Confirm repository name/visibility, Supabase region/project and fresh pilot data versus
  explicitly approved import. Record in setup.md; do not infer permission to publish source or data.
- [ ] P002 Inspect repository state and prepare ignore rules for .env, .runtime, dumps, local outbox,
  browser auth files and private screenshots. Scan tracked files/history before any remote push.
  Evidence: sanitized publication manifest; never print discovered secrets.
- [ ] P003 Scaffold web/ with Vite, React, TypeScript and locked supported dependencies; create
  public-config example and scripts for build/typecheck/lint/test. Build at / and /repository/.
  Evidence: both builds and a dist secret scan. Preserve root Django tooling.
- [ ] P004 Create supabase/ migration/config structure, isolated synthetic fixtures and SQL test
  runner. Verify local Docker availability; use isolated CI if unavailable on Windows.
  Evidence: clean schema rebuild and explicit guard against destructive tests on hosted pilot data.
- [ ] P005 Create verification.md with GA-01–05, IN-01–07, WR-01–12 and inherited project/task/group
  requirements. Mark hosted/manual checks pending; do not import old Django passes as migration passes.

## Phase 2 — Authentication and session security (first implementation milestone)

Dependencies: P003–P005; hosted tasks also require P001 and configured service access.

- [ ] P006 Configure Google as the only Supabase sign-in provider; disable password/email,
  anonymous and other providers. Document OAuth client/test audience and exact callbacks in
  setup.md without secrets. Evidence: dashboard/config review and direct unsupported-endpoint tests.
- [ ] P007 Prove server-owned verified Google identity in a minimal schema/RPC spike. Reject
  missing Google identity, unverified/mismatched email and forged editable user metadata.
  Evidence: adversarial SQL/API tests plus managed-staging verification. Resolve uncertainty
  before expanding the application; do not fall back to trusting browser verification flags.
- [ ] P008 Implement unique profile bootstrap from authenticated identity, with server-controlled
  immutable user id and bounded display-name/timezone preferences. Evidence: first/repeated and
  concurrent sign-in produce one profile; no public email directory or email-based Django merge.
- [ ] P009 Implement PKCE sign-in, root callback processing and hash-route restoration in web/.
  Validate relative return routes, clear exchanged codes, handle cancellation/replay/failure, and
  preserve invitation return state without auto-acceptance. Evidence: callback/open-redirect tests
  at both base paths; Google credentials are entered only at Google.
- [ ] P010 Implement locked-down private live-session helper checking JWT session_id against
  auth.sessions and auth.uid(). Use fixed search_path, least privilege and restricted grants.
  Evidence: missing/mismatched/ended session denied; callers cannot read other session rows.
- [ ] P011 Apply live-session checks to every application read and RPC; implement local-scope
  sign-out with cache clearing and truthful handling of server failures. Evidence: replay captured
  access JWT immediately after sign-out; all application data denied while a second session works.
- [ ] P012 Add auth states, Google recovery guidance and authenticated navigation; no password,
  magic-link or local recovery UI. Evidence: keyboard navigation and GA-01–05 automated checks.
- [ ] P013 Run live Google first/return sign-in with separate testers and verify identity/bootstrap,
  sign-out and callback URLs. Record sanitized evidence; no broad Gmail/Calendar scopes.

**Gate A:** P007 and P010–P011 security proofs must pass before project feature implementation.
P013 may await credentials while isolated tests progress, but blocks hosted pilot release.

## Phase 3 — Project authorization and transactional core

Dependencies: Gate A; no full task/invitation UI until Gate B passes.

- [ ] P014 Migrate projects, active memberships, groups, tasks and private invitation/receipt
  tables, with indexes, constraints, server timestamps and versions. Evidence: fresh migration,
  invalid cross-project relationship rejection and uniqueness tests.
- [ ] P015 Default-deny RLS; grant only scoped reads and reviewed RPC execution. Revoke generic
  domain writes and private-schema access; audit views, sequences, helpers and PUBLIC/anon grants.
  Evidence: raw table/API/RPC attacks cannot change roles, owner, creator or verification state.
- [ ] P016 Implement atomic project creation and project/member list reads; establish one owner
  membership in the same transaction. Evidence: concurrent/retried creation, empty states and
  outsider denial; profile display limited to permitted contexts.
- [ ] P017 Implement independent manager invitation/assignment grants and owner-only role changes.
  Evidence: complete owner/manager/member/outsider matrix across two projects, including a manager
  with no delegated permissions and immediate enforcement after grant removal.
- [ ] P018 Implement removal/leave and ownership transfer with project-first lock ordering and
  expected versions. Clear task assignees and group memberships on departure. Evidence: owner
  cannot leave before transfer; concurrent transfer/remove attempts preserve exactly one owner.
- [ ] P019 Implement owner-only group mutations with current same-project members. Evidence:
  cross-project additions fail, group deletion preserves tasks, grouping grants no authority.
- [ ] P020 Implement exact-name/version confirmed owner-only project deletion and dependent cleanup.
  Evidence: unauthorized and stale-owner requests denied, old links fail, other projects/accounts
  remain intact, pending invites cannot restore access, retry cannot resurrect deleted records.
- [ ] P021 Exercise all project policies through authenticated direct API calls, not only SQL-owner
  tests or hidden UI controls. Include anonymous requests, forged IDs and captured stale JWTs.
  Evidence: complete permission matrix passes; any unauthorized disclosure blocks Gate B.

**Gate B:** P014–P021 pass before full workflows. Validate deployed policy grants again in staging.

## Phase 4 — Tasks and usable project screens

Dependencies: Gate B.

- [ ] P022 Implement task create/edit/assign/complete RPCs with current permission checks,
  expected versions and idempotency receipts. Derive creator on server and retain creation time.
  Evidence: forged assignee/creator, stale versions, duplicate save and concurrent mutation tests.
- [ ] P023 Implement timezone conversion with explicit repeated/nonexistent-time handling.
  Evidence: timezone changes preserve instants; DST and incorrect client-clock tests pass.
- [ ] P024 Build project navigation, role labels, member controls and groups using the scoped API.
  Evidence: every permitted workflow works; unauthorized choices hidden without weakening APIs.
- [ ] P025 Build task lists/detail/forms with visible Assign to, only permitted choices and
  preserved entered values on failure. Evidence: owner/member workflows and conflict recovery.
- [ ] P026 Reuse Projects Management Hub branding without subtitle, signed-in identity and mobile
  layout. Evidence: desktop/mobile review, keyboard checks and focused accessibility audit.

## Phase 5 — Draft-and-copy invitations

Dependencies: Gate B and authentication return-route support.

- [ ] P027 Implement token generation, digest lookup and encrypted token storage with server-only
  Vault key for authorized draft retrieval. Evidence: secrets absent from browser bundles/logs,
  tables inaccessible directly, retrieval denied after permission loss or invitation cancellation.
- [ ] P028 Implement idempotent creation and draft retrieval for owner/authorized inviter; enforce
  seven days from server creation. Evidence: repeat copies/reopening do not extend expiry,
  conflicting retries fail and duplicate submissions do not create duplicate invitations.
- [ ] P029 Implement narrow invitation preview, verified-email acceptance and cancellation RPCs.
  Evidence: IN-03–07 boundary/race/replay cases, including removed members and mismatched Google
  accounts. Anonymous preview reveals only project name/inviter, never tasks or member list.
- [ ] P030 Implement recipient/subject/message/expiry preview, Copy email and Copy link, success
  announcements only after successful copying, selectable fallback and no Sent wording.
  Evidence: exact paste output, denied clipboard, keyboard/mobile operation; no email API calls.
- [ ] P031 Complete Google-to-invitation journey and existing-account second-project acceptance.
  Evidence: explicit acceptance required, regular-member role, old memberships preserved and
  canceled/expired links show clear next steps.

## Phase 6 — Website reminders

Dependencies: P022–P026; permissions/session gates remain mandatory.

- [ ] P032 Implement paginated get_due_reminders with authoritative database time, current active
  membership/assignee and open-task filtering. Return server time, occurrence key, version and
  approved metadata. Evidence: future/ineligible tasks excluded and cursor boundaries stable.
- [ ] P033 Implement two-second active/connected polling with no overlapping requests, stale-response
  rejection and immediate login/focus/reconnect/mutation reconciliation. Evidence: duplicates,
  out-of-order responses, background/resume and offline/online cases; preserve keyboard focus.
- [ ] P034 Render due/creation dates with timezone abbreviations and Assigned by original creator;
  omit unknown historical metadata and standalone IANA timezone line. Evidence: initial and
  refreshed cards agree; reassignment does not alter creator/creation time.
- [ ] P035 Verify WR-01–12 end to end: completion, reschedule, reassignment, removal, departure,
  deletion and sign-out invalidate access/reminders correctly; stale/offline status is truthful.
- [ ] P036 Verify no email-reminder toggle promising delivery, email-dispatch worker, Cron sender,
  SMS/push or public development outbox in pilot artifacts. Local Django behavior stays unchanged.

## Phase 7 — Hosted rehearsal and release

Dependencies: prior phases; live credentials and setup choices required.

- [ ] P037 Add minimal-permission CI for locked build, types/lint, unit/SQL/API tests, three-engine
  Playwright and axe. Pin action versions; restrict deployment and never expose secrets to forks.
  Evidence: reproducible successful pipeline and clean artifact/publication audit.
- [ ] P038 Prepare reviewed Supabase migrations and Pages deployment workflow as separate steps.
  Publish web/dist only after explicit deployment readiness review; record build/schema/config
  versions. Evidence: /repository/ direct links, refresh, callbacks and assets work on hosted pilot.
- [ ] P039 Run hosted direct API project/session isolation and Google tester journeys. Evidence:
  all security cases pass on deployed configuration, not just fixtures. Collect no secrets in reports.
- [ ] P040 Measure task entry 9/10 <=20s and invitation acceptance 9/10 <=15s using original manual
  per-device/three-person conditions; keep all failed attempts in results.
- [ ] P041 Measure active reminders 99/100 in [0,10]s and returning/Google-return visits 99/100 <=5s.
  Include specified device categories and record cold starts/reconnect conditions honestly.
  Hosted quota/cold-start failures are not silently excluded or labeled acceptable performance.
- [ ] P042 Check physical mobile/home-screen and screen-reader usability alongside desktop browsers.
  Evidence: keyboard/focus/error handling and readable reminder cards, not viewport emulation alone.
- [ ] P043 Measure polling load/egress, confirm free quotas and inactivity behavior, redact logs and
  write troubleshooting/version instructions. Evidence: documented tester capacity and limitations.
- [ ] P044 Export and restore application schema/data in isolation; document Auth identity recovery
  separately. Rehearse rollback with backward-compatible schema and online-write considerations.
  Evidence: restored counts/relationships and no accidental writes to the pilot database.
- [ ] P045 Review final pilot with user; document Google-only/manual-invitation/website-only scope,
  unresolved limitations and noncommercial use. Publish approved release and run post-deploy smoke
  checks. Do not count deferred email/password requirements as passed full-product requirements.

## Render portability checks now; cutover later

- [ ] P046 Test production build/routing at / as well as /repository/; verify no github.io literal in
  domain logic and all invitation links derive from PUBLIC_APP_URL. Evidence: automated base-path tests.
  Dependency: P003/P009; may be completed before hosted rehearsal.
- [ ] P047 Write Render Static Site deployment/cutover runbook: same frontend and Supabase IDs,
  exact new callback URLs, required re-sign-in on new origin, old invitation-link forwarding to
  a fixed trusted host, and rollback. Dependency: P038/P044. Documentation only; do not deploy Render.

Future commercial cutover is NOT authorized in this checklist. Before that phase, review hosting
terms, privacy/terms, monitoring, backups, capacity, identity scope and optional external email.
GitHub source repository remains usable when commercial hosting moves to Render.

## Immediate next action

Start with P001 (one setup question at a time), then complete the minimal scaffolding and
Gate A authentication proof. Do not rewrite every screen before verifying server authorization.

## Completion summary

47 planned tasks; 0 completed. Gates A/B prioritize security. Hosted/manual/release tasks remain
pending until their evidence exists. This checklist is a planning artifact, not an implementation claim.
