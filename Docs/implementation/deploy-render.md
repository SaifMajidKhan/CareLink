# Deploy the CareLink API on Render

Use this guide after committing and pushing the verified Neon connection changes. The database already exists in Neon; this step creates the FastAPI web service in the existing CareLink-FYP Render project.

## Create the web service

In Render, open the CareLink-FYP project and its Development environment, then choose New / Add service > Web Service. Connect GitHub and select `saif01234567/CareLink`.

| Field | Value |
| --- | --- |
| Name | `carelink-api` (choose another available name if taken) |
| Project / Environment | CareLink-FYP / Development |
| Branch | `saleem` |
| Language | Python 3 |
| Region | Singapore |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Instance Type | Free, for development |

The build/start commands run inside `backend`. Root npm tooling is for local Neon configuration checks and is not needed by the hosted Python API.

## Add environment variables

Privately open `C:\CareLink-Repo\.env.local` in your editor. For each key below, copy its value into Render's Environment Variables section. Copy the full URL, without the `KEY=` prefix or surrounding quotes. Do not paste credentials into chat, screenshots, GitHub, or the Flutter app.

| Key | Value |
| --- | --- |
| `DATABASE_URL` | Pooled Neon URL from the local file |
| `DATABASE_URL_UNPOOLED` | Direct Neon URL from the same local file |
| `CORS_ORIGINS` | `http://localhost:4200` for the local portal; replace/add the exact deployed portal HTTPS origin when ready |

Existing `postgresql://` URLs work without manual edits. `DATABASE_URL_UNPOOLED` is used for initial application-table setup; normal API requests use the pooled URL. No Neon account API key is needed in Render.

## Deploy and verify

1. Click Create / Deploy Web Service.
2. Wait for the service to show Live. If it fails, share the error lines from Logs after removing any secrets.
3. Open the service's public HTTPS address with `/health` appended. It should return `status: ok`.
4. Open `/docs` at the same address to view the API contract. The initial `/health` check confirms API startup; also test registration, sign-in and records on the deployed service.
5. The current patient app automatically uses the hosted HTTPS API configured in `lib/connected/config/app_config.dart`. Start with fictional test accounts; earlier local SQLite accounts are not automatically migrated to Neon.
6. Complete a phone-to-hosted-API walkthrough, including an offline report followed by one successful upload after reconnecting.

Free Render instances sleep after idle time, so the first request may need time to wake the backend. Consider the previously discussed paid instance shortly before the supervisor demo, after testing the deployed service.

## Deployment and existing phone sessions — 4 November 2026

The service is deployed at https://carelink-api-orjq.onrender.com. Read-only checks returned HTTP 200 for `/health` (`status: ok`), `/docs` and `/openapi.json`. These checks verify startup and the published API contract; the phone-to-hosted-account walkthrough remains to be completed.

A restored phone sign-in retains the server address it originally used. Deploying the API, or changing the build's default address, does not change that saved session. To connect to the hosted service:

1. Restart the app after loading the latest sign-out fix.
2. In Profile, choose Sign out and confirm. Unsent reports still block sign-out and must be uploaded or reviewed first.
3. Open Sign in or Create account from the guest welcome screen. The current build uses `https://carelink-api-orjq.onrender.com` automatically; the patient-facing Server connection section has been removed.
4. Sign in to an account registered on the hosted server, or create a fictional test account there.

Confirmed sign-out now clears the local sign-in, downloaded records and reminders even when remote logout returns a connection error or HTTP 401. It first attempts remote token revocation; an unreachable server may retain that token until its normal expiry. The change does not transfer or upload records from one server to another. Regression checks cover unreachable-server logout, expired-session logout and preservation of unsent reports.

The new account and guest flow, provider callback addresses and optional Render settings are documented in [Account and social sign-in](account-and-social-sign-in.md). Google/Facebook developer setup is still required; these providers are unavailable until configured.

## References

- [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
- [Root directories for repositories with multiple apps](https://render.com/docs/monorepo-support)
- [Environment variables and secrets](https://render.com/docs/configure-environment-variables)
- [Free instance limitations](https://render.com/docs/free)
