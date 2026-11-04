# Native Android sign-in and app identity

Updated: 4 November 2026. Native Google/Facebook sign-in replaces the phone's
earlier browser-handoff flow. Keep the app and backend changes in separate
commits on `saleem`; the web portal is outside this change.

## Android identity

- App label: **CareLink**.
- Application ID and Kotlin namespace: **`com.carelinkteam.patient`**.
- Main activity: **`com.carelinkteam.patient.MainActivity`**.
- No CareLink build has been uploaded to Google Play Console, according to the user.
- The ID is the intended release identity; Play Console still needs to accept its availability when the first bundle is uploaded. No Play Store upload or publication is performed by this change.
- Keep the same application ID for later store updates. The display name can be managed separately.

The old `com.example.carelink_patient` app is a separate Android installation.
Changing the ID does not migrate its local phone database or pending reports.
Keep the old development installation until any needed reports are uploaded.
Uploaded records remain under the same backend account and can be downloaded
after signing in to the new installation. Do not uninstall or clear the old app
as part of this setup.

## Local SDK configuration

Copy `apps/patient_app/android/native-auth.properties.example` to
`native-auth.properties` in the same folder. The actual local file is ignored by
Git. It has three settings:

| Setting | Source |
| --- | --- |
| `GOOGLE_SERVER_CLIENT_ID` | Existing Google **Web application** OAuth client ID, matching Render's `GOOGLE_CLIENT_ID` |
| `FACEBOOK_APP_ID` | The Meta app ID matching Render's `FACEBOOK_APP_ID` |
| `FACEBOOK_CLIENT_TOKEN` | Meta App settings → Advanced → Security → Client Token |

The Facebook Client Token is an Android SDK configuration value designed for a
client build. It is different from the App Secret. The Facebook App Secret and
Google Client Secret stay on the backend; never put them in this file or APK.
The local config is kept out of Git even though public client IDs may be
embedded in the application. CI can instead set `CARELINK_`-prefixed environment
variables with the same setting names.

Gradle generates Android resources from these values. A small Kotlin channel
returns only the public Google server client ID and a Facebook readiness flag
to Dart; it never returns the Client Token. Meta automatic app-event logging
and advertiser-ID collection are disabled. Unused advertising-ID/Privacy Sandbox
advertising permissions contributed by dependencies are removed from the merged
manifest.

## Google Android registration

In the same Google Cloud project as the Web client, create/register an **Android**
OAuth client with package `com.carelinkteam.patient` and this machine's public
debug signing-certificate SHA-1:

```text
A4:68:3A:67:84:00:C1:B8:A0:BC:31:54:8F:A6:C1:33:8D:DC:AE:C0
```

Retain the Web client: its ID is the native SDK's `serverClientId` and the backend's
expected ID-token audience. The Android OAuth client is the package/certificate
registration; its ID does not replace the Web ID in Render or the settings file.
An Android client was initially created for the starter package, before the user
requested a permanent professional ID. The user then confirmed that the new
package was registered in the same Google Cloud project.

Google uses the official `google_sign_in` SDK and the device's account-selection
UI. Accounts signed in only to a desktop Chrome browser are not automatically
Android device accounts. A device without a usable Google account/services may
need setup before the picker can complete sign-in.

## Meta Android registration

Register the Android platform with:

```text
Package: com.carelinkteam.patient
Class:   com.carelinkteam.patient.MainActivity
Key hash: pGg6Z4QAwbigvDFUj6bBM43crsA=
```

This is the same debug certificate in Meta's Base64 SHA-1 format. The key hash
does not change when the package is renamed. The user successfully saved the
starter Android platform after Meta's package/store warning, then confirmed that
the new package and activity above were saved in Meta. A store lookup does not establish
that the chosen package is globally available in Play Console.

Facebook uses its official Android SDK through `flutter_facebook_auth`, with
`nativeWithFallback`. It can use an installed Facebook app. Meta can use a secure
browser/custom tab when native app login is unavailable. This is provider-owned
behaviour, not an app-built password form; a universal in-app Facebook account
popup cannot be guaranteed.

## Application/server flow

1. `/auth/providers` supplies `native_available` alongside the older `available` flags. A new client also checks its local SDK configuration before enabling a provider.
2. Google SDK returns an ID token; Facebook SDK returns a classic user access token. Screens do not collect provider passwords or trust client-supplied names/emails as identity.
3. The phone sends that credential over HTTPS to `/auth/social/google/native` or `/auth/social/facebook/native`.
4. The server verifies Google signature, issuer, expected Web audience, expiry and verified email; Meta tokens are inspected for validity, app ID, user type, user ID and expiry before fetching the matching profile with an app-secret proof.
5. The existing provider/subject identity mapping returns the same CareLink patient account. The phone saves only the resulting CareLink session in its secure session store; the SDK owns any provider cache.

Browser nonce and PKCE checks remain on the legacy browser endpoints for older
clients. Native Google ID tokens are directly submitted credentials: they do not
use that browser redirect flow. Native Android authorized-party IDs can differ
from the server audience. Matching email alone never merges accounts. Disabled
accounts and non-patient identities remain rejected.

## Storage compatibility

The current Facebook package requires `flutter_secure_storage` 10.3.1. The app
uses that migration-capable v10 release, rather than jumping directly from v9 to
v11. Cipher migration and migration backup are enabled; automatic reset on error
is disabled. SQLite dose records and the outbox implementation are unchanged.
The native session restore/write path retains the existing `carelink_session`
key. Real saved-login migration is separate from mocked storage tests, and the
package rename creates a new app sandbox regardless of cipher migration.

## Verification

- Flutter analysis: no issues found.
- Flutter tests: **65 passed**, including native credential exchange, cancelled SDK flows, older-backend handling and missing Android configuration.
- Backend tests: **49 passed**, including signed native Google tokens, bad audience/issuer/expiry/signature rejection, no client-profile trust, Meta token inspection and existing browser/medication workflows.
- Root `npm run build`: backend configuration and Python compilation passed.
- Android debug APK built successfully for `com.carelinkteam.patient` after enabling AGP resource generation for SDK settings. Real native-picker/account completion still needs an Android walkthrough.

Real Google/Meta account completion must still be confirmed on Android. Do not
claim a successful provider login from configuration flags, test fixtures or a
build result. Release signing and first Play Console upload are separate work;
register the eventual Play App Signing certificate for Google and Meta before
testing a store-distributed build. No production signing key is generated here.

## References

- [Android application ID and namespace](https://developer.android.com/build/configure-app-module)
- [Official Google Flutter Android integration](https://pub.dev/packages/google_sign_in_android)
- [Google SDK initialization contract](https://pub.dev/documentation/google_sign_in/latest/google_sign_in/GoogleSignIn/initialize.html)
- [Facebook Flutter SDK setup and login behaviour](https://pub.dev/packages/flutter_facebook_auth)
- [Secure storage migration guidance](https://pub.dev/packages/flutter_secure_storage/changelog)
