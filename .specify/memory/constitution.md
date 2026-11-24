<!--
Sync Impact Report
Version change: unratified template -> 1.0.0 (initial adoption).
Modified principles: five unnamed template slots replaced by
I. Authority Belongs to Each Project;
II. Membership Requires a Trustworthy Invitation;
III. Account Access Must Remain Secure;
IV. Reminders Must Reflect Current Work and Access;
V. Quality Must Be Defined and Demonstrated.
Added sections: Measurable Quality Targets; Development and Review; completed Governance.
Removed sections: none beyond template examples and placeholder instructions.
Follow-up TODOs: none. Detailed security limits belong in the security specification.
This report is temporary review material and is to be removed before committing.
-->

# task-reminder Constitution

## Core Principles

### I. Authority Belongs to Each Project

**Rule.** An account may belong to multiple projects. Every action must check the account's
current permissions in the relevant project. All project members can view every task.
Groups organize existing members without changing permissions.

The creator becomes the owner. Only the owner can change roles, remove members, or transfer
ownership. Owners may give managers permission to invite people and assign tasks. Regular
members may create tasks for themselves and update or complete tasks assigned to them.
Assigning work to others requires owner authority or manager assignment permission.

Members may leave voluntarily. An owner must transfer ownership to an existing manager before
leaving, promoting a member first if necessary.

**Reason.** People need predictable access even when their responsibilities differ across projects.

**Verification.** Confirm that a manager in Project A has only member permissions in Project B.
Test direct requests, reminder links, group changes, and access after departure.
Every isolation check must pass.

### II. Membership Requires a Trustworthy Invitation

**Rule.** Invitations are tied to the recipient's verified email address. Membership begins
when that person, signed in to a new or existing account, accepts a valid invitation.
Everyone joins as a regular member. Before acceptance, only the project name and inviter
are visible.

Invitations expire seven days after sending. Owners can cancel any pending invitation in
their project. Managers with invitation permission can cancel invitations they sent.
Cancellation takes effect immediately. Expired or cancelled invitations require a fresh invitation.

**Reason.** Joining must be deliberate, and forwarding an invitation must never grant another
person access.

**Verification.** Test acceptance with an existing account joining a second project. Confirm
that forwarded, expired, cancelled, and previously accepted invitations cannot create
unauthorized membership.

### III. Account Access Must Remain Secure

**Rule.** Username-and-password sign-in establishes account identity. Project authorization
must be checked separately.

Passwords must use a maintained password-hashing method with a unique salt and never appear
in logs. Failed sign-ins must be limited per account and per source, allowing several ordinary
typing mistakes before short delays and increasing delays for sustained failures.
Exact limits belong in the security specification.

Recovery uses a single-use link sent to the account's verified email, expiring after 30 minutes.
Recovery remains available during sign-in delays. A successful reset ends every session.
Ordinary sign-out immediately ends the current session.

**Reason.** Account protection must cover everyday mistakes, attempted abuse, recovery,
and shared-device use.

**Verification.** Inspect password storage and logs. Test repeated failures, expired and reused
reset links, and immediate rejection of requests using sessions ended by sign-out or reset.

### IV. Reminders Must Reflect Current Work and Access

**Rule.** Reminders go to the current assignee only while that person remains a project member.
Assignment, membership, task status, schedule, and channel preferences must be checked
before sending.

Users may enable email reminders. In-website reminders remain available while the website
is open or when it is next opened, including from a home-screen shortcut.
The initial scope includes these two channels.

Completion cancels pending reminders and removes active in-website reminders. Rescheduling
replaces the old schedule. Delivered reminder links require sign-in and current project access,
then show the task's current state.

Emails may contain the task title and a link. Descriptions and other private details stay
inside the website. An already-delivered title may remain in the recipient's inbox.

**Reason.** Reminders must remain useful as assignments, schedules, and membership change.

**Verification.** Queue reminders, then complete, reschedule, reassign, or remove the assignee
before sending. Confirm the resulting recipient, content, and schedule are correct and
former members receive no queued reminder.

### V. Quality Must Be Defined and Demonstrated

**Rule.** Every feature must have written acceptance criteria and a concrete verification method
before implementation. Required checks must pass before release. Any unauthorized access
blocks release until fixed.

**Reason.** A feature is ready when its agreed behavior has been demonstrated.

**Verification.** Review each feature's criteria and recorded results, including failure cases
and the applicable targets below.

## Measurable Quality Targets

| Measure | Required result |
|---|---|
| Task entry | At least 9 of 10 manual attempts take no more than 20 seconds, from opening the project task list to seeing a task for oneself saved with the correct reminder. |
| Invitation acceptance | At least 9 of 10 manual attempts take no more than 15 seconds, from opening a valid invitation while signed in with the invited email verified to seeing the project as a regular member. |
| Email reminders | At least 99 of 100 scheduled reminders are accepted by the email service from the scheduled time through 60 seconds later, inclusive. Early, late, and missing acceptance fail. Rejections and later delivery failures are tracked separately. |
| Open-website reminders | In an active, connected tab, at least 99 of 100 reminders appear from the scheduled time through 10 seconds later, inclusive. Early, late, and missing appearances fail. |
| Returning to the website | At least 99 of 100 connected visits show the correct due reminders within five seconds of opening the website while signed in or submitting valid sign-in credentials. |
| Project isolation | Every check passes, including cross-project permissions and access after leaving or removal. |

## Development and Review

Feature specifications must define test conditions, expected outcomes, and evidence needed
for acceptance. Screen layouts, technology choices, and detailed feature behavior belong in
those specifications. Reviews must check both the feature criteria and this constitution.

## Governance

Proposed amendments must explain the change, its reason, affected behavior, and verification
updates. The product owner must approve amendments before they replace the constitution.

Versions use major increments for incompatible changes to principles, minor increments for
added or expanded rules, and patch increments for clarifications. Each amendment records
its approval date and version.

**Version**: 1.0.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13
