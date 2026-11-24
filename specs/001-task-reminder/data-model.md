# Data Model — task-reminder

All identifiers are UUIDs except Django's opaque session identifiers. Times are timezone-aware
UTC instants. Text is escaped on output. Secret tokens use cryptographic randomness and are
stored as digests; temporary outbound token payloads are encrypted with a separate environment
key and removed after their terminal delivery state or expiry.

## Entities and Constraints

| Entity | Fields and relationships | Constraints |
|---|---|---|
| Account | normalized username, normalized email, email_verified_at, password hash or unusable-password marker, auth_generation, email_enabled=false, display_timezone | Unique case-folded username and email; Google-only usernames are internally generated; verification required for project creation/acceptance; no account deletion flow in v1 |
| Google identity (allauth SocialAccount) | account, provider=google, uid=validated sub, last_seen_email, linked_at | Unique (provider,uid); one Google identity per application account in v1; never linked through email match alone |
| Sign-in flow state | state digest, session binding, nonce, PKCE verifier, intent=login/connect, target account for connect, safe return path, issued_at, expires_at, consumed_at | One-use server-side state with ten-minute expiry; temporary secrets excluded from logs and removed on consumption/expiry |
| Session | Django database session, account ID, auth_generation snapshot, expiry | Active generation must equal current account generation on every authenticated request |
| AccountProof | account, purpose=verify/reset, token_digest, issued_at, expires_at, consumed_at | Unique digest; verify expires in 24h, reset in 30m; valid only when now < expiry and unconsumed |
| Project | name, owner_account_id, version, created_at | Non-null owner; owner must have active membership; owner authority derives from this pointer |
| Membership | project, account, role=member/manager, can_invite, can_assign, version, joined_at, left_at | Partial unique active (project,account); fresh invitation creates new membership identity after departure; member flags false |
| Invitation | project, inviter, recipient_email, token_digest, sent_at, expires_at, status, accepted_membership_id | Unique digest; pending/accepted/cancelled; expiry derived from now >= expires_at; expiry seven days after successful send acceptance |
| Group | project, name, version | Case-folded name unique within project; owner-managed |
| GroupMembership | group, membership | Unique pair; matching project and active membership required |
| Task | project, title, description, assignee_membership nullable, status=open/completed, reminder_at nullable, version, schedule_generation, assignment_generation | Title 1–200 trimmed characters; description at most 10,000; assignee must be active in same project; version required for edits |
| EmailOccurrence | task, schedule_generation, assignment_generation, recipient_membership, due_at | Unique tuple for task/generations/recipient; immutable identity |
| OutboundMessage | purpose, related proof/invitation/occurrence, recipient, payload_digest, encrypted_payload, idempotency_key, state, first_attempt_at, next_attempt_at, lease_owner, lease_until, provider_id, accepted_at | Unique logical purpose/occurrence and unique idempotency key; frozen payload after first attempt |
| DeliveryAttempt | outbound message, started_at, finished_at, result, provider_status, sanitized error | Append-only attempts; no credentials, plaintext tokens, or task descriptions |
| DeliveryEvent | provider event ID, provider message ID, event_type, event_time, received_at | Unique provider event ID; preserve event history and out-of-order arrival |
| RateBucket | dimension=account/source, keyed identifier, failure_count, window_start, blocked_until | Atomic updates; exact spec thresholds; identifiers keyed-hashed for storage where feasible |
| MutationReceipt | actor, operation, client key, input digest, resource ID, result code | Unique actor/operation/key; different input with reused key is a conflict |

Project names are 1–100 trimmed characters and group names 1–80. Emails use one documented
normalization policy shared by registration and invitations. Do not invent provider-specific
dot or plus-address equivalence. A user's verified address must match under that policy.

Use database uniqueness, check constraints, and foreign keys wherever possible. Same-project
relationships use composite foreign keys through migrations or explicit constraint triggers.
A deferred constraint trigger verifies that each project owner has active membership at commit.
Service-level checks provide friendly errors; the database rejects invalid concurrent writes.

## State Transitions

