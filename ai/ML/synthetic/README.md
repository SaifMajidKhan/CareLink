# CareLink synthetic demo dataset v1

This generator creates fictional software-test data, not observations of real patients. No downloaded patient data was used to generate it. It is not clinically calibrated, representative of Pakistan, or evidence of predictive accuracy for diabetes or hypertension. The condition labels are demo tags and do not change behavior probabilities.

## Generate

Python standard library only. From the repository root:

```powershell
python ML/synthetic/generate_demo.py --output C:/CareLink-FYP/Datasets/CareLink-Synthetic-v1
```

An existing output folder is refused. Use a new folder to rerun. Default seed 42 reproduces the same CSVs. Commit this generator and documentation; generated data can be recreated.

## Files and meanings

- `patients_SYNTHETIC.csv`: 120 fictional people, a demo condition tag, one or two scheduled doses daily, patient-level train/validation/test assignment (84/18/18), and synthetic flag.
- `dose_events_SYNTHETIC.csv`: 90 consecutive days per person. Unique dose ID, patient ID, day index, fictional medication ID, scheduled UTC time, eventual self-report, reported taken time, time entered locally, server upload time, split and synthetic flag. There are no medicine names or clinical doses.
- `simulator_truth_DO_NOT_USE_AS_FEATURES.csv`: hidden simulator behavior for testing the difference between ingestion and reporting. Keep out of model features and app-visible records. This is invented truth, not measured truth.
- `manifest.json`: seed, version, counts and SHA256 checksums.

`eventual_report` is taken, skipped or not_confirmed. It describes the completed simulation and is NOT necessarily available at prediction time. A missing report never implies that medicine was not taken. All records have `is_synthetic=True`.

## Assumptions

All probabilities are arbitrary demo settings. Each person's baseline taking probability is uniform 0.60-0.97; reporting probability is independently uniform 0.70-0.98. A fictional disruption lasts 3-11 days and reduces taking probability by 0.20. A previous missed simulated dose reduces the next probability by 0.08. Simulated report delays and upload delays are sampled from explicit minute lists in the code. These rules create variation to exercise the pipeline, not a discovered medical relationship. No disease-specific risk factors, prescriptions or severity effects are asserted.

Limitations include fixed schedules, no medication changes, no corrections, no time-zone travel, and simplified reporting errors/connectivity. Add these as separately versioned test scenarios later if needed.

## Prevent future information entering a model

At a prediction cutoff T, the server can use an event report only if uploaded_at <= T. If it has not arrived, its eventual_report and reported_taken_at must be hidden. The phone can see locally recorded reports sooner; decide which prediction environment is being evaluated.

Build history features only from prior scheduled doses whose reports were available then. Never use future outcomes, simulator truth, patient IDs, split labels or condition demo tags as predictive features. Keep patients in their assigned split. Fit preprocessing only on training data and test on later prediction dates as well.

The accepted exercise predicts at least one reported skipped dose on the next day, using 14 complete prior days. The prediction cutoff is midnight UTC starting the target day (the boundary at the end of the previous day). Labels allow 48 hours after the target day ends. A late upload cannot be used retrospectively as an earlier feature.

The data-preparation increment did not train a model. The subsequent baseline experiment is documented in baseline-results.md. Any eventual metrics must be labeled synthetic-only: a model can learn our invented rules and still fail on real patients. Do not present synthetic test accuracy as real-world accuracy. App demonstrations must say Demo prediction.

## Checks

The generator checks unique IDs, valid patient links, 90-day coverage, valid timestamp ordering, empty timestamps for unreported events, and all three report states. Repeated runs with seed 42 were compared for identical CSV hashes. Original research downloads are unchanged.

## Prepare daily examples

```powershell
python -B ML/synthetic/test_prepare_examples.py
python -B ML/synthetic/prepare_examples.py --source C:/CareLink-FYP/Datasets/CareLink-Synthetic-v1 --output C:/CareLink-FYP/Datasets/CareLink-Synthetic-v1-examples
```

Both source and output folders are outside the Git repository. The builder refuses an existing output folder. It reads only dose_events_SYNTHETIC.csv, never simulator truth. The source SHA256 is recorded in the preparation report.

