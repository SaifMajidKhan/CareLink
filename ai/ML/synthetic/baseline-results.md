# First synthetic baseline result

This experiment uses invented CareLink data only. It measures how well a model learns the simulator's behavior, not real diabetes or hypertension adherence. No app deployment or clinical accuracy is established.

## Fixed setup

- 4,842 eligible training examples and 1,081 eligible validation examples.
- Seven allowlisted history counts; StandardScaler fitted only on training data.
- Logistic regression: C=1, lbfgs, max_iter=1000, seed 42, threshold 0.5.
- No tuning performed. Test features and labels were not evaluated.
- Unknown days excluded: 1,542 training and 287 validation. This creates a selected population of resolved reports.
- Source CSV SHA256: 2a5654b2817bb47e953439141386de15858c2528adb3aa48e6ca3c0b61e45284.
- Python 3.12.14; exact dependencies in requirements-baseline.txt.

## Validation results

| Measure | Majority baseline | Logistic regression |
| --- | ---: | ---: |
| Accuracy | 66.60% | 71.32% |
| Reported-skip recall | 0% | 29.92% |
| Alert precision | 0 (no positive predictions) | 65.45% |
| Balanced accuracy | 50.00% | 61.00% |
| F1 | 0 | 0.4106 |
| ROC AUC | 0.5000 | 0.6891 |
| Average precision | 0.3340 | 0.5359 |
| Brier score (lower is better) | 0.3340 | 0.1988 |

Logistic regression caught 108 of 361 reported-skip days, missed 253, raised 57 false alerts and correctly classified 663 all-reported-taken days. It improves accuracy by 4.72 percentage points but misses about seven in ten positive days at this threshold. The majority baseline never predicts a skip. Its zero precision is a reporting convention, not a meaningful alert rate.

These are day-level metrics from repeated, overlapping histories. They are not independent patient observations, and no independent-row confidence intervals are claimed. This split separates patients but does not establish generalization to a later calendar period. No feature importance or clinical interpretation should be inferred from the correlated counts.

## Verification and outputs

All five preparation boundary tests and three training input tests passed. Training tests check test-value exclusion, patient split overlap and unknown exclusion. Exported JSON model parameters reproduce the pipeline probabilities to numerical tolerance.

The local output directory is C:/CareLink-FYP/Datasets/CareLink-Synthetic-v1-baseline. It contains validation_report.json and model_parameters_SYNTHETIC.json. The isolated environment is outside Git. Source files and downloaded datasets are unchanged.

## Next step

Review the tradeoff between catching more reported skips and raising more false alerts. Any threshold comparison must use validation data only. Fix the choice before a single final test evaluation. Retain this first result as the baseline, even if later experiments improve it. Real-world evaluation still requires appropriate real data.
