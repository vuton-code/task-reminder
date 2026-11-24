# UI improvements and owner-only deletion

Approved scope: account identity, project roles, task assignment visibility, reminder metadata,
invitation copy, professional site title, and owner-only project deletion.

## Acceptance criteria (before implementation)
- Account name, email and decorative initial avatar remain visible at desktop and mobile widths.
- Project cards and navigation show the current account's Owner, Manager or Member role.
- Assign to is visible on task creation. Members without assignment permission can only select
  themselves; forged choices fail validation and service authorization remains enforced.
- Due reminders show scheduled date/time and timezone, current assignee, and latest assignment
  timestamp both on first render and after polling. Existing unknown timestamps are labeled
  not recorded; edits and reschedules do not change assignment time.
- Invitation errors use ordinary sentences, with a clear next step and no Python list syntax.
- Website title is consistent across navigation, browser titles and home-screen metadata.
- Only the current owner can open or submit project deletion. GET only previews consequences;
  deletion requires POST, CSRF and the exact project name. Cancel preserves everything.
- Confirmed deletion removes the project's tasks, groups, invitations, memberships and local
  queued email records. It blocks old links and leaves other projects and accounts intact.
  Already delivered external email cannot be recalled. Sending and deletion share a project lock.

## Verification
Focused Django tests for role rendering, forged assignments, timestamps, invitation errors,
owner/member/manager/outsider deletion, confirmation, CSRF, related records and reminder races.
Browser checks at mobile and desktop sizes with polling, keyboard use, no-JS confirmation and
axe checks. Run full regression suite before handing back the local app.

## Manual testing reported by the user
19 core workflow checks passed, including ownership transfer, group permission isolation,
password reset revoking both browsers, and former-member reminder suppression with email enabled.
Reset-link reuse has not yet been reported. Formal timing and live-provider gates remain open.


## Decisions
- Approved display name: Projects Management Hub; repository identity remains task-reminder.
- Deletion is permanent, requires exact-name confirmation, and removes local project email records.
- Existing tasks have no historical assignment timestamp; show not recorded until reassigned.
- Password reset and session invalidation passed manually; reset-link reuse remains unreported.

Follow-up: remove the brand subtitle; each reminder retains its assignee and adds the task creation timestamp in the user timezone, on initial rendering and after polling. Verify the metadata test and browser reminder cards.

Display refinement: omit unknown assignment timestamps and the standalone IANA timezone line; retain timezone abbreviations on dates.

Assigned by identifies the original task creator, not the current assignee; preserved through reassignment. Store creator on new tasks; omit the line for historical tasks with unknown creators. Verify creation and reassignment in the reminder metadata test.
