# Neon PostgreSQL integration — 4 November 2026

## Scope

The existing CareLink-DB project and its production branch were linked with the Neon CLI. Only PostgreSQL is declared. The Flutter app keeps using the FastAPI API; it has no direct database credentials. No Render service or mobile release was deployed by this change.

## Changes

- Added root Git exclusions for Neon context and local credential files.
- Kept the generated `neon.ts` policy and tooling dependencies.
- Added Python environment-file loading with hosted process settings taking priority.
- Preserved SQLAlchemy and psycopg 3, accepting provider URLs without manual password editing.
- Used pooled connections for requests and direct connections for initial schema creation, with TLS and checks for stale runtime connections.
- Added isolated configuration tests and a repeatable HTTP smoke test using temporary fictional records.
- Added root build and backend-test commands; the portal is not part of these commands.

## Setup observations

- Neon CLI 8.18.0 installed successfully.
- Initial `neon init` created the link and configuration, but optional Claude agent-plugin installation timed out. Installed Neon skills were available and read; retrying all agent installations was unnecessary.
- Browser sign-in completed successfully.
- The first API connectivity attempt failed transiently. A read-only check and a retry succeeded.
- `neon config plan` and `neon deploy` reported that the existing branch matched the Postgres-only policy; deploy downloaded three variable names without exposing their values.
- The backend's initial tables were created through the direct connection. This is initial schema creation, not a versioned schema migration.

## Checks

The following checks passed against the updated working tree:

| Check | Result |
| --- | --- |
| `npm run build` | Neon configuration loaded; Python backend compilation passed |
| `npm run test:backend` | 12 passed; isolated SQLite test databases |
| Real PostgreSQL connection | `SELECT 1` passed; driver `psycopg` |
| API startup on port 8017 | Uvicorn reported application startup complete |
| Live HTTP/Neon smoke test | Passed registration/sign-in, dose persistence and duplicate prevention, readings, consent and revocation |
| Temporary test-data cleanup | Passed; only each run's uniquely identified fictional records removed |
| Git exclusions | `.env.local`, `.neon`, root `node_modules/` and backend `.venv/` ignored |

Live test output:

```text
PASS: patient and caregiver registration and sign-in through HTTP
PASS: medicine schedule and dose report persisted in Neon; retry saved no duplicate
PASS: fictional BP reading saved and retrieved
PASS: caregiver blocked before consent, allowed after approval, blocked after removal
PASS: removed only this run's fictional test accounts and records
Neon end-to-end verification passed.
```

The first live run passed its application checks but encountered a transient database connection error during cleanup. The exact test identities were checked and removed, guarded cleanup was made retryable, and a complete rerun passed. One verification invocation used an incorrect relative Python path and was corrected. The tests emitted a non-fatal Starlette/httpx deprecation warning; no dependency migration was attempted in this setup task.

The temporary API was stopped after testing. No Git commit or push was performed. Existing unrelated planning, design and portal work was preserved. Database passwords, session tokens and connection-string values are intentionally omitted.
