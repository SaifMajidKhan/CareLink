# Welcome, guest access and account sign-in

Updated: 4 November 2026. The Flutter client is included in the patient-app checkpoint. The matching backend authentication code remains local for a separate commit. Public provider sign-in is not activated until that code is deployed and the team's Google and Meta developer apps are configured and tested.

## What changed

- People without a saved sign-in open a guest welcome screen. It contains no patient records, sample medicine reports or invented account identity.
- Medicines, history, readings, care-team actions and navigation tabs ask the guest to sign in or create an account. Dismissing the prompt keeps the person in guest mode. Guest browsing does not open a patient database or send health records to the API.
- A signed-in patient continues to use their saved account. Guest access does not silently sign out existing patients or move their pending reports.
- Sign-in and registration use the configured API address automatically. The public default is `https://carelink-api-orjq.onrender.com`; there is no patient-facing server-address form.
- Forms validate name, email, password length and password confirmation. API validation errors are displayed beside the relevant field instead of the generic `(422)` message. Submitted password values are not included in error messages.
- The early "FYP demonstration / fictional details" banner was removed from the connected app's welcome, account and profile screens. The project's prototype and data limitations remain documented in the repository.
- Google and Facebook buttons check the backend's availability flags. An unconfigured provider stays disabled and email sign-in remains available. A button is not evidence of completed provider setup.

## Registration rules

Names must contain 1–80 characters after trimming. Email must contain a valid-looking address without spaces or extra `@` characters; it is normalized to lowercase. Passwords must contain 10–128 characters. Registration also checks that the confirmation matches. Password strength limits were not relaxed to hide a validation error.

The previous 422 message meant the backend rejected an input. The app previously discarded the structured field-error list. Existing accounts are not recreated or silently migrated when the hosted service is selected.

## File organization

| Area | Files |
| --- | --- |
| Deployment address and callback identifiers | `apps/patient_app/lib/connected/config/app_config.dart` |
| Guest welcome and feature gates | `screens/guest_home_screen.dart`, `widgets/auth_prompt.dart` |
| Account forms and validation | `screens/sign_in_screen.dart`, `auth/auth_validation.dart` |
| Browser sign-in and device PKCE | `auth/social_sign_in.dart` |
| Reusable branding and provider buttons | `widgets/carelink_brand.dart`, `widgets/social_sign_in_buttons.dart` |
| Provider verification and one-time handoff | `backend/app/social_auth.py` |
| Separate provider identity and temporary-flow tables | `backend/app/database.py` |

Paths in the middle rows are relative to `apps/patient_app/lib/connected/`.

## Run the updated Android app

Stop the running app in Android Studio, fetch packages if prompted, and Run again. This update adds a browser-authentication plugin and an Android callback activity, so hot reload alone is insufficient.

The default hosted address is part of the build. Developers can use a different local build without exposing settings to patients:

```powershell
Set-Location C:\CareLink-Repo\apps\patient_app
flutter --no-version-check run -d emulator-5554 --dart-define=CARELINK_API=http://10.0.2.2:8000
```

A restored session retains its original server. Sign out normally before switching servers; unsent reports still block sign-out. Their account/server separation is preserved.

## How social sign-in works

The app opens the provider in the system's browser authentication tab. The backend receives the provider callback at its fixed HTTPS address, verifies the provider identity and redirects to `carelink://auth/callback` with a short-lived one-time code. The device exchanges that code using its original PKCE verifier and receives the normal CareLink session over HTTPS. CareLink session tokens and provider secrets are not placed in the callback URL.

Google ID tokens are checked with Google's official `google-auth` library, including signature, issuer, audience and expiry, followed by nonce, authorized-party and verified-email checks. Facebook tokens are checked for the configured app, user type, user ID and expiry before fetching the profile with an app-secret proof. Provider HTTP endpoints are fixed in the server code.

Provider identity is keyed by provider plus subject ID. A matching email never automatically links an existing account. If that email is already registered through another method, the user must use the existing method. Explicit account linking is separate future work. Facebook can withhold email; in that case an internal, non-deliverable identifier is used instead of inventing a contact address.

