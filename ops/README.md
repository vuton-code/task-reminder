# Deployment and local operations

The local development server and fake email worker require no provider credentials.
See the feature quickstart for Windows commands. Do not expose the development outbox publicly.

## Production preparation

1. Supply .env.production privately with DEBUG=false, a unique DJANGO_SECRET_KEY,
   HTTPS APP_BASE_URL, explicit ALLOWED_HOSTS, managed DATABASE_URL, OUTBOX_ENCRYPTION_KEY,
   and Resend/Google credentials when available. EMAIL_BACKEND_MODE must be resend.
2. Set TRUSTED_PROXY_CIDRS to the actual ingress peers only. The application accepts
   X-Forwarded-Proto only from these peers. Never trust arbitrary client forwarding headers.
3. Adapt nginx.conf.example with the actual domain/certificates. Request logs omit query
   strings and redact invitation/reset/verification paths. Gunicorn access logging is off.
4. Build the production image, run migrate and collectstatic --noinput, then start web and
   worker with compose.production.yaml. The production template has no development bind mount.
5. Run manage.py check --deploy --fail-level WARNING and check_worker. Configure monitoring for
   heartbeat >15 seconds, oldest due >30 seconds, unknown/held work and later email failures.
6. Run cleanup_expired daily. Back up PostgreSQL daily and protect backup access and retention.
   Preserve the outbox encryption key in a separate secret backup. Accepted-message identities
   must be restored together with tasks and memberships to prevent duplicates.
7. Run provider tests and the documented manual/physical-device trials before public release.

## Local restore rehearsal

With the local PostgreSQL server running:

    .venv/Scripts/python.exe manage.py rehearse_restore

This creates a timestamped .runtime/backups dump and a NEW restore_rehearsal_* database.
It never overwrites or drops an existing database. artifacts/restore-results.json records
counts and hashes for projects, memberships, groups, tasks, occurrences, messages and events.
Stop the worker during the rehearsal so the source snapshot remains stable.

## Operational limitations

The Windows development environment does not have Docker or a Linux ingress. Compose,
Gunicorn and nginx configuration are prepared but have not been exercised on their deployment
platform. Live provider credentials and certificates remain pending. No deployment occurred.
Provider retrieve support follows https://resend.com/docs/api-reference/emails/retrieve-email;
event semantics follow https://resend.com/docs/webhooks/event-types.
