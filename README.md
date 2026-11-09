# CareLink

CareLink is our approved BSCS Final Year Project: a medication-reporting and care-coordination app for people managing hypertension or diabetes.

**Progress updated: 9 November 2026.** The Flutter Android app includes medication schedules, dose reports, history, health readings, profiles and offline reporting. The same app now has a caregiver mode for scanning a patient’s QR code or entering their ID and requesting access. The patient decides whether to approve the request. The FastAPI backend is hosted on Render and stores records in Neon PostgreSQL. A separate model was trained on synthetic data, with its Colab notebook and results saved in this repository.

The project is a working development prototype. Final device acceptance, complete social-login walkthroughs, production release preparation and useful real-world AI prediction remain open.

## Progress at a glance

| Area | Current status |
| --- | --- |
| Planning | Project approved; scope, medication workflows, consent rules and offline behaviour documented |
| Patient app | Connected Flutter app with schedules, reporting, history, reminders and profiles |
| Caregiver mode | Email account, camera QR scanner, manual ID entry and read-only dose updates after approval; physical camera test pending |
| Design | Shorter Today, History, Profile and forms; large text and touch targets retained for older and middle-aged patients |
| Backend | FastAPI deployed on Render with Neon PostgreSQL |
| Google login | Native SDK implemented; user confirmed that the device account picker opens; completed login and session restoration still need confirmation |
| Facebook login | Native SDK, Android registration and backend verification configured; real-account walkthrough still pending |
| AI/ML | Synthetic-data generation, training and validation completed for a baseline experiment; live personal prediction is not deployed |
| Web portal | Separate team member's workstream; its completion is not claimed by this app/backend checkpoint |
| Release | Debug APK available; no CareLink APK/AAB uploaded to Google Play Console |

## Android app: implemented features

### Accounts and profile

- Guest welcome screen; private actions ask the user to sign in or create an account.
- Email/password registration and sign-in, with clearer field validation and errors.
- Secure session storage and account-scoped phone data.
- Editable patient name and chronic condition.
- Patient ID and QR display on a dedicated care-ID page.
- API address configured by the developer, outside the patient-facing account screen.
- Native Google account selection and Facebook SDK integration. The backend checks provider credentials before creating a CareLink session.

### Medication schedules and reports

- Add a medicine schedule with multiple daily times, effective dates and an explicit timezone.
- Manage schedules and confirm when a schedule should end.
- Today shows one dose to focus on; **All doses** opens the rest of the day when needed.
- Record **Taken** or **Skipped**, including actual or approximate taken time where relevant.
- Keep the time medicine was reportedly taken separate from the time the report was entered or received.
- Correct a report with a reason and a server audit record.
- Browse History with a date selector and short dose rows. Open a row for full details and any available correction action.
- An unanswered dose remains **Not confirmed**; it is never automatically counted as Skipped.

### Offline reporting and reminders

- Download schedules/history into a local SQLite cache, with the last update time shown.
- Save dose reports to a durable upload queue before sending them to the backend.
- Show **“Saved on this phone—waiting to upload”** while a report is pending. A caregiver receives the server update after upload.
- Handle retries without silently creating duplicate reports; show conflicts for review.
- Keep cached data and queued reports separate for each account/server.
- Protect pending reports during sign-out and prevent a second edit of the same pending report.
- Schedule local reminders for downloaded doses, a 10-minute snooze and one recording follow-up 30 minutes after the original reminder.
- Cancel relevant reminders after a local report. Snooze changes the notification, not the medication schedule.

Android controls notification delivery; exact timing, reboot behaviour and background delivery still need physical-phone acceptance checks.

### Health readings and caregiver consent

- Record blood-pressure and glucose readings with their units and measurement times.
- View saved readings through the connected app.
- Review caregiver requests and permissions before accepting or declining them.
- View active and past connections; confirm removal of caregiver access without a compulsory 7- or 14-day waiting period.
- Caregivers choose **I’m a caregiver** on the welcome screen and use email/password to sign in or create a caregiver account.
- **Add a patient** lets a caregiver scan the QR from **Profile → Your care ID**, or enter the full patient ID. Scanning fills the ID; **Send request** sends it for approval.
- Caregivers see a pending state until the patient approves. Approved connections can open today’s shared doses and reports as a read-only view.

See the [two-account walkthrough](Docs/implementation/caregiver-mobile-and-accessibility.md) for a phone demo and the camera permission fallback.

### UI and file organization

- Shorter Today, History and Profile layouts bring common actions closer to the top.
- Profile links directly to care ID, care team, health readings, medicines and settings. QR details, reminders and sign-out each have a clear place.
- Medicine, report, correction and reading forms keep the required fields and review steps with fewer repeated headings.
- Shared theme, reusable widgets, separate views, data services, authentication adapters and models.
- Layout checks at 320 logical pixels wide and 1.8 text scale; statuses use words/icons alongside colour.
- Primary teal `#0F766E`, background `#F8FAFC`, main text `#0F172A` and white cards.