Temporary authorization flows expire after 10 minutes; handoff codes expire after 90 seconds and are single-use. New social accounts are patients only, and disabled accounts cannot sign in. The two new tables are additive; existing account IDs, password hashes and phone queues are retained. This remains initial schema creation, not a general migration framework.

## Step 1: deploy the new backend code

Commit and push the backend authentication changes on the active member branch, then let Render deploy that commit. Keep this separate from the Flutter UI commit and the other member's portal work. Saving provider credentials on the old deployment does not add the new routes.

In Render, set `PUBLIC_API_URL` to `https://carelink-api-orjq.onrender.com`. The code can also use Render's `RENDER_EXTERNAL_URL`, but an explicit public address makes the callback setup easier to review. The configured address must be HTTPS and have no path, query or fragment.

## Step 2: configure Google

1. Open [Google Auth Platform](https://console.cloud.google.com/auth/overview) in your own Google account. Create/select the CareLink project and set the app's branding and audience. While in testing, add the accounts that will test sign-in.
2. Create an OAuth client with application type **Web application**. This flow uses the backend's HTTPS callback, not a native Android client secret.
3. Register this exact authorized redirect URI:

```text
https://carelink-api-orjq.onrender.com/auth/social/google/callback
```

4. Privately add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to the Render service's environment. Save and redeploy. Never paste the secret into chat or commit it.
5. Check `/auth/providers`: `google.available` should be `true`. Open the updated Android app, select Google and complete sign-in with an allowed test account. Use an account not already registered by email for this first social-sign-up test.

Google's console uses the HTTPS callback above. The `carelink://` URL is the final server-to-phone handoff, registered in Android's manifest.

## Step 3: configure Facebook

1. Open [Meta for Developers](https://developers.facebook.com/apps/) and create/select the CareLink app with a Facebook Login use case suitable for user sign-in. Follow the console's current app requirements.
2. Configure Facebook Login's valid OAuth redirect URI as:

```text
https://carelink-api-orjq.onrender.com/auth/social/facebook/callback
```

3. Add `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET` privately in Render. Also set `FACEBOOK_GRAPH_VERSION` to a supported version shown by the Meta app, in the format `vNN.0` using the actual version number. No Graph version is silently guessed by the backend.
4. Save and redeploy. `/auth/providers` should report `facebook.available: true`.
5. In development mode, test with people who have the appropriate role/access in the Meta app. Complete any Meta review and policy requirements before offering it to everyone.

Meta may require published privacy and data-deletion URLs and other app details. Those must describe the team's real practices and contact details; this change does not publish invented policy pages or claim public app approval. Account linking, account deletion and password recovery remain separate work.

## Verification and limits

Tests cover guest feature prompts, cancellation, small-phone layout, registration limits and normalization, useful 422 field messages, unavailable provider states, PKCE, callback state/host checks, replay prevention, expired flows, email-collision denial, disabled accounts, Google signed-token verification and Facebook app/token verification with mocked upstream responses.

Real Google/Facebook account sign-in cannot be verified before developer credentials, allowed callbacks and provider access are configured. Existing backend email/password authentication and authorization stay in place. No provider receives medicine schedules, readings, caregiver records or research predictions from this integration.

Recorded authentication checks: Flutter analysis passed; all 45 Flutter tests then passed; all 33 backend tests passed; `npm run build` loaded the Neon configuration and compiled the Python backend successfully. After the UI redesign, the Flutter suite increased to 62 passing tests. The debug APK built and was installed over the existing emulator app with its data retained. The guest welcome and login prompt were visually checked. No real provider credentials were used, and no successful public provider sign-in is claimed.

The existing backend tests still emit a Starlette/httpx deprecation warning, and the Android browser plugin reports a future Flutter/Kotlin compatibility warning. Both checks complete successfully with the current pinned environment.

Use the [two-commit checkpoint instructions](account-checkpoint.md) to save this work without including the portal or local credential files.

## Primary references

- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [Google web-server OAuth setup](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google token verification library](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.id_token.html)
- [Meta manual Facebook Login flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/)
- [Flutter Web Auth 2 setup](https://github.com/ThexXTURBOXx/flutter_web_auth_2)
