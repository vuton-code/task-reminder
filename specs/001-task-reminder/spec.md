# Feature Specification: First Usable task-reminder

**Feature Branch**: None (no branch-creation hook configured)

**Created**: 2026-11-13

**Status**: Draft, validated for planning

**Updated**: 2026-11-13 — Added Google sign-in at the product owner’s request.

**Input**: User description: "Create the first usable version of task-reminder following the approved constitution, including accounts, projects, invitations, groups, tasks, and email and in-website reminders."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage My Own Project and Tasks (Priority: P1)

A person starts with Google sign-in or registers with a username and password, establishes
a verified email, creates a project, and records tasks for themselves with optional reminders.

**Why this priority**: This is a usable personal task workflow and establishes the account
and project boundaries needed by the remaining journeys.

**Independent Test**: With a new account, create a project, save and edit a self-assigned task,
refresh the website, and complete the task. Verify persistence, ownership, and correct times.

**Acceptance Scenarios**:

1. **Given** an unused username and email, **When** a person registers and follows the email verification link, **Then** their account has a verified email and they can sign in with their username and password.
2. **Given** a signed-in verified account, **When** the person creates a named project, **Then** they become its owner and can select it from their project list.
3. **Given** a project member, **When** they save a task title and optional description and reminder time for themselves, **Then** the project task list shows the persisted task, assignee, status, and correct reminder time.
4. **Given** an assigned task, **When** its assignee edits, reschedules, or completes it, **Then** the saved task reflects that change after refresh and pending reminders reflect its current state.
5. **Given** invalid or missing required input, **When** the person submits it, **Then** the website identifies the problem and preserves entered values without claiming a successful save.

### User Story 2 - Invite People and Govern Each Project (Priority: P1)

An owner invites collaborators, delegates specific manager permissions, and maintains
independent membership and authority in each project.

**Why this priority**: Collaboration requires deliberate membership and enforceable privacy.

**Independent Test**: Use two projects and three prepared accounts. Invite an existing account
into the second project, vary its role between projects, and exercise the permission matrix.

**Acceptance Scenarios**:

1. **Given** an owner or manager with invitation permission, **When** they invite an email address, **Then** a pending invitation identifies that project and inviter, expires seven days after sending, and grants no membership before acceptance.
2. **Given** a valid invitation and an account with the matching verified email, **When** the signed-in recipient accepts, **Then** they become a regular member using that account, retaining their other project memberships.
3. **Given** an invitation, **When** an unauthenticated visitor or an account with a different or unverified email follows it, **Then** no membership or project tasks or member list are disclosed; only the project name and inviter may be shown.
4. **Given** a pending invitation, **When** the owner cancels it or an authorized manager cancels their own invitation, **Then** cancellation immediately prevents acceptance. A manager cannot cancel another person's invitation.
5. **Given** an expired or cancelled invitation, **When** its intended recipient tries to accept it, **Then** they are told a fresh invitation is needed and receive no membership.
6. **Given** an owner, **When** they promote or demote a member or grant or revoke either manager permission, **Then** the updated authority applies only in that project and is enforced on the next action.
7. **Given** a manager in Project A who is a regular member in Project B, **When** they attempt manager actions in B, **Then** access is denied, including through direct requests.
8. **Given** a non-owner member, **When** they leave or the owner removes them, **Then** their project access and group memberships end immediately and their account retains other memberships.
9. **Given** an owner and an existing manager, **When** the owner transfers ownership, **Then** exactly one owner remains. An owner cannot leave before transfer or transfer to a regular member.
10. **Given** a retried acceptance or concurrent ownership changes, **When** actions finish, **Then** membership is not duplicated and the project still has exactly one owner.

### User Story 3 - Assign Work and Organize Groups (Priority: P2)

Collaborators see project work, owners and authorized managers assign tasks, and the owner
organizes people into groups without changing access.

**Why this priority**: Delegation and organization make a shared project useful as it grows.

**Independent Test**: In a prepared project, assign work among members and create a group.
Repeat actions as each role and verify both permitted and denied behavior.

**Acceptance Scenarios**:

