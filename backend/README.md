# CareLink API

Local teaching MVP for fictional data. Run with Python 3.12 or newer.

```powershell
Set-Location C:\CareLink-Repo\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API reference: http://localhost:8000/docs. The Android emulator reaches this host at http://10.0.2.2:8000.

The default is a local SQLite database for an easy demonstration. Set `DATABASE_URL` to a `postgresql+psycopg://...` URL before starting to use PostgreSQL. No public database or hosting is provisioned. Set `CORS_ORIGINS` to comma-separated exact portal origins; default is http://localhost:4200.

## Render deployment

The repository root contains `render.yaml`. It starts the API from this `backend` folder and checks `/health`.

Use a hosted PostgreSQL database for a public deployment; never use the local SQLite file because it is not durable on a cloud web service. In Render enter these environment variables without committing their values:

- `DATABASE_URL`: the PostgreSQL connection string, using `postgresql+psycopg://...`.
- `CORS_ORIGINS`: exact deployed portal address or addresses, separated by commas. Leave it as `http://localhost:4200` only for a local portal.

After deployment, test `https://YOUR-API.onrender.com/health`. Enter that same HTTPS address in the patient app's **Server connection** field. The app deliberately refuses non-HTTPS remote addresses.

Run tests with `python -m pytest tests -q`. Use an isolated test database. Passwords use scrypt; opaque session tokens are hashed at rest and expire after seven days. Public registration cannot select administrator or coordinator roles.

Production work still required: TLS termination, email ownership verification, password recovery, persistent distributed abuse controls, database migrations/backups, encrypted phone databases, physical-device notification acceptance, and explicitly reviewed coordinator/admin policies. Do not expose this teaching server publicly or enter genuine patient data.
