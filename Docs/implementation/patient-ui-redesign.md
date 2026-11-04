# Patient UI redesign

Updated: 4 November 2026. Implemented and saved as the patient-app checkpoint on
the existing `saleem` branch. The user requested this checkpoint be pushed.
Backend authentication changes remain separate. No merge into `main` or backend
deployment was performed for this UI update.

## What changed

- **Today:** light header, readable greeting/date, update indicator, compact saved-report count, consistent medicine cards and a useful first-medicine action. Care-team and reading shortcuts remain secondary to the medicine routine.
- **History:** calendar and scrollable week selector, explicit Taken/Skipped/Not confirmed counts when doses exist, readable record times and a clear empty state.
- **Profile:** avatar initials, editable details, grouped care/routine/account options and a shortcut to a separate Patient ID/QR screen.
- **Forms:** consistent medicine, dose-report, correction, reading and profile forms with visible labels, larger controls and a primary save/review action at the bottom.
- **Care team:** grouped requests, active connections and past connections. Requests show the person's name and open a permission review before approval.
- **Medicine management:** readable schedule times and dates, with confirmation before setting an end date.

The palette keeps the accepted teal-and-white direction. White cards, restrained
mint surfaces, clear borders and consistent spacing replace the older flat pages.
There are no decorative medical charts or invented personal predictions.

## Files and responsibilities

| Location in `apps/patient_app/lib/` | Responsibility |
| --- | --- |
| `core/theme/app_theme.dart` | Shared colours, text, buttons, fields, cards and navigation |
| `connected/screens/dashboard.dart` | Account data, refresh/outbox, reminders and page navigation |
| `connected/views/` | Separate Today, History and Profile layouts |
| `connected/screens/` | Focused forms, QR identity, care team, readings and medicine management |
| `connected/widgets/` | Shared cards, action rows, notices, status tags, empty states and save controls |
| `connected/utils/care_format.dart` | Human-readable dates, times, units and Unicode-safe initials |
| `connected/models/day_summary.dart` | Counts of explicit reported outcomes |

The dashboard delegates layout to the views instead of keeping every screen in
one file. Updating a profile also updates the root session so the new name can
be remembered securely on the phone.

## Behaviour the design preserves

- An unanswered dose stays **Not confirmed**. It is never counted as Skipped automatically.
- The offline report label remains **Saved on this phone—waiting to upload**. Pending uploads and conflicts remain visible; the UI blocks editing the same pending report again.
- Reports still queue locally before upload. Corrections keep their reason and expected server version; Taken reports keep actual/approximate time separately from entry time.
- Snooze changes the reminder, not the medicine schedule. Existing notification scheduling and cancellation are retained.
- Measurements retain their kind, unit and measurement time. Changing glucose units clears an unsaved numeric value so it cannot be silently reused with another unit.
- Patient approval is still required for caregiver access. Removing a connection still requires confirmation. Displaying or copying a Patient ID does not grant access.
- Pending reports still prevent sign-out. Account/server isolation and phone storage remain in the existing data layer.

## Readability and accessibility checks

- Body text is 16–17 logical pixels, supporting text 14, with larger headings.
- Controls use at least 48-pixel targets; primary buttons are approximately 52 pixels high and grow with their content.
- Text follows phone scaling. Today, History and Profile were checked at 320 logical pixels wide with 1.8 text scale.
- Status uses text and icons alongside colour. Dates and update times are formatted for people instead of displaying raw ISO timestamps.
- Page transitions respect the system's reduced-animation setting. Lists remain scrollable and long labels can wrap.

These checks do not establish usability for every person or replace testing with
patients, caregivers, screen readers and physical phones.

## Verification recorded on 4 November 2026

Commands were run from `C:/CareLink-Repo/apps/patient_app`:

```text
flutter --no-version-check analyze --no-pub
No issues found!

flutter --no-version-check test --no-pub --reporter expanded
00:06 +62: All tests passed!

flutter --no-version-check build apk --debug --no-pub
Built build/app/outputs/flutter-apk/app-debug.apk

adb -s emulator-5554 install -r -t <debug APK>
Success
```

Tests cover signed-in navigation, profile editing, larger-text layouts, explicit
dose counts, pending-upload protection, report/correction payloads, required
medicine details, BP payloads, unit switching and consent confirmation, along
with the existing account/storage regressions.

The build was installed as an update, retaining the emulator's app data.
Today, History, Profile, care ID, readings and the medicine/reading entry forms
were visually checked on Android. No schedules, measurements or caregiver
connections were created during this visual review. The account used for the
native preview has no saved doses; populated dose/report states were checked
with isolated test fixtures.

Local screenshots and command logs are in `C:/CareLink-FYP/validation/`; they
are kept outside Git. The build emits non-fatal Java native-access and
`flutter_web_auth_2` future-Kotlin-compatibility warnings. The current APK builds
and launches successfully.

## Save and review

Use [the checkpoint commands](account-checkpoint.md) to save the app and backend
work in separate commits. The web portal and unrelated planning files are not
part of this app checkpoint. Google/Facebook activation still requires the
developer-app configuration described in [the account guide](account-and-social-sign-in.md).
