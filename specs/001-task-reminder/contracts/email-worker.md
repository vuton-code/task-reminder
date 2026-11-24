# Email Provider and Worker Contract

## Provider Operations

The production adapter supports send(message, idempotency_key), retrieve(provider_id), and
verify_webhook(raw_body, headers). It returns explicit accepted, rejected, or unknown outcomes.
The fake adapter implements acceptance, rejection, timeout-before-acceptance,
acceptance-with-lost-response, delayed webhook, and duplicate/out-of-order webhook scenarios.

An accepted outcome contains provider ID and acceptance evidence timestamp. Prefer the provider
event timestamp when available; record response observation time separately. Never send before
the scheduled UTC instant. A later webhook can refine acceptance evidence without rewriting
the original observation. Record when acceptance time is uncertain.

Reminder email includes only generic wording, escaped title, and a same-origin access-checked
task URL. Sender and application base URL come from trusted configuration.
Email descriptions, group lists, and other task details are excluded.

Verification, invitation, and reset mail use the same durable transport with purpose-specific
payloads and authorization/lifecycle validation. Invitation acceptance is enabled only after
its send is accepted; seven-day expiry starts from that acceptance time. Account-proof expiry
starts at issue and expired proofs must not be sent. These transactional emails do not depend
on the optional task-reminder email preference.

## Durable Dispatch Protocol

1. Task transactions create or invalidate occurrence/outbox work atomically. A periodic sweep
also discovers overdue eligible work using unique occurrence keys.
2. A worker claims a due message in a short transaction using SKIP LOCKED and a lease. Persist
a stable idempotency key and attempt marker before any network call.
3. Reacquire domain locks in the order from data-model.md. Recheck lease ownership and current
task generation, assignment, membership, verified recipient email, status, time, and preference. Suppress invalid work.
4. Freeze recipient and exact payload before first send. Keep domain locks through a bounded
five-second provider request so completed changes before handoff are observed.
5. Record accepted provider ID, definitive rejection, or unknown outcome. Release locks.
Worker crashes after the durable attempt marker lead to reconciliation, never blind retry.

The boundary is provider handoff initiation after the eligibility check under locks.
A change completed before that boundary governs the send. A change competing with handoff
waits for serialization. An in-flight external request can finish after a local timeout.
A successfully delivered email cannot be recalled.

## Retries and Reconciliation

- Definitive temporary rejections retry with delays of 2, 5, 10, 20, then 60 seconds and
provider Retry-After when supplied. Count all elapsed time against the 60-second target.
- Definitive permanent rejections stop automatic attempts and retain a failure reason.
- For unknown acceptance, first inspect matching signed events or retrieve a known provider ID.
Use a correlation tag containing only an opaque message ID to associate an early webhook.
- If no acceptance evidence is available, replay the identical payload with the same key
only within the provider's 24-hour window, only while still eligible, and only when payload
and recipient remain unchanged. Provider deduplication reconciles the prior attempt.
- If eligibility has changed, do not replay. Continue read-only reconciliation.
- Once 24 hours have elapsed from first attempt, unresolved messages enter held state for
operator review. They must not automatically get a new key. Confirmed accepted messages never
resend, even after deduplication retention expires.
- Changes to title or other submitted fields during unknown outcome prevent payload replay.
A confirmed accepted message retains its historical title. New schedule/assignment generations
have separate occurrences, subject to the current task state.
- Workers use a 30-second lease and a heartbeat. Expired dispatching leases are unknown,
not automatically pending. Crash tests cover before call, during call, and after acceptance.

## Webhooks

Verify signatures against the exact raw body before parsing or recording a trusted outcome.
Use provider event IDs for durable deduplication, reject invalid signatures, and enforce the
verification library's replay timestamp policy. Commit the receipt before responding success.
Unknown provider IDs can be associated by opaque message tags; otherwise hold the event for
reconciliation. Events may arrive before the send response or out of order.

Record acceptance and later delivered, bounced, delayed, complained, suppressed, and failed
events separately. A delivered event means recipient mail-server acceptance, not user reading.
Repeated events must not create jobs or alter task state. No webhook may grant membership.

## Operational Checks

Worker heartbeat, oldest pending age, due backlog, acceptance latency, unknown/held count,
and rejection/later-failure counts are observable without logging private content.
Alert when heartbeat is older than 15 seconds or oldest due work exceeds 30 seconds.
Provider quotas are checked before live trials. Queue backlog and throttling count toward
delivery metrics. Daily backups and a restore rehearsal include accepted-message identities.

Run one worker initially, with bounded concurrency added only after capacity measurement.
Polling active website reminders remains independent of this worker and email service.

## Contract Tests

Prove identical retries return one accepted occurrence, duplicate webhooks are harmless,
unknown acceptance survives restart, cancellation before dispatch suppresses sending,
departure never restarts an old occurrence, and changed payloads are not replayed with a
previous key. Demonstrate long-outage held-state behavior without waiting 24 real hours.
