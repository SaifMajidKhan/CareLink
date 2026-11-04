# CareLink colour scheme and prototype direction

Recorded: 2026-10-04
Status: teal-and-white direction accepted on 2026-10-05. The user requested a minimal patient side and more caregiver options. The connected Flutter patient UI was redesigned on 2026-11-04. The Figma boards below remain historical concepts; current implementation notes take precedence for the app.

## Current Flutter implementation — 4 November 2026

- Shared source: `apps/patient_app/lib/core/theme/app_theme.dart`.
- Patient tabs are Today, History and Profile. Care-team management opens from Today or Profile.
- Light page headers, white bordered cards, restrained mint accents and rounded bottom navigation replace the older solid teal headers.
- Today keeps a compact count of saved dose updates. It has no large progress dashboard or inferred adherence score.
- History uses a week selector and calendar, readable dates and explicit report counts.
- Profile groups care, routine and account actions. The QR code and full Patient ID open on a separate care-ID page.
- Medicine entry, dose reporting, readings, profile editing and caregiver requests use the same design system.
- Main supporting text is `#475569`; smaller secondary text is `#64748B`. The soft teal card surface is `#F0FDFA`.
- Text scales with phone settings. Controls use at least 48-pixel targets, with primary buttons around 52 pixels high. Layout checks cover a 320-pixel-wide phone at 1.8 text scale.
- Plain timestamps replace raw ISO strings. Report status always includes words and an icon, not colour alone.

See `Docs/implementation/patient-ui-redesign.md` for the change and verification record. The sections below describe the original design exploration, not the current implementation status.

## Main colours

| Use | Colour | Hex |
| --- | --- | --- |
| Primary buttons and selected navigation | Deep teal | `#0F766E` |
| Page background | Very light grey | `#F8FAFC` |
| Cards and white text on dark buttons | White | `#FFFFFF` |
| Main text | Dark navy | `#0F172A` |
| Supporting text | Slate grey | `#475569` |
| Taken status | Green | `#166534` |
| Not confirmed status | Amber | `#92400E` |
| Errors and removal actions | Red | `#B91C1C` |

## Supporting surfaces

| Use | Hex |
| --- | --- |
| Teal selection background | `#CCFBF1` |
| Taken status background | `#DCFCE7` |
| Unconfirmed/offline message background | `#FEF3C7` |
| Error background | `#FEE2E2` |
| Subtle borders | `#E2E8F0` |

Use pale colours as backgrounds with the matching dark text colour, not as small text on white. Use red sparingly for errors or destructive actions, not to imply that an unanswered dose is dangerous.

## Typography and layout

- Proposed font: Roboto, with regular, medium, and bold weights, subject to Figma font availability.
- Design reference: Android phone frame, 412 by 892 logical pixels.
- Body text: 16; supporting labels: 14; screen titles: 28-32.
- Tap targets: at least 48 by 48; primary buttons approximately 52 high.
- Page padding: 24; common spacing: 8, 12, 16, 24.
- Cards: rounded corners around 20, with restrained borders and shadows.
- Use text and icons alongside colour. Check contrast, large text, and readability during implementation.
- Keep the theme in one shared Flutter theme file when implementation begins.

## Historical first visual preview (superseded by Concept 02)

Create an editable Figma mockup before building the app. Start with Today, Record a dose, and Profile/My Care identity. Include a small palette on the presentation board. Use clearly fictional data and label the concept as a demo.

The Today screen should show the daily medicine list, a summary such as "2 of 4 doses reported taken", clear dose status, and an obvious way to record a dose. The dose screen should support Taken, Skipped, and the agreed 10-minute snooze. The profile should show the Patient ID and a QR preview; scanning is a connection request, not automatic access.

Original navigation: Today, History, My Care, Profile. Concept 02 below replaces this with three patient tabs.

## Product rules the design must preserve

- No response means Not confirmed, not automatically Skipped.
- Snooze changes the notification only, not the medicine schedule.
- The single automatic recording follow-up is 30 minutes after the original reminder; this is not a medical late-dose rule.
- Offline reports show "Saved on this phone—waiting to upload".
- Caregiver connections require patient acceptance. Patients can remove access after confirmation without a compulsory waiting period.
- No genuine patient information, real predictions, or live account connections are represented in the mockup.

## Review and handoff

The design is a proposal until the user confirms its appearance. Editable Figma design: https://www.figma.com/design/I1wRDorjOz3qWjRMkWCg5Y?node-id=4-49 (SALEEM Aman's team). Three screens were created: Today, Record a dose, and Profile. The QR is a nonfunctional visual placeholder. This is a static visual concept; navigation and saving are not wired up. Do not claim a working Flutter app from a Figma mockup.

Suggested commit after design review: `docs: add CareLink colour scheme and prototype direction`.
## Concept 02: patient simplicity and caregiver detail

Updated: 2026-10-05. The user approved making the next preview with a simpler patient Home, caregiver Dashboard and Patient Details.

Review board: https://www.figma.com/design/I1wRDorjOz3qWjRMkWCg5Y?node-id=15-87

The original board remains in the same file for comparison. Concept 02 uses editable Figma text, layouts and existing button instances. It is a static preview, not a working application.

### Patient

- Three tabs: Today, History, My Care.
- Today focuses on the current dose with large Taken, Skipped and Remind me in 10 minutes buttons, followed by the next medicine.
- Remove the large daily progress card from Home.
- The profile shortcut opens Patient ID, QR and settings. My Care contains caregivers, requests and removal options.
- Additional recording questions appear only when needed; exact interaction details still need design.
- Pending uploads must still show "Saved on this phone—waiting to upload". The current preview shows an online, unconfirmed dose; the offline state is not illustrated on this board.

### Caregiver

- Dashboard: approved patients, latest uploaded dose summaries, last update times, and QR/Patient ID connection requests.
- Patient Details: Today, History and Notes sections; explicit dose status; latest care note and Add care note action.
- Further planned views: Updates, history/trends and connection management under More. These destinations are not fully drawn or connected yet.
- Stale records show an out-of-date notice, not an automatic missed-dose judgment.
- Caregivers can view reports and add separate notes. They cannot edit medication schedules or record doses on the patient's behalf.
- Connection requests still require patient approval; a caregiver may leave a connection.

Validation: visually inspected all three screens for readable labels, button text and layout. All displayed people, medicines and reports are fictional. No application functionality or notification behavior was tested.

Suggested commit after review: docs: refine patient and caregiver prototype direction
