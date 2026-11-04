# CareLink patient app

Flutter / Dart Android app for medication reporting and care-team coordination.

People without a saved sign-in open the guest welcome screen. Private features
ask for sign-in or account creation. Signed-in patients have schedules, reports,
history, profile, health readings and consent-based caregiver connections.

## Run

Open this folder in Android Studio, start the emulator, fetch packages and Run.
The current default API is `https://carelink-api-orjq.onrender.com`.

```powershell
Set-Location C:\CareLink-Repo\apps\patient_app
flutter --no-version-check pub get
flutter --no-version-check run -d emulator-5554
```

The API address lives in `lib/connected/config/app_config.dart`, with a
`CARELINK_API` build override for local development. Patients do not configure
server addresses. Saved sessions keep their original account/server scope.

## Organization

- `lib/main.dart`: starts the connected app.
- `lib/connected/connected_app.dart`: restores the secure session and switches between guest and patient flows.
- `lib/connected/screens/`: page controllers, guest/account forms and focused patient entry screens.
- `lib/connected/views/`: separate Today, History and Profile layouts.
- `lib/connected/models/`: presentation summaries that retain explicit dose outcomes.
- `lib/connected/utils/`: readable dates, times, names and units.
- `lib/connected/auth/`: shared validation, native Google/Facebook SDK boundary and server credential exchange.
- `lib/connected/widgets/`: reusable cards, action rows, empty states, notices, dose status, save bars, branding and account controls.
- `lib/connected/data/`: API client, account-scoped SQLite outbox/cache and reminders.
- `lib/core/theme/`: shared colour, typography, button, input and navigation styles.
- `assets/auth/`: Google sign-in brand asset and attribution.
- `test/`: regression tests including guest gates, validation, provider handoff and offline persistence.

Today focuses on medicines and the next useful action. History has a day selector
and explicit report counts. Profile groups care, routine and account options;
Patient ID and QR have their own page. Forms share clear labels and save controls.
See [the UI redesign notes](../../Docs/implementation/patient-ui-redesign.md).

## Google and Facebook

The Android build now uses native SDK sign-in. Google opens the device account
picker. Facebook uses its app when possible and may use a secure browser/custom
tab as an SDK fallback. Configure the final package, debug certificate and local
SDK settings using [the native setup guide](../../Docs/implementation/native-social-sign-in.md).

The application ID is `com.carelinkteam.patient`. It is different from the old
starter installation; uploaded records remain on the backend, while that old
installation's local cache/outbox is not automatically copied into this app.

Buttons stay disabled until the backend supports native sign-in and the local
Android SDK settings exist. The app contains no provider App Secret/Google Client
Secret or database password. See [the account guide](../../Docs/implementation/account-and-social-sign-in.md)
for server configuration and the history of the earlier browser implementation.

This update changes Android dependencies, resources and callbacks. Stop and Run
the app again after fetching packages; hot reload alone is not enough.

## Checks recorded on 4 November 2026

- Flutter analysis: no issues found.
- Flutter tests: 65 passed, including native SDK exchange, signed-in navigation, larger-text layouts,
  report/correction payloads, reading units and caregiver approval confirmation.
- Android debug APK: built for `com.carelinkteam.patient` and installed separately
  from the old starter package on the emulator.
- Guest welcome and account prompt: visually checked on the emulator.
- Signed-in Today, History, Profile, care ID, readings and medicine/reading
  entry forms: visually checked on the emulator. No account records were
  created during this design walkthrough.

Real provider sign-in and physical-phone acceptance remain separate checks.
The earlier browser-authentication package has been removed from the phone app.
