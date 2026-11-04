# Save the patient UI and account checkpoint

The patient-app and matching backend authentication work are saved as separate
checkpoints on `saleem`, at the user's request. The app checkpoint includes the
UI redesign and earlier guest/account improvements. Provider credentials and
real sign-in testing remain separate setup steps. The portal and unrelated
planning work are outside these checkpoints.

The commands below record the checkpoint workflow. Check `git status` before
using them again; already committed files do not need another commit.

## 1. Patient app

```powershell
Set-Location C:\CareLink-Repo
if ((git branch --show-current) -ne 'saleem') { throw 'Switch to saleem before committing.' }

git add Docs/design/colour-scheme.md `
  Docs/implementation/patient-ui-redesign.md `
  apps/patient_app/README.md `
  apps/patient_app/android/app/src/main/AndroidManifest.xml `
  apps/patient_app/assets/auth/ `
  apps/patient_app/lib/connected/ `
  apps/patient_app/lib/core/theme/app_theme.dart `
  apps/patient_app/pubspec.yaml `
  apps/patient_app/pubspec.lock `
  apps/patient_app/test/auth_flow_test.dart `
  apps/patient_app/test/auth_validation_test.dart `
  apps/patient_app/test/social_sign_in_test.dart `
  apps/patient_app/test/connected_logout_test.dart `
  apps/patient_app/test/fake_connected_store.dart `
  apps/patient_app/test/presentation_test.dart `
  apps/patient_app/test/signed_in_design_test.dart `
  apps/patient_app/test/connected_forms_test.dart `
  apps/patient_app/test/widget_test.dart

git diff --staged --stat
git diff --staged --check
git commit -m "feat: redesign patient screens and improve account flows"
```

Review the staged list before committing. It should contain patient-app files
and their design notes.
The offline sign-out fix, shared theme, new patient views and form regression
tests are included in this app checkpoint. Guest/account work and the UI redesign
were saved together because both sets of app changes were waiting to be committed.

## 2. Backend authentication and documentation

```powershell
git add backend/.env.example `
  backend/README.md `
  backend/app/database.py `
  backend/app/main.py `
  backend/app/schemas.py `
  backend/app/social_auth.py `
  backend/requirements.txt `
  backend/tests/test_social_auth.py `
  render.yaml `
  README.md `
  Docs/implementation/deploy-render.md `
  Docs/implementation/account-and-social-sign-in.md `
  Docs/implementation/account-checkpoint.md

git diff --staged --stat
git diff --staged --check
git commit -m "feat: prepare verified Google and Facebook sign-in"
git push origin saleem
```

The root README records the patient-app checkpoint and pending backend work.
Review the backend diff before creating the separate commit. Never add `.env.local`,
database files, provider secrets or the APK to either commit.

Render can redeploy the backend from `saleem`. After that, follow the
[provider setup guide](account-and-social-sign-in.md) to add the developer
credentials privately. Test registration and the real provider flows before
merging the reviewed changes into `main`. Keep `saleem` for future development.