1. **Given** any project member, **When** they view its task list, **Then** every task in that project is visible, including tasks assigned to other members.
2. **Given** a regular member, **When** they create a task for themselves or update or complete a task assigned to them, **Then** the action succeeds; attempts to modify another person's task or assign work to someone else are denied.
3. **Given** an owner or manager with assignment permission, **When** they assign or reassign a task to a current member, **Then** the new assignee is saved and pending reminders target that person.
4. **Given** a manager without assignment permission, **When** they assign work to another person, **Then** the action is denied.
5. **Given** an owner, **When** they create, rename, or delete a group or change its members, **Then** only that project's existing members can be included and nobody's project role or task visibility changes.
6. **Given** project members in groups, **When** a member filters the member list by group, **Then** matching people appear; non-owners cannot alter group definitions or membership.
7. **Given** an assignee who leaves, **When** their membership ends, **Then** their tasks remain visible as unassigned and an owner or authorized manager can reassign them.

### User Story 4 - Receive Relevant Reminders (Priority: P1)

The current assignee receives optional email and sees due reminders while using the website
or on returning, with current project permissions respected.

**Why this priority**: Reliable reminders are the product's core promise.

**Independent Test**: Prepare tasks with known reminder times and verified member accounts.
Observe email-service acceptance and visible reminders, then repeat after changes to tasks,
assignments, preferences, and membership.

**Acceptance Scenarios**:

1. **Given** an incomplete assigned task with a future reminder, **When** its scheduled time arrives with the assignee's website active and connected, **Then** the reminder appears within the open-website target and never early.
2. **Given** due reminders and an authorized assignee, **When** they open the website while signed in or submit valid sign-in credentials, **Then** correct due reminders across their current projects appear within the returning-visit target.
3. **Given** an assignee who enabled email, **When** an eligible reminder becomes due, **Then** the email service accepts the message within the email target; its content includes at most the task title and an access-controlled link plus generic reminder wording.
4. **Given** email is disabled before sending, **When** a reminder becomes due, **Then** no email is sent and the in-website reminder remains available.
5. **Given** a queued reminder, **When** the task is completed, rescheduled, reassigned, or its assignee leaves before dispatch, **Then** dispatch uses the latest state and does not send a stale reminder or disclose the task to a former member.
6. **Given** a previously delivered link, **When** someone opens it, **Then** sign-in and current project access are required and the current task state is displayed.
7. **Given** rejected or later failed email delivery, **When** the failure is reported, **Then** its outcome is distinguishable from service acceptance and in-website reminders remain available.
8. **Given** repeated processing or a temporary connection loss, **When** processing or connectivity resumes, **Then** the same schedule produces one active in-website reminder and no duplicate email from a confirmed successful send. Eligible overdue reminders are recovered and lateness remains recorded.
9. **Given** a completed or rescheduled task, **When** its previous reminder is visible, **Then** that previous active reminder is removed and the new schedule, if any, governs future reminders.

### User Story 5 - Recover and End Account Access Safely (Priority: P1)

A person can recover a forgotten password, tolerate ordinary sign-in mistakes, and sign out
of a shared device without losing access on their other devices.

**Why this priority**: Account access must stay usable and protected throughout its lifecycle.

**Independent Test**: Use an account signed in on two devices. Exercise failed sign-ins,
recovery, reset-link expiry and reuse, ordinary sign-out, and requests from ended sessions.

**Acceptance Scenarios**:

1. **Given** a few mistyped passwords, **When** the user retries, **Then** ordinary mistakes are tolerated according to the limits below and sustained failures trigger temporary delays per account and source.
2. **Given** sign-in delays, **When** the user requests recovery, **Then** recovery remains available with abuse controls separate from sign-in delays.
3. **Given** a verified account email, **When** recovery is requested, **Then** a reset link is sent there, is valid for less than 30 minutes, and can be successfully used once.
4. **Given** expired or used reset links, **When** they are submitted, **Then** the password remains unchanged and access is denied.
5. **Given** active sessions on two devices, **When** a password reset succeeds, **Then** both sessions immediately lose access and the old password fails.
6. **Given** active sessions on two devices, **When** one signs out normally, **Then** that session immediately loses access while the other continues.
7. **Given** registration, sign-in, and recovery activity, **When** credential storage and logs are inspected, **Then** passwords use the constitution's storage protections and no passwords or usable recovery secrets appear in logs.

### User Story 6 - Start and Return with Google (Priority: P1)

A person chooses Continue with Google to start using task-reminder without filling in a
separate registration form or choosing a website username or password. Returning users
reach the same projects and tasks.

**Why this priority**: A familiar sign-in method removes account-creation friction.