- Account proof: issued -> consumed or expired. Reset consumption, password update, auth-generation
increment, and invalidation of other outstanding reset proofs occur in one transaction.
- Invitation: prepared (no valid sent invite) -> pending on provider acceptance -> accepted,
cancelled, or expired. Cancellation can also invalidate an invitation awaiting email handoff.
Record send acceptance time from provider reconciliation if a response is lost. Immediate
link arrival may reconcile pending send status before evaluating acceptance.
- Membership: active -> departed. Rejoining creates a new active row from a fresh invitation,
so old invitation and reminder identities never regain authority.
- Ownership transfer: lock project and both memberships; require target is an active manager;
replace owner pointer and set the former owner's manager flags to both true in one transaction.
- Task edit: require expected version; increment version on success. Schedule change increments
schedule_generation. Assignee change increments assignment_generation. Completion cancels
pending occurrences. Departure clears assignee, increments assignment_generation, removes
group membership, and invalidates pending sends in one project transaction.
- Due-list visibility is derived from current task status, reminder_at <= server time,
current assignee, and active membership. It is never an independently stale authorization list.
- Outbound state: pending -> prepared -> dispatching -> accepted, rejected, unknown, suppressed,
or held. Rejected transient attempts can return to pending. Unknown enters reconciliation.
Later delivered/bounced/failed events annotate acceptance without erasing its timestamp.
- Accepted occurrences are never reset by preference changes. Enabling email can enqueue a
still-due occurrence that was never attempted; it never resends an accepted occurrence.

## Transaction Ordering and Concurrency

Use a consistent order for domain mutations: project, account rows in ID order when needed,
memberships/invitations, task rows in ID order, occurrences, outbound messages. A preference
change takes its account lock only and must not subsequently request project locks.
Account recovery similarly avoids project locks.

Job claiming is a separate short transaction over outbound rows using SKIP LOCKED and a
30-second lease. Release claim locks before obtaining domain locks. Write the durable attempt
marker before handoff. Dispatch reacquires project/account/task/message locks in the order
above, rechecks the lease and all eligibility, then holds them through a maximum five-second
provider request. A crashed dispatch lease becomes unknown and is reconciled.

All operations changing role, membership, task state, or schedule must acquire the project
lock. This intentionally serializes project mutations in v1. Email preference changes serialize
with dispatch through the account lock. Successful mutations committed before dispatch are
therefore observed. A provider request that has begun may finish after a timeout; subsequent
removal cannot recall that in-flight request.

Authorization for mutations is checked again after locks. Task optimistic versions reject
stale updates with a conflict. Retried create/accept/transfer operations use mutation receipts
and recheck current authorization before returning a saved result. Replayed invitation
acceptance never recreates departed membership.

## Indexes and Recovery

Index active membership by account/project, tasks by project/status and assignee/reminder_at,
pending messages by next_attempt_at, proof/invitation token digests, session expiry, provider
message IDs, and delivery event IDs. Poll oldest due jobs first. Sweep overdue eligible tasks
periodically to repair a missed occurrence, using unique constraints for deduplication.

Retention cleanup removes expired proof secrets and encrypted outbound payloads, expires
sessions and mutation receipts after a documented period, and preserves enough delivery
metadata to prevent confirmed-send duplication. Task content is excluded from operational
logs. Backup/restore validation includes memberships, schedules, and durable send outcomes.

## Google Account Lifecycle

An unlinked validated Google identity creates a profile only if its normalized email is unused.
Create profile and SocialAccount atomically, with database uniqueness resolving concurrent
callbacks. Use an unusable password marker and generated internal username. A colliding email
returns an explicit existing-account connection flow and grants no session for that account.
Do not duplicate the identity in a second custom provider table.

Connection locks the current account and rechecks recent password authentication and flow
intent, matching verified email, and provider-subject uniqueness before committing.
A provider identity linked to another account cannot be moved by this operation.

Returning identity lookup uses provider/sub. Changed Google email does not rewrite the
application email or membership. Clear email verification on mismatch and require a fresh
proof of the stored address before email sending, new project creation, or invitation acceptance.
Existing project permissions continue to come from memberships.
Local password reset applies only to usable local passwords and revokes all website sessions.
Unlinking and adding a local password to a Google-only account are outside this release.
