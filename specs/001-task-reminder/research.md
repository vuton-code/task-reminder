# Research — First Usable task-reminder

Research date 2026-11-13. Choices below resolve the technical context for planning.

## Application and Runtime

**Decision.** Python 3.13 and maintained Django 5.2 LTS patches, with server-rendered templates
and small JavaScript modules. Lock exact tested dependencies at implementation.
**Rationale.** Forms, authentication, CSRF, migrations, and sessions are available in one
application. Django 5.2 supports Python 3.13.
**Alternatives considered.** A separate JavaScript frontend plus API adds a deployment and
authentication boundary; a client-only application still requires trusted server authorization.
[Official compatibility documentation](https://docs.djangoproject.com/en/5.2/releases/5.2/)

## Transactional Storage and Work Scheduling

**Decision.** PostgreSQL 17 stores domain data and durable jobs. A supervised Django management
command claims due jobs using short transactions and SKIP LOCKED.
**Rationale.** Committing task changes and queue changes together avoids lost scheduling work.
Row locking serializes competing membership and dispatch decisions.
**Alternatives considered.** An in-process timer loses work on restart. A separate broker adds
infrastructure and a second consistency boundary at this scale.
[PostgreSQL locking](https://www.postgresql.org/docs/17/explicit-locking.html),
[Queue claiming](https://www.postgresql.org/docs/17/sql-select.html)

## Passwords and Sessions

**Decision.** Use Django password APIs with Argon2 first, database sessions, CSRF checks, and
an explicit account auth generation for reset-all-session semantics.
**Rationale.** Django provides maintained password hashing and password-change session
invalidation. The generation makes the reset contract explicit and testable.
**Alternatives considered.** Long-lived browser bearer credentials complicate immediate
revocation. A custom password algorithm has no role in this design.
[Password management](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/),
[Session authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/)

## Email Provider and Outcome Semantics

**Decision.** Use Resend with a verified sending domain, stable idempotency keys, signed
webhooks, and a local deterministic fake in tests.
**Rationale.** Successful send acceptance provides an identifiable outcome. Delivered events
refer to recipient mail-server acceptance. Keep bounces, delays, and later failures separate.
**Alternatives considered.** SMTP alone provides insufficient application-level duplicate
reconciliation for the specified crash/retry cases.
[Provider events](https://resend.com/docs/webhooks/event-types),
[Webhook verification](https://resend.com/docs/webhooks/introduction)

## Dispatch Boundary and Unknown Outcomes

**Decision.** Serialize task/member changes and the bounded provider handoff using database
locks. Persist an attempt marker before calling the provider. Recheck eligibility at handoff.
**Rationale.** A membership change completed before dispatch wins. An in-flight request may
already have been accepted even when its response is lost. Database commits and the external
send cannot be one atomic transaction; record uncertainty explicitly.
**Alternatives considered.** Checking membership only when queueing allows private sends after
departure. Blind retries can duplicate delivery.

Resend retains idempotency keys for 24 hours. Replay only an identical, still-authorized payload
inside that window. A changed payload or expired deduplication window requires reconciliation,
and unresolved jobs are held for operator review. Do not claim permanent exactly-once delivery.
[Idempotency contract](https://resend.com/docs/dashboard/emails/idempotency-keys)

## Website Reminder Updates

**Decision.** Render due reminders with the page and poll every two seconds while active,
refreshing immediately on visibility/connectivity changes.
**Rationale.** This fits the ten-second target without persistent streaming connections and
keeps website reminders independent of email jobs. Actual browser performance must be measured.
**Alternatives considered.** Streaming and WebSockets add connection lifecycle work. Browser
timers alone cannot be trusted to enforce schedule or authorization.

## Operational Defaults

**Decision.** Compose provides local web, worker, and PostgreSQL services. Production uses
always-on web/worker processes and managed PostgreSQL over TLS, with environment secrets,
backups, clock synchronization, and health checks.
**Rationale.** A sleeping process cannot reliably satisfy the reminder target. Deployment
credentials, domain, and provider capacity are verified before live acceptance trials.
**Alternatives considered.** Request-triggered or low-frequency scheduled execution risks
late reminders when users are absent.

These decisions specify a deployable shape without choosing a paid hosting account.
No unresolved technical clarification remains for task generation.

## Google Sign-in Addition

**Decision.** Use django-allauth's Google provider and authorization-code flow, enabling PKCE.
Email-based automatic authentication and connection stay disabled. Existing accounts connect
Google explicitly after recent local-password proof. Select a maintained compatible package
version and lock it during implementation.
**Rationale.** A maintained integration supplies the protocol flow while application adapters
enforce account collision and invitation rules.
**Alternatives considered.** Automatic merging by email would bypass explicit proof of the
existing account. Handwritten OAuth validation adds avoidable security-sensitive code.
[Google provider setup](https://docs.allauth.org/en/latest/socialaccount/providers/google.html),
[Connection configuration](https://docs.allauth.org/en/latest/socialaccount/configuration.html)

**Decision.** Key the connection by Google's stable subject. Accept verified email automatically
only when Google is authoritative for Gmail or a verified hosted-domain account. Other email
addresses use a website verification challenge.
**Rationale.** The subject remains stable when an email changes; a verified third-party email
claim can outlast control of that external mailbox.
**Alternatives considered.** Using email as the provider identity conflates identity with a
mutable address.
[Identity validation](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token),
[OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