**Independent Test**: Use a new Google identity, a returning linked identity, and an existing
password account with a matching email. Verify onboarding, explicit linking, invitation
acceptance, project isolation, cancellation, and logout.

**Acceptance Scenarios**:

1. **Given** a person new to task-reminder, **When** they complete Google sign-in, **Then** the website creates their application profile automatically and signs them in without asking them to choose a username or password.
2. **Given** a returning Google user, **When** they sign in again, **Then** they reach the same account, tasks, memberships, and reminder preferences without duplicate profiles.
3. **Given** an existing account with the same email and no Google connection, **When** Google sign-in completes, **Then** the website requires sign-in to the existing account before connecting Google and never silently merges accounts or grants access from an email match alone.
4. **Given** an existing password user who recently proved access to their account, **When** they choose Connect Google and complete Google sign-in with the matching verified email, **Then** future Google sign-ins open that existing account with all its memberships.
5. **Given** a Google user following an invitation, **When** the website has verified the invited address and the person explicitly accepts a valid invitation, **Then** they join as a regular member. A different or unverified address grants no membership.
6. **Given** a cancelled, failed, expired, or replayed Google sign-in, **When** the person returns, **Then** no unauthorized session, duplicate account, or membership is created and the website allows a fresh attempt.
7. **Given** Google sign-in does not establish current control of the supplied email, **When** the user starts, **Then** the website requests email verification before project creation or invitation acceptance; it still does not require a local password.
8. **Given** a Google-authenticated session, **When** the user signs out, **Then** the current website session loses access immediately. A password reset on an account that also has a local password invalidates all its website sessions, including Google-authenticated sessions.
9. **Given** a Google-only account, **When** the person needs to recover Google access, **Then** the website directs them to Google's recovery process. Website password recovery does not create a new local sign-in method.
10. **Given** due reminders and successful Google authentication, **When** the browser returns Google's sign-in result to the website, **Then** the correct due reminders appear under the Google-return target below.

### Edge Cases

- Concurrent first Google sign-ins must create exactly one profile per Google identity.
- A Google email change must not replace the account email, merge accounts, or move memberships automatically. A changed address requires email verification before invitation use.
- Google sign-in and account linking must reject results intended for another website or another browser sign-in attempt.

