# Caregiver mobile flow and simpler patient screens

CareLink now has a caregiver option in the same Android app. A caregiver uses a separate email and password account. The existing backend handles connection requests and decides whether records can be shared.

## Try it with two test accounts

1. On the patient phone, sign in and open **Profile → Your care ID**. Leave the QR on screen, or tap **Copy patient ID** for manual entry.
2. On the caregiver phone, open CareLink and choose **I’m a caregiver**. Create a caregiver account or sign in with one.
3. Choose **Add a patient → Scan patient QR** and allow camera access when asked. If the camera is unavailable, enter the full patient ID instead.
4. Check the ID and tap **Send request**. The caregiver sees **Waiting for patient approval**.
5. On the patient phone, open **Profile → My care team**. Review the named request and choose **Approve connection** or decline it.
6. Back on the caregiver phone, refresh connections and tap the connected patient to see today’s medicines and reports. This screen has no editing actions.
7. On the patient phone, remove access from **My care team**. Refresh the caregiver’s updates to verify that access is blocked.

Scanning alone sends nothing. The QR is an identifier; the API requires an active approval to serve shared records. The caregiver app fetches these records online and does not save a separate offline copy.

## What changed for patients

| Screen | Change |
| --- | --- |
| Today | One dose to focus on, with a short expandable list for the whole day. Tap a row for details and any available correction action. |
| History | A date button and previous/next controls replace the weekly strip. Tap a compact dose row for its full details. |
| Profile | Short links to Care ID, care team, health readings, medicines and settings. Reminders, reconnecting and sign-out live in Settings. |
| Forms | Repeated introductions were removed. Form fields, consent and review steps, and save buttons remain. |

Spacing was reduced between sections while preserving the app’s text sizes, Android text scaling, labeled controls and touch targets. Longer lists and larger text can still scroll. These decisions follow [Flutter’s accessible UI guidance](https://docs.flutter.dev/ui/accessibility/ui-design-and-styling) and [Android’s guidance for accessible controls](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views).

## Verification

- Flutter analysis found no issues; all 69 Flutter tests passed.
- The Android debug APK built successfully with the camera permission. The app ID remains `com.carelinkteam.patient`.
- The existing API workflow test verified that pending requests cannot read records, approval enables read access, and removal revokes it.
- QR parsing, manual ID entry and request confirmation were tested in Flutter. A physical camera scan and Android’s permission prompt still need a device check.

## Device checks to finish

- Try the camera with a QR shown on a second phone. Also deny permission and finish the request by typing the ID.
- Ask an older adult and a middle-aged adult to try recording a dose, finding yesterday’s report, and approving a caregiver. Observe where they pause, scroll or tap the wrong control, then adjust the layout.
- Try the same actions with larger Android text and TalkBack.