One row represents one patient and target day. For example, January 15 uses scheduled doses from January 1 at 00:00 through January 15 at 00:00 exclusive. Only reports uploaded by January 15 at 00:00 are visible as features. The label covers January 15 doses and accepts uploads through January 18 at 00:00 inclusive (48 hours after January 15 ends). UTC is a demo convention; production must use the patient's schedule timezone.

The seven allowed features count scheduled doses across 14 days and taken/skipped/unconfirmed reports across 14 and 3 days. All counts reflect what the server knew at the prediction cutoff. This v1 assumes fixed schedules known beforehand; it is not suitable for live extracts or changing prescriptions without additional schedule/version and observation-end metadata.

Outcome rules:
- At least one target-day dose reported skipped by the deadline: reported_skip, target 1, eligible.
- Every scheduled target-day dose reported taken by the deadline: all_reported_taken, target 0, eligible.
- Otherwise: unknown, blank target, ineligible. No report does not mean skipped.

Unknown rows stay in the output for auditing. Filter eligible_for_training before fitting. Use only the feature_allowlist from preparation_report.json as model inputs. Patient IDs, cutoff timestamps, split, outcome, deadline, eligibility, synthetic flag and target are metadata/labels, not model features. No target-day count or retrospective label information enters the features.

The completed simulation is assumed observed through every label deadline. Real extracts must additionally exclude outcomes whose observation deadline has not yet elapsed. Choosing resolved days can introduce selection bias; always report the unknown rate, including by split.

Verified output: 9,120 examples, 4,555 all_reported_taken, 2,493 reported_skip and 2,072 unknown (22.72%). Eligible total: 7,048. Training has 4,842 eligible examples, validation 1,081 and test 1,125, with patient assignments preserved. Test examples must remain unused for model selection. The current split separates patients but not calendar periods; a later-time evaluation is still needed before any temporal generalization claim.

Five boundary tests passed: future upload masking, history-window boundaries, unknown handling, label-deadline boundaries, and positive-label precedence/target-day boundaries. For the subsequent validation-only model results, see baseline-results.md.

## First baseline experiment

`train_baseline.py` fits two models on the eligible training patients only:

- Majority baseline: always predicts the most frequent training outcome.
- Logistic regression: StandardScaler followed by regularized logistic regression (C=1, lbfgs, max_iter=1000). Scaling is fitted on training data only. The threshold is fixed at 0.5 before validation; no parameter search is performed.

Only the seven FEATURES in prepare_examples.py enter the model. Unknown outcomes are excluded and counted. Test rows are skipped before their feature values or labels are parsed; patient IDs and split metadata are checked across all rows to reject overlap. The source file is hashed for provenance. Validation rows are evaluated; test performance remains unmeasured.

Accuracy counts all correct predictions. Recall measures how many reported-skip days were caught. Precision measures how many alerts correspond to reported-skip days. A model predicting no skips can have reasonable accuracy but zero recall. The report also includes the confusion matrix, balanced accuracy, F1, ROC AUC, average precision and Brier score. Probabilities concern resolved synthetic reports, not actual ingestion or clinically calibrated risk.

The model parameters are saved as inspectable JSON, not an executable pickle. The script checks that these parameters reproduce validation probabilities. This artifact is for learning, not app deployment. Overlapping daily histories produce correlated observations, so we do not claim confidence intervals based on independent rows.

An isolated Python environment is located at C:/CareLink-FYP/ML-Environments/baseline. It is outside Git. From the repository root, use its interpreter:

```powershell
$mlPython = 'C:\CareLink-FYP\ML-Environments\baseline\Scripts\python.exe'
& $mlPython -B ML/synthetic/test_train_baseline.py
& $mlPython -B ML/synthetic/train_baseline.py --source C:/CareLink-FYP/Datasets/CareLink-Synthetic-v1-examples/daily_examples_SYNTHETIC.csv --output C:/CareLink-FYP/Datasets/CareLink-Synthetic-v1-baseline
```

The output directory must not already exist. Preserve earlier results and select a new name for a new experiment. No Git commit or push is performed by the scripts.

The completed baseline run and limitations are recorded in [baseline-results.md](baseline-results.md). To recreate dependencies in your own isolated Python 3.12 environment, run `python -m pip install -r ML/synthetic/requirements-baseline.txt`.