- Acceptance at or after the seven-day expiry instant fails. Cancellation committed before acceptance wins; an already completed acceptance requires owner removal rather than invitation cancellation.
- Invitation acceptance retries cannot recreate a membership after that member was removed. A fresh invitation is required.
- Invitations to an existing member explain that the person already belongs to the project without creating another membership.
- A manager losing invitation permission immediately loses permission to send or cancel invitations. Existing pending invitations stay valid until acceptance, cancellation, or expiry.
- An owner who is the sole member must invite someone, promote them, and transfer ownership before leaving.
- Groups cannot include members of a different project. Removing a group preserves tasks and project memberships.
- Concurrent task changes must either preserve the latest accepted change or report a conflict for review; silently overwriting a newer change is unacceptable.
- Failed saves preserve entered content. Retrying a save or acceptance must not duplicate the task or membership.
- A reminder time must identify an unambiguous instant. Ambiguous or nonexistent local daylight-saving times require correction or explicit offset selection.
- Reassignment after a reminder is already due removes the old assignee's active reminder and makes the due reminder available to the new eligible assignee.
- Membership, permission, and schedule changes completed before dispatch must govern dispatch. An email already accepted by the service cannot be recalled.
- Unknown email-service acceptance must be reconciled before retrying to avoid duplicate sends. Rejections, ambiguous outcomes, late acceptance, and later failures remain distinguishable.
- Offline or background tabs catch up when active connectivity returns. Their delay is recorded separately from active, connected-tab measurements.
- A task with no reminder time creates no reminder. Completed tasks retain their task record.
- Invalid credentials and recovery requests do not reveal whether an account exists.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Acceptance coverage |
|---|---|---|
| FR-001 | Users MUST be able to register with a unique username, email, and password, verify ownership of their email, and sign in using username and password. Google onboarding MUST also support automatic profile creation under FR-024. Duplicate usernames or verified emails MUST NOT create competing accounts. | Story 1.1; Story 6; edge cases |
| FR-002 | The system MUST apply constitution-compliant password storage, exclude passwords and usable recovery secrets from logs, and distinguish sign-in identity from project authorization. | Story 5.7; Story 2.7 |
| FR-003 | Failed sign-ins MUST trigger temporary limits per account and source using the specified initial policy, while recovery remains available. | Story 5.1-2 |
| FR-004 | Local-password recovery MUST use the verified email, a single-use link expiring 30 minutes after issue, and immediate termination of all website sessions upon successful reset. Ordinary sign-out MUST immediately end only the current session. | Story 5.3-6 |
| FR-005 | Verified users MUST be able to create named projects and select among all projects they belong to. Every project MUST have exactly one owner. | Story 1.2; Story 2.9-10 |
| FR-006 | Every project read and change MUST enforce current project membership and permissions. All members MUST see all project tasks; outsiders MUST see neither tasks nor member lists. | Story 2.3, 2.7-8; Story 3.1 |
| FR-007 | Only owners MUST be able to change roles and independently grant or revoke managers' invitation and assignment permissions. | Story 2.6-7; permission matrix |
| FR-008 | Owners and managers with invitation permission MUST be able to send email invitations tied to the recipient's verified email, expiring seven days after sending. | Story 2.1-3 |
| FR-009 | Membership MUST begin only on valid, authenticated acceptance by the intended verified recipient, always as a regular member. Existing accounts MUST support additional projects. | Story 2.2-3, 2.10 |
| FR-010 | Owners MUST be able to cancel any pending project invitation; authorized managers MUST be able to cancel only invitations they sent. Cancellation MUST prevent subsequent acceptance immediately. | Story 2.4-5 |
| FR-011 | Members MUST be able to leave, owners MUST be able to remove other members, and ownership MUST transfer only to an existing manager before an owner leaves. | Story 2.8-10 |
| FR-012 | Departure MUST immediately revoke project access, remove group membership, stop queued reminders to the former member, and leave their tasks unassigned for reassignment. | Story 2.8; Story 3.7; Story 4.5 |
| FR-013 | Owners MUST be able to manage named groups of current project members. Members MUST be able to view and filter group membership. Group changes MUST NOT change project permissions or task visibility. | Story 3.5-6 |
| FR-014 | Members MUST be able to create self-assigned tasks with a required title, optional description, and optional reminder time, and update or complete their assigned tasks. | Story 1.3-5; Story 3.2 |
| FR-015 | Owners and managers with assignment permission MUST be able to create, edit, complete, assign, and reassign tasks across their project. Other members MUST NOT modify tasks assigned to someone else. | Story 3.2-4; permission matrix |
| FR-016 | Saved tasks, memberships, schedules, and preferences MUST persist across refresh and sign-in. Failed or conflicting changes MUST be reported without falsely confirming success or creating duplicates on retry. | Story 1.3-5; Story 2.10; edge cases |
| FR-017 | Users MUST be able to enable or disable account-wide email reminders. In-website reminders MUST remain available independently. | Story 4.1-4 |
| FR-018 | Each reminder MUST be directed to the current assignee after checking current membership, preferences, completion state, and schedule immediately before dispatch. | Story 4.5; edge cases |
| FR-019 | Completion MUST cancel pending reminders and remove active ones. Rescheduling MUST replace the old schedule. Reassignment MUST update recipients and active visibility. | Story 1.4; Story 4.5, 4.9 |
| FR-020 | Email reminder content MUST be limited to generic wording, the task title, and a link requiring sign-in and current project access. Opening a link MUST show the current task state. | Story 4.3, 4.6 |
| FR-021 | Due reminders MUST be visible while the site is active and connected and when the user returns, including through a home-screen shortcut. | Story 4.1-2, 4.8 |
| FR-022 | Reminder processing MUST recover eligible overdue work, avoid duplicates after confirmed delivery, and distinguish acceptance, rejection, ambiguous results, and later delivery failure. | Story 4.7-8; edge cases |
| FR-023 | Every feature MUST have acceptance evidence before release. All isolation checks and the success criteria below MUST pass. | All stories; SC-001 through SC-010 |
| FR-024 | Users MUST be able to start and return through Google without choosing a website username or password. Successful first sign-in creates one application profile; repeat sign-ins reuse it. | Story 6.1-2; concurrency edge case |
| FR-025 | Connecting Google to an existing account MUST require explicit consent, recent proof of access to that account, and a matching verified email. An email match alone MUST NOT grant access or merge accounts. | Story 6.3-4 |
| FR-026 | Google users MUST obey the same project permissions, explicit invitation acceptance, verified-recipient checks, and session revocation rules as password users. | Story 6.5, 6.7-8; SC-006 |
| FR-027 | Cancelled, invalid, expired, mismatched, or replayed Google sign-in attempts MUST fail safely without creating access or duplicate profiles. | Story 6.6; edge cases |
| FR-028 | Google-only account recovery MUST use Google's recovery process. Local password recovery MUST operate only for accounts with a local password. | Story 6.9 |

