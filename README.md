# CareLink

BSCS Final Year Project: medication reporting and chronic-care coordination for hypertension and diabetes.

**Progress update: 4 November 2026.** The patient-app checkpoint includes the redesigned screens, guest welcome and clearer account forms. The existing FastAPI backend is deployed on Render with Neon PostgreSQL. Google/Facebook sign-in code is included in separate app and backend checkpoints; the deployed service detects both provider settings and passes start/cancellation checks. Real-account Android walkthroughs still need confirmation. The web portal is a separate team workstream. Use fictional data for testing; CareLink remains an FYP prototype, not a clinically validated product.

## Project documents

- [Approved project scope](Docs/planning/project-scope.md)
- [Detailed medication and consent workflow](Docs/requirements/medication-workflow.md)

## Current progress

### Patient app

- Patient sign-up/sign-in, editable name and chronic condition, Patient ID and QR display.
- Intended Android release ID: `com.carelinkteam.patient`. Native Google account selection and the Facebook Android SDK replace the earlier browser-handoff client. The SDK update passes 65 app tests and 49 backend tests; native endpoint deployment and real account walkthroughs are being completed.
- Guest welcome with account prompts for private features, hosted-server configuration outside the patient UI, and clear inline registration errors.
- Redesigned Today, History and Profile with readable timestamps, clear empty states, grouped settings, a separate QR/Patient ID page and consistent medicine/report/reading/caregiver forms. Small-screen checks cover larger text; clinical and physical-device usability acceptance remains open.
- Google/Facebook browser sign-in client, backend identity verification and setup guide. Both provider settings are detected by the deployed backend, and start/cancellation checks pass. Real-account sign-in and session restoration still need Android walkthrough confirmation.
- Daily medication schedules with multiple times, effective dates and explicit timezone; patient ownership enforced by the API.
- Today and History screens, Taken/Skipped reporting, approximate taken times and reasoned corrections with server audit records.
- Local phone cache and durable upload queue, account separation, acknowledgement and visible conflict handling.
- Notification scheduling, single recording follow-up, snooze and cancellation after a local report; physical-device acceptance is still required.
- BP and glucose entry with units and measurement times.

### Backend and AI

- FastAPI account access rules, schedules, reports, readings and caregiver-consent APIs are committed and pushed.
- The backend is deployed at [CareLink API](https://carelink-api-orjq.onrender.com), backed by Neon PostgreSQL. Health and API documentation checks passed; physical-phone acceptance remains outstanding.
- A synthetic adherence-model experiment, Colab evidence and a separate research-example endpoint are available. Live personal adherence prediction remains unfinished and unvalidated.
- Google/Facebook verification and one-time account-handoff code has its own backend authentication checkpoint. Its 33 backend tests pass; real provider sign-in remains pending walkthrough confirmation.

### Web portal — separate workstream

- The caregiver/coordinator/admin portal is not part of the patient-app checkpoint.
- The portal will use the backend API contract after the backend deployment is available.

## Technology and folders

| Component | Technology | Location |
| --- | --- | --- |
| Android patient app | Flutter / Dart | `apps/patient_app/` |
| Connected phone screens/storage | Flutter, SQLite, secure token storage | `apps/patient_app/lib/connected/` |
| Caregiver/coordinator/admin portal | Angular / TypeScript — separate team workstream | `web-portal/` |
| API | FastAPI / Python — Render deployment | `backend/app/` |
| Server data | SQLAlchemy; Neon PostgreSQL, isolated SQLite tests/local demos | `backend/` |
| ML experiments and evidence | Python / scikit-learn / Colab | `ML/` |
| Requirements, design, run instructions | Markdown and original proposal material | `Docs/` |

The original local patient prototype and its tests are retained. Its demo SQLite database is not uploaded or silently migrated into an account.

The professional package is a separate installation from the starter
`com.example.carelink_patient` build. Server records stay with their accounts;
the old installation's local cache and pending reports are not automatically
copied into the new app. No Play Console build has been uploaded or published.

## ML evidence

The existing experiment generated 120 fictional patients over 90 days (16,380 dose records). It produced 9,120 examples and excluded 2,072 unknown outcomes. Logistic regression was trained on 4,842 examples and evaluated on 1,081 validation examples from separate patients.

Synthetic validation accuracy was 71.3% versus a 66.6% majority baseline. At threshold 0.5, the model detected 108 of 361 reported-skip days and missed 253. This measures the invented simulator, not real-world usefulness. Final held-out evaluation and real-data feasibility remain unfinished.

- [Synthetic workflow](ML/synthetic/README.md)
- [Colab notebook](ML/notebooks/CareLink_Synthetic_Model_Training.ipynb)
- [Validation evidence](ML/evidence/colab-synthetic-baseline/validation_report.json)
- [Dataset feasibility](Docs/planning/daily-prediction-data-options.md)

## Next work

- Complete Google and Facebook sign-in walkthroughs on Android, including return to the app and session restoration. Deployed start/cancellation checks do not establish successful real-account sign-in.
- Complete the hosted app walkthrough, including registration, saved records and offline upload.
- Continue the synthetic-model threshold review and real-data feasibility work before claiming personal prediction.
- Test reminders, offline upload and account flows on a physical Android phone.
- Integrate the portal only through the documented backend API after the portal owner is ready.

No diagnosis, prescribing, treatment changes or proof of medicine ingestion is provided.

- [Hosted API deployment](Docs/implementation/deploy-render.md)
- [Guest/account flow and Google/Facebook setup](Docs/implementation/account-and-social-sign-in.md)
- [Patient UI redesign and verification](Docs/implementation/patient-ui-redesign.md)
- [Native sign-in and professional Android package](Docs/implementation/native-social-sign-in.md)
- [Commands to save the current checkpoint](Docs/implementation/account-checkpoint.md)

## Team and Git workflow

- Active repository: `C:\CareLink-Repo`.
- The Flutter patient app, backend/AI, and web portal follow the team's agreed ownership split.
- The web portal remains on its own workstream and must not be included in patient-app or backend/AI commits.
- Keep app, backend/AI and portal work in separate commits so the faculty can see each member's contribution.
- Assistant changes are never committed, pushed, merged or deployed automatically.
- Do not commit secrets, genuine patient information, generated builds, local databases, environments or dependency folders.
