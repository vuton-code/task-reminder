# Public repository preparation audit

Date: 2026-11-23. Scope: current local source, before initial Git setup.

## Result

At the initial audit there was no Git repository or local commit history to scan.
Git has since been initialized on main and connected to the empty user-created repository.
Candidate files were enumerated using Git itself in a temporary repository with this working
folder and its ignore rules. At that audit no files had been staged, committed or uploaded.
Before the initial commit, recheck staged bytes against the reviewed manifest, secret patterns
and local environment values; stop on any unexplained change. Commit uses the approved noreply email.

Pattern checks covered private keys, common provider tokens/JWTs, credential-bearing URLs,
sensitive assignments, email addresses, personal filesystem paths and live invitation/reset links.
Candidate content was also compared against long secret/token/password/key/database-URL values
from the local environment without printing those values. No exact local-secret matches were found.
No private-key, provider-token, personal-path or live-link matches were found in candidates.

Reviewed findings: example/local Docker database credentials, placeholder configuration,
synthetic test passwords, generated development passwords (code only), example email addresses,
and mocked Google claims. Gmail addresses occur in Google fixture tests, not copied tester records.
The only non-text candidate was the bundled font, static/fonts/Inter.ttf.

## Excluded from normal Git addition

- .env and environment variants, except the reviewed placeholder .env.example.
- .runtime (local database, backup, outbox-related runtime and logs), artifacts (screenshots/reports),
  virtual environment, caches and collected static output.
- Local agent tools/configuration, browser authentication state, exports/backups/database dumps,
  key files, node_modules, build output and Supabase temporary state.

Existing source, templates, static source assets, tests, dependency manifests, specifications and
operations documentation are candidates for publication. See publication-manifest.txt for their
SHA-256 fingerprints. The manifest itself is excluded from its own fingerprint list.

## Required before first push

This is a point-in-time pattern review, not a guarantee that every possible secret is detectable.
Inspect the exact staged diff and re-scan it after initialization and any further edits; check any
new commit history before pushing. Never force-add ignored files. Do not use browser folder upload,
which does not enforce .gitignore. Review commit author email for desired public visibility.
Future frontend builds require their own secret scan. Public source does not authorize publishing
local tester data, backups, logs or screenshots. Any real credential discovered must be removed
and rotated before publication.