### Project Permission Matrix

This matrix also defines the required positive and negative authorization tests.

| Action | Owner | Manager | Regular member |
|---|---|---|---|
| View project tasks and members | Yes | Yes | Yes |
| Create own task; edit or complete assigned task | Yes | Yes | Yes |
| Create or modify others' tasks; assign or reassign | Yes | Assignment permission required | No |
| Send invitations | Yes | Invitation permission required | No |
| Cancel pending invitations | Any in project | Own, with current invitation permission | No |
| Change roles or manager permissions | Yes | No | No |
| Remove another member | Yes | No | No |
| Transfer ownership to an existing manager | Yes | No | No |
| Manage groups and group membership | Yes | No | No |
| Leave project | After transferring ownership | Yes | Yes |

All actions are denied to outsiders except viewing the project name and inviter through an
invitation and accepting a valid invitation under its recipient checks.

### Initial Sign-in and Recovery Limits

These are adjustable product defaults for this specification, preserving tolerance for typos.

- Allow the first five consecutive failed attempts per account without an added delay.
- After failures six through nine, require 30 seconds before another account attempt.
- After ten consecutive failures, require five minutes before another account attempt.
- Reset the account failure count after successful sign-in or 30 minutes without a failed attempt.
- At 50 failed attempts from one source within ten minutes, delay further sign-in attempts from that source for five minutes. Attempts blocked by an existing delay do not extend it.
- Recovery requests remain available during sign-in delays. Allow at most three recovery emails per account per 15 minutes and 20 requests per source per 15 minutes, with the same public response for known and unknown accounts.
- Tests MUST cover the exact thresholds, expiry boundaries, shared sources, and attempts spread across sources. The technical plan defines how a source is identified.

### Key Entities *(include if feature involves data)*

- **Account** — Application identity, optional user-chosen username and local password, verified email state, and email-reminder preference; may belong to several projects.
- **Google connection** — A Google identity explicitly associated with exactly one application account; email matching alone does not create this connection.
- **Session** — A signed-in account's access on a device, with an active or ended state.
- **Verification or recovery request** — Account-related proof with a purpose, recipient, expiry, and consumed state.
- **Project** — Named workspace with exactly one owner, memberships, groups, and tasks.
- **Membership** — Account's project role and independent manager invitation and assignment permissions.
- **Invitation** — Project, inviter, recipient email, sent and expiry times, and pending, accepted, cancelled, or expired state.
- **Group** — Named collection of existing members within one project, with no authorization effect.
- **Task** — Project, title, optional description, one current assignee or unassigned state after departure, open/completed status, and optional reminder time.
- **Reminder occurrence** — Task schedule and eligible recipient, active website visibility, email attempt outcomes, acceptance time, and later failure information.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** — At least 9 of 10 manual task-entry attempts finish in 20 seconds or less, from opening the project task list until a task for oneself is visibly saved with the correct reminder.
- **SC-002** — At least 9 of 10 manual invitation-acceptance attempts finish in 15 seconds or less, from opening a valid invitation while signed in with the invited email verified to seeing the project as a regular member.
- **SC-003** — At least 99 of 100 eligible scheduled email reminders are accepted by the email service between the scheduled instant and 60 seconds later, inclusive. Early, late, and missing acceptance fail. Rejections and later delivery failures are reported separately.
- **SC-004** — At least 99 of 100 reminders in an active, connected tab appear between the scheduled instant and ten seconds later, inclusive. Early, late, and missing appearances fail.
- **SC-005** — At least 99 of 100 connected visits display the correct due reminders within five seconds of opening the website while signed in or submitting valid sign-in credentials.
- **SC-006** — Every permission-matrix and project-isolation check passes, including direct requests, cross-project roles, group changes, departed members, ended sessions, and reminder links. Any unauthorized access blocks release.
- **SC-007** — Every invitation lifecycle check passes, including matching verified identity, new and existing accounts, expiry, cancellation, replay, and concurrent acceptance.
- **SC-008** — Every account-security check passes, including password-storage review, secret-free logs, defined sign-in limits, recovery expiry and single use, and session termination.
- **SC-009** — Every reminder mutation and privacy check passes, including completion, rescheduling, reassignment, departure, preference changes, retries, and failure reporting.

