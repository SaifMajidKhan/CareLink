# CareLink

BSCS Final Year Project: medication reporting and chronic-care coordination for hypertension and diabetes.

**Progress update: 4 November 2026.** The patient-app checkpoint was pushed to the `saleem` branch in commit `4083565`. Backend and AI work are prepared locally for Saleem's next separate checkpoint. The web portal is owned by another team member. Use fictional data only; CareLink is an FYP prototype, not a clinical product.

## Project documents

- [Approved project scope](Docs/planning/project-scope.md)
- [Detailed medication and consent workflow](Docs/requirements/medication-workflow.md)

## Current progress

### Patient app — pushed to `saleem`

- Patient sign-up/sign-in, editable name and chronic condition, Patient ID and QR display.
- Daily medication schedules with multiple times, effective dates and explicit timezone; patient ownership enforced by the API.
- Today and History screens, Taken/Skipped reporting, approximate taken times and reasoned corrections with server audit records.
- Local phone cache and durable upload queue, account separation, acknowledgement and visible conflict handling.
- Notification scheduling, single recording follow-up, snooze and cancellation after a local report; physical-device acceptance is still required.
- BP and glucose entry with units and measurement times.

### Saleem's backend and AI — next checkpoint

- FastAPI backend structure, account access rules, schedules, reports, readings and caregiver-consent APIs are prepared locally.
- PostgreSQL and Render deployment configuration is prepared but has not yet been committed or deployed.
- A synthetic adherence-model experiment and Colab training evidence are available. The next task is to connect this research demonstration to a safe, non-medical adherence-insight endpoint.

### Web portal — separate team-member responsibility

- The caregiver/coordinator/admin portal is not part of Saleem's patient-app checkpoint.
- The portal will use the backend API contract after the backend deployment is available.

## Technology and folders

| Component | Technology | Location |
| --- | --- | --- |
| Android patient app | Flutter / Dart | `apps/patient_app/` |
| Connected phone screens/storage | Flutter, SQLite, secure token storage | `apps/patient_app/lib/connected/` |
| Caregiver/coordinator/admin portal | Angular / TypeScript — owned by another member | `web-portal/` |
| API | FastAPI / Python — Saleem's next checkpoint | `backend/app/` |
| Server data | SQLAlchemy; SQLite local demo, PostgreSQL deployment planned | `backend/` |
| ML experiments and evidence | Python / scikit-learn / Colab | `ML/` |
| Requirements, design, run instructions | Markdown and original proposal material | `Docs/` |

The original local patient prototype and its tests are retained. Its demo SQLite database is not uploaded or silently migrated into an account.

## ML evidence

The existing experiment generated 120 fictional patients over 90 days (16,380 dose records). It produced 9,120 examples and excluded 2,072 unknown outcomes. Logistic regression was trained on 4,842 examples and evaluated on 1,081 validation examples from separate patients.

Synthetic validation accuracy was 71.3% versus a 66.6% majority baseline. At threshold 0.5, the model detected 108 of 361 reported-skip days and missed 253. This measures the invented simulator, not real-world usefulness. Final held-out evaluation and real-data feasibility remain unfinished.

- [Synthetic workflow](ML/synthetic/README.md)
- [Colab notebook](ML/notebooks/CareLink_Synthetic_Model_Training.ipynb)
- [Validation evidence](ML/evidence/colab-synthetic-baseline/validation_report.json)
- [Dataset feasibility](Docs/planning/daily-prediction-data-options.md)

## Next work

- Commit the backend and AI work as a separate Saleem checkpoint.
- Deploy the backend with PostgreSQL and a public HTTPS address for real-phone FYP demonstrations.
- Connect the synthetic-model research result to a clearly labelled, non-medical adherence-insight endpoint.
- Test reminders, offline upload and account flows on a physical Android phone.
- Integrate the portal only through the documented backend API after the portal owner is ready.

No diagnosis, prescribing, treatment changes or proof of medicine ingestion is provided.

## Team and Git workflow

- Active repository: `C:\CareLink-Repo`.
- Saleem develops the Flutter patient app, backend and AI work on `saleem`; reviewed changes merge to `main` through pull requests.
- The web portal remains on its owner's branch and must not be included in Saleem's app/backend commits.
- Keep app, backend/AI and portal work in separate commits so the faculty can see each member's contribution.
- Assistant changes are never committed, pushed, merged or deployed automatically.
- Do not commit secrets, genuine patient information, generated builds, local databases, environments or dependency folders.
