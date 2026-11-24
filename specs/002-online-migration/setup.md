# Pilot setup decisions

Updated: 2026-11-23.

- Approved: public GitHub repository for the personal, noncommercial pilot.
- Approved scope: Google-only sign-in, manually sent invitation drafts, website-only reminders.
- Confirmed public repository: https://github.com/vuton-code/task-reminder
- Local branch: main; origin points to the confirmed repository.
- Commit author: vuton-code, using the user-provided GitHub noreply email.
- Supabase project/region: pending.
- Fresh pilot data versus explicit import: pending; no existing data may be uploaded by default.
- User created the empty GitHub repository; remote was checked empty.
- No source push or deployment has occurred.

Next step: review and commit the sanitized source locally, then upload through Git.
Do not upload the project folder through the browser.
See publication-audit.md for the local audit and its limits.