- **SC-010** — All Google onboarding, repeat sign-in, explicit linking, cancellation, invalid-result, invitation, and logout checks pass. At least 99 of 100 successful Google-return visits show correct due reminders within five seconds from the browser returning the provider's sign-in result to the website. Time spent on Google's account selection, consent, or recovery screens is recorded separately.

### Verification Conditions and Evidence

- Use representative desktop and phone browsers, a documented connected test environment, prepared project data, and synchronized timing. Record device, browser, connection, dataset, and observed start/end times.
- Manual timings include reading, navigation, and typing. Use ten attempts per supported device category with at least three people and a fixed short task prompt. Do not exclude unsuccessful attempts or replace them with successful reruns.
- Invitation timings use already-signed-in accounts with the intended email verified. Registration and email verification are separately tested in Stories 1 and 2.
- Run the 100-reminder and 100-visit samples per supported device category where applicable. Define scheduled times beforehand and retain every result, including early and missing outcomes.
- Email samples contain eligible incomplete tasks whose current assignees are members and have enabled email. Cancelled or intentionally suppressed reminders are assessed by SC-009, with suppression reported separately from delivery results.
- Returning-visit samples mix already-signed-in openings and valid sign-ins and include completed tasks and departed projects to verify exclusion.
- Record deterministic boundary and concurrent-operation results for privacy and lifecycle rules. A successful percentage never excuses an unauthorized disclosure.
- Preserve a requirement-to-test mapping and results for every FR and acceptance scenario. Passing this specification review establishes readiness to plan; release requires demonstrated behavior.

## Assumptions

- The approved constitution v1.0.0 governs this feature. Google is an additional way to establish account identity; its project authority comes from the same memberships. Password safeguards and password-reset requirements apply to local passwords. Defaults below are planning assumptions and may be revised within those principles.
- Username-and-password sign-in remains an available option. A Google-only user recovers access through Google. Adding a local password or disconnecting the only sign-in method is deferred.
- Existing-account linking requires recent password confirmation within five minutes and a matching verified Google email. If the password is forgotten, recover the existing account first. This default avoids silent account merging.
- Google sign-in uses only basic identity information. Access to Gmail, Calendar, Drive, and contacts is outside this feature.
- Password registration uses one unique username and one verified email per account. Google onboarding automatically creates the application profile and requires no user-chosen username or local password. Both methods require a verified email before project creation or invitation acceptance. Verification links are single-use and expire after 24 hours; users can request another.
- A project has one owner. After ownership transfer, the former owner becomes a manager retaining invitation and assignment permissions until changed by the new owner.
- New managers initially have neither delegated permission; the owner grants each explicitly.
- Group management belongs to the owner for the first version. A member may belong to multiple groups in the same project.
- Each task has one assignee, an open/completed status, and one optional reminder instant. Description is optional; the title is required. Task deletion, recurring reminders, attachments, comments, and subtasks are deferred.
- Owners and assignment-enabled managers can edit or complete any project task. Other members can edit only their assigned work.
- Email reminders default to disabled until enabled by the user. In-website reminders are always available. Preferences apply across the account's projects.
- Due in-website reminders remain active until completion, rescheduling, reassignment, or loss of membership. Dismissal, snoozing, and read/unread workflows are deferred.
- Times are displayed with an explicit timezone and resolve to a specific instant. Changing display timezone preserves the scheduled instant.
- Ordinary use requires connectivity. Desktop and phone browser use, including opening from a home-screen shortcut, are included. SMS, closed-site push, native apps, and offline editing are deferred.
- Email service access is needed for verification, invitations, recovery, and reminder delivery. Delivery acceptance and later failures must be observable without exposing credentials.
- The plan will choose supported browsers, technical components, deployment arrangements, and detailed capacity tests. The initial performance targets apply to the documented test conditions above.


## Approved UI and project lifecycle update

The product owner approved the UI pass after manual workflow testing, including the display
name **Projects Management Hub** and owner-only permanent project deletion. Detailed acceptance
criteria and verification are in [ui-improvements.md](ui-improvements.md). Deletion is an explicit,
confirmed project action; it does not allow an owner to leave a surviving project without transfer.
