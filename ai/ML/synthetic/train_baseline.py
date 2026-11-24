"""Train synthetic-only baselines; never fit or evaluate test rows."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss,
    confusion_matrix)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from prepare_examples import FEATURES


def load_development(path):
    groups = {'train': [], 'validation': []}
    patients = {}
    keys = set()
    unknown = dict.fromkeys(groups, 0)
    with path.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            pid, split = row['patient_id'], row['split']
            if split not in {'train', 'validation', 'test'}:
                raise ValueError('Invalid split')
            if pid in patients and patients[pid] != split:
                raise ValueError('Patient appears in multiple splits')
            patients[pid] = split
            if row['is_synthetic'] != 'True':
                raise ValueError('Synthetic-only experiment')
            # Test labels and features are deliberately not parsed.
            if split == 'test':
                continue
            key = (pid, row['target_day'])
            if key in keys:
                raise ValueError('Duplicate daily example')
            keys.add(key)
            if row['eligible_for_training'] == 'False':
                if row['target_reported_skip'] != '' or row['outcome'] != 'unknown':
                    raise ValueError('Unknown label inconsistency')
                unknown[split] += 1
                continue
            if row['eligible_for_training'] != 'True':
                raise ValueError('Invalid eligibility')
            y = int(row['target_reported_skip'])
            if y not in (0, 1) or row['outcome'] != ('reported_skip' if y else 'all_reported_taken'):
                raise ValueError('Outcome mismatch')
            x = [float(row[f]) for f in FEATURES]
            if not np.isfinite(x).all() or min(x) < 0:
                raise ValueError('Invalid feature values')
            groups[split].append((x, y))
    for split, rows in groups.items():
        if not rows or {y for _, y in rows} != {0, 1}:
            raise ValueError(f'{split} must contain both classes')
    return groups, unknown


def scores(y, probability, prediction):
    return dict(accuracy=accuracy_score(y,prediction),
        balanced_accuracy=balanced_accuracy_score(y,prediction),
        precision=precision_score(y,prediction,zero_division=0),
        recall=recall_score(y,prediction,zero_division=0),
        f1=f1_score(y,prediction,zero_division=0),
        roc_auc=roc_auc_score(y,probability),
        average_precision=average_precision_score(y,probability),
        brier_score=brier_score_loss(y,probability),
        confusion_matrix_rows_actual_0_1_columns_predicted_0_1=confusion_matrix(y,prediction,labels=[0,1]).tolist())


def train(source, output):
    if output.exists():
        raise SystemExit('Choose a new output folder; existing results are preserved.')
    groups, unknown = load_development(source)
    X, y = map(np.array, zip(*groups['train']))
    vx, vy = map(np.array, zip(*groups['validation']))
    # Fixed defaults chosen before looking at validation results. No tuning here.
    dummy = DummyClassifier(strategy='most_frequent').fit(X,y)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0,solver='lbfgs',max_iter=1000,random_state=42))
    model.fit(X,y)
    probability = model.predict_proba(vx)[:,1]
    metrics = dict(
        majority_baseline=scores(vy,dummy.predict_proba(vx)[:,1],dummy.predict(vx)),
        logistic_regression=scores(vy,probability,(probability>=0.5).astype(int)))
    report = dict(is_synthetic=True, evaluation_split='validation', test_evaluated=False,
        threshold=0.5, hyperparameter_search=False,
        training_rows=len(y), validation_rows=len(vy), excluded_unknown=unknown,
        training_positive_rate=float(y.mean()),validation_positive_rate=float(vy.mean()),
        feature_allowlist=FEATURES, metrics=metrics,
        versions=dict(python=platform.python_version(),scikit_learn=sklearn.__version__,numpy=np.__version__),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        limitations=['Invented data only; not medical or real-world validation',
        'Unknown days excluded; results concern resolved reports only',
        'Overlapping histories create correlated rows; no independent-row confidence intervals',
        'Patient-disjoint split but no later-calendar-period evaluation',
        'Probabilities are not clinically calibrated'])
    scaler, classifier = model.steps[0][1], model.steps[1][1]
    # Inspectable parameters instead of an executable pickle file.
    parameters = dict(is_synthetic=True, model='standardized_logistic_regression',
        feature_order=FEATURES, scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
        coefficients=classifier.coef_[0].tolist(), intercept=float(classifier.intercept_[0]),
        classes=classifier.classes_.tolist(), threshold=0.5,
        purpose='Demo only; not approved for app deployment')
    manual=1/(1+np.exp(-(((vx-scaler.mean_)/scaler.scale_)@classifier.coef_[0]+classifier.intercept_[0])))
    np.testing.assert_allclose(manual,probability,rtol=1e-10,atol=1e-12)
    output.mkdir(parents=True)
    for name, data in [('validation_report.json',report),('model_parameters_SYNTHETIC.json',parameters)]:
        (output/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    train(args.source,args.output)
