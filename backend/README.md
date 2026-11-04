# CareLink API

Local teaching MVP for fictional data. Run with Python 3.12 or newer.

```powershell
Set-Location C:\CareLink-Repo\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API reference: http://localhost:8000/docs. The Android emulator reaches this host at http://10.0.2.2:8000.

Without database settings, the default is local SQLite for a demonstration. When the repository's ignored `.env.local` exists, the backend reads Neon's `DATABASE_URL` and `DATABASE_URL_UNPOOLED` automatically. Process environment variables take priority, followed by backend-local env files and then repository-root env files. Set `CORS_ORIGINS` to comma-separated exact portal origins; the default is http://localhost:4200.

## Neon database

Neon hosts PostgreSQL; Render will host the Python API. The phone communicates with the API and never receives database credentials. The root `neon.ts` declares only PostgreSQL, preserving the existing authentication and Python/scikit-learn architecture.

The native Android sign-in update adds `/auth/social/google/native` and
`/auth/social/facebook/native`, which verify SDK credentials before issuing the
same patient sessions used by email login. Existing browser routes remain for
older clients. See [native setup](../Docs/implementation/native-social-sign-in.md).

`neon deploy` applies that configuration and downloads credentials into `.env.local` (or `.env` if present). Both files, the `.neon` link file, and root tooling dependencies are ignored by Git. Never print or commit their values.

- `DATABASE_URL`: pooled URL for normal API requests.
- `DATABASE_URL_UNPOOLED`: direct URL for initial SQLAlchemy table creation. Keep both URLs from the same database and branch.
- Provider `postgresql://` URLs work directly: the backend selects the installed psycopg 3 driver and requires TLS for Neon.
- Initial table creation uses the direct connection. It does not migrate existing tables; future schema changes need versioned migrations.
- The runtime pool is small and checks connections when reused after idle time.

From the repository root, `npm run build` loads the Neon configuration and compiles the Python backend. It does not build the Flutter APK or another member's portal. `npm run test:backend` runs the backend tests against isolated SQLite databases; ordinary tests do not use cloud credentials.

For an explicit live database/API check, start the backend in one terminal:

```powershell
Set-Location C:\CareLink-Repo\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8017
```

In another terminal:

```powershell
Set-Location C:\CareLink-Repo\backend
.\.venv\Scripts\python.exe -m app.verify_neon --api http://127.0.0.1:8017 --allow-demo-writes
```

The opt-in check creates uniquely named fictional accounts, saves a schedule, dose report and reading through HTTP, verifies persistence in Neon, checks consent/removal, and removes only that run's test records. Initial application tables remain. Stop the temporary API with Ctrl+C afterwards.

## Render deployment

The repository root contains `render.yaml`. It starts the API from this `backend` folder and checks `/health`.

Use a hosted PostgreSQL database for a public deployment; never use the local SQLite file because it is not durable on a cloud web service. In Render enter these environment variables without committing their values:

- `DATABASE_URL`: the pooled PostgreSQL connection string from Neon. Plain `postgresql://...` is accepted.
- `DATABASE_URL_UNPOOLED`: the direct connection string from the same Neon database.
- `CORS_ORIGINS`: exact deployed portal address or addresses, separated by commas. Leave it as `http://localhost:4200` only for a local portal.

After deployment, test `https://YOUR-API.onrender.com/health`. The patient app's default HTTPS address is set in `lib/connected/config/app_config.dart`; patients do not enter server addresses. A developer can use the `CARELINK_API` build override for local testing.

Run tests with `python -m pytest tests -q`. Use an isolated test database. Passwords use scrypt; opaque session tokens are hashed at rest and expire after seven days. Public registration cannot select administrator or coordinator roles.

The API is hosted at https://carelink-api-orjq.onrender.com with Neon PostgreSQL. Production work still required includes email ownership verification, password recovery, persistent distributed abuse controls, versioned database migrations/backups, encrypted phone databases, physical-device notification acceptance, and explicitly reviewed coordinator/admin policies.

## Optional Google and Facebook sign-in

`app/social_auth.py` adds provider availability, browser authorization, verified provider callbacks and a one-time PKCE-bound handoff to the Android app. Email authentication keeps working when these optional providers are not configured. No email-based automatic account linking is performed.

Set `PUBLIC_API_URL` and the relevant Google/Meta credentials privately in Render. Meta also needs an explicitly selected supported `FACEBOOK_GRAPH_VERSION`. See [account setup and verification](../Docs/implementation/account-and-social-sign-in.md) for the exact callbacks, environment-variable names and limits. Provider activation and real-account walkthroughs remain pending developer-app configuration.