See the [design record](Docs/design/colour-scheme.md), [earlier UI work](Docs/implementation/patient-ui-redesign.md) and [latest patient screen changes](Docs/implementation/caregiver-mobile-and-accessibility.md). Final usability checks with patients, caregivers and screen readers remain open.

## Backend and hosting

- FastAPI APIs for accounts, profiles, schedules, dose reports, corrections, readings and caregiver connections.
- Access checks block unrelated users and caregivers without active patient approval. Revocation removes server access.
- Caregiver/coordinator API support for relationship-bound notes, summaries and review items for explicitly reported skips.
- Administrator API boundaries restrict account/activity views to metadata; coordinator assignments remain pending until patient approval.
- Password hashing, expiring sessions, server-side token hashing, request validation and audit records.
- Google/Facebook credential verification on the server; no automatic linking of accounts based only on a matching email address.
- Earlier browser-login routes remain available for older clients; the current Android app uses native SDKs.
- Render deployment configuration and Neon integration, using pooled request connections and a direct connection for initial table creation.
- Repeatable Neon/API smoke test verified fictional account creation, persisted schedules/reports/readings, duplicate prevention, consent and revocation; temporary test records were cleaned up.

| Hosted resource | Address |
| --- | --- |
| API | [CareLink API](https://carelink-api-orjq.onrender.com) |
| Health check | [API health](https://carelink-api-orjq.onrender.com/health) |
| API documentation | [Interactive API reference](https://carelink-api-orjq.onrender.com/docs) |

The phone communicates with the API and never receives database credentials. Provider secrets and database URLs stay in private environment configuration. This deployed development service does not yet establish production readiness.

## Android identity and social-login status

- App name: **CareLink**.
- Intended permanent application ID: **`com.carelinkteam.patient`**.
- Google Android registration and Meta Android platform settings were updated for this package, as confirmed by the user.
- The APK package/activity and signing certificate were checked. The debug APK is installed and starts on the emulator.
- The native Google account picker opens in the new app, as confirmed by the user. Choosing an account, returning to Today and staying signed in after reopening are still awaiting confirmation.
- Both deployed native endpoints are enabled and reject invalid credentials with HTTP 401. These checks do not establish successful real-account login.
- Facebook uses its installed app when available and may use a secure browser/custom tab as the SDK fallback. The current emulator has Google Play services but no Facebook/Facebook Lite app.
- The local Android SDK settings file is ignored by Git. Google Client Secret and Facebook App Secret remain on the backend.

The new package is a separate installation from `com.example.carelink_patient`. Server records stay with their accounts; the old installation's local cache and pending reports are not automatically copied. Production signing, Play App Signing certificate registration and the first Play Console bundle upload remain separate work. Play Console has not yet confirmed package availability through a first upload.

See the [native sign-in guide](Docs/implementation/native-social-sign-in.md) for setup and verification details.

## AI/ML: completed experiment and evidence

Public dataset options were researched for daily adherence prediction. No suitable unrestricted real daily hypertension/diabetes dataset was verified in that research, so the prototype pipeline uses clearly labelled synthetic data.

Completed work:

1. Created a reproducible generator with seed 42: **120 fictional patients**, **90 days**, **16,380 dose records**.
2. Prepared **9,120 daily examples**, with historical features and separate patient groups for training, validation and testing.
3. Identified **2,072 unknown outcomes** across all splits; unknown outcomes are excluded from the binary-model evaluation rather than treated as skips.
4. Trained a logistic-regression baseline on **4,842 resolved examples** and evaluated it on **1,081 validation examples**.
5. Ran the training in Google Colab and saved the notebook, validation report and model parameters as evidence.
6. Added a separate backend research-example endpoint; it does not produce patient-specific predictions.

| Recorded synthetic validation result | Value |
| --- | --- |
| Logistic-regression accuracy | 71.3% |
| Majority-baseline accuracy | 66.6% |
| Recall for reported-skip days at threshold 0.5 | 29.9%: detected 108 of 361; missed 253 |
| Final held-out test evaluation | Not performed |

These results measure the invented simulator. They do not show that the model predicts real missed medicine or is clinically useful. The target is a reported outcome, not proof of medicine ingestion. Threshold review, independent real-data feasibility and later-calendar-period evaluation remain unfinished. Live personal prediction is not deployed.

- [Synthetic generation, preparation and training instructions](ML/synthetic/README.md)
- [Executed Colab notebook](ML/notebooks/CareLink_Synthetic_Model_Training.ipynb)
- [Validation report](ML/evidence/colab-synthetic-baseline/validation_report.json)
- [Saved synthetic-model parameters](ML/evidence/colab-synthetic-baseline/model_parameters_SYNTHETIC.json)
- [Earlier dataset research and options](Docs/planning/daily-prediction-data-options.md)

The earlier research document records the decision before training; the results above and the committed training evidence describe the later completed experiment.

## Latest recorded verification

The table includes the latest mobile checks and earlier backend and deployment checks.

| Check | Result |
| --- | --- |
| Flutter static analysis | No issues found (9 November 2026) |
| Flutter automated tests | **69 passed** (9 November 2026) |
| Backend automated tests | **49 passed**, using isolated test databases |
| Root `npm run build` | Passed: Neon configuration loaded and Python backend compiled |
| Android debug build | Updated APK built and package ID/camera permission checked (9 November 2026); the earlier build was installed and launched on the emulator |
| Patient UI checks | 320-pixel-wide layouts at 1.8× text, plus a short screen with multiple doses and reachable report/correction actions |
| Caregiver mobile checks | Automated QR parsing, manual input, request confirmation, pending/approved/revoked state and read-only display; physical camera test pending |
| API consent recheck | Existing request, approval, dose reporting and revocation test passed against an isolated database (9 November 2026) |
| Earlier HTTP-to-Neon smoke test | Passed persistence, duplicate prevention, consent/revocation and test-data cleanup |
| Deployed native authentication | Both providers enabled; invalid Google/Facebook credentials rejected with 401 |
| User's native Google check | Account picker opens; successful login/session restoration still pending confirmation |

Automated checks cover account gates, validation, offline persistence, report/correction payloads, reminder logic, consent, native credential exchange and rejected credentials. They do not replace complete physical-phone walkthroughs.

The root build command checks backend tooling; it does not build the Flutter APK or the separate web portal.

## Technology and repository structure

| Location | Purpose |
| --- | --- |
| `apps/patient_app/` | Flutter/Dart Android patient and caregiver app and its tests |
| `apps/patient_app/lib/connected/` | Connected screens, views, authentication, API client, SQLite cache/outbox and reminders |
| `apps/patient_app/lib/core/theme/` | Shared colours, typography and control styles |
| `backend/app/` | Python/FastAPI API, security, storage and authentication |
| `backend/tests/` | Backend workflow, configuration and authentication tests |
| `ML/synthetic/` | Data generator, example preparation, baseline training and tests |
| `ML/notebooks/` | Google Colab training notebook |
| `ML/evidence/` | Saved model-training evidence |
| `Docs/` | Requirements, design, deployment and implementation records |
| `web-portal/` | Angular/TypeScript portal: separate member's workstream |
| `render.yaml`, `neon.ts` | Hosting/database configuration without secret values |

The earlier local-only Flutter prototype and its regression tests are retained. Its demo database is not silently uploaded into a connected account.

## Next steps, in order

1. **Finish social-login acceptance:** complete Google login and reopening/session checks; test Facebook with a real account and its app-switch/fallback behaviour.
2. **Run the complete patient journey on a physical phone:** sign in, create schedules, report/correct doses, view history, edit profile and save readings against the hosted API.
3. **Verify offline and reminder behaviour on that phone:** save offline, restart, reconnect, confirm upload and caregiver visibility; test denied permissions, background delivery, snooze and reboot recovery.
4. **Test the mobile caregiver flow on two phones:** scan the QR, repeat with manual ID entry, approve or decline, view permitted updates and check that removal blocks access. Ask older and middle-aged users to try the shorter patient screens.
5. **Continue ML work:** review the validation threshold and error trade-offs, retain the held-out test for final evaluation, and seek suitable real data before making personal-prediction claims.
6. **Prepare production features and release:** email ownership checks/password recovery, authenticated provider linking if required, durable abuse controls, versioned schema migrations/backup procedures, encrypted phone databases, release signing and Play Console testing.

CareLink currently records reports and supports coordination. It does not diagnose, prescribe or recommend treatment changes.

## Project documents and running the app

- [Approved project scope](Docs/planning/project-scope.md)
- [Medication, consent and offline requirements](Docs/requirements/medication-workflow.md)
- [Patient app run instructions](apps/patient_app/README.md)
- [Backend run instructions](backend/README.md)
- [Neon integration verification](Docs/implementation/neon-verification.md)
- [Render deployment guide](Docs/implementation/deploy-render.md)
- [Account and social-login setup/history](Docs/implementation/account-and-social-sign-in.md)

Some implementation documents describe earlier checkpoints. Use this dated README and the latest linked verification notes for the current overall status.

## Team and Git workflow

- Active repository: `C:\CareLink-Repo`.
- Continue this work on the existing **`saleem`** branch, keeping changes in focused commits.
- App/backend/AI and portal work follow the team's ownership split; portal changes are saved by its owner.
- Push app and documentation checkpoints to `saleem`. Keep them unmerged into `main` until review.
- Keep private environment files, Android local SDK settings, passwords/tokens, real patient information, generated builds, local databases and dependency folders out of Git.
