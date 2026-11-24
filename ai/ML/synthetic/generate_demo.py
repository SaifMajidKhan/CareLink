"""Generate fictional CareLink workflow data. Not clinical training evidence."""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = '1.0'

def generate(output, seed=42):
    if output.exists():
        raise SystemExit('Output already exists; choose a new folder to preserve originals.')
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    patients, events, truth = [], [], []
    splits = ['train'] * 84 + ['validation'] * 18 + ['test'] * 18
    rng.shuffle(splits)
    for n in range(120):
        pid = f'SYN-{n+1:04d}'
        split = splits[n]
        condition = ['hypertension', 'type_2_diabetes', 'both'][n % 3]
        doses = rng.choice([1, 2])
        patients.append(dict(patient_id=pid, condition_demo=condition,
                             scheduled_doses_per_day=doses, split=split, is_synthetic=True))
        # Arbitrary simulator assumptions, not estimated from real patients.
        base = rng.uniform(.60, .97)
        report_probability = rng.uniform(.70, .98)
        previous_missed = False
        disruption_start = rng.randrange(10, 70)
        disruption_length = rng.randrange(3, 12)
        for day in range(90):
            disrupted = disruption_start <= day < disruption_start + disruption_length
            for slot in range(doses):
                due = start + timedelta(days=day, hours=8 + slot * 12)
                probability = max(.1, base - .2 * disrupted - .08 * previous_missed)
                taken = rng.random() < probability
                previous_missed = not taken
                actual = due + timedelta(minutes=rng.choice([0, 5, 15, 40, 90])) if taken else None
                reported = rng.random() < report_probability
                report = ('taken' if taken else 'skipped') if reported else 'not_confirmed'
                recorded = (actual or due) + timedelta(minutes=rng.choice([0, 5, 30, 120, 1440])) if reported else None
                uploaded = recorded + timedelta(minutes=rng.choice([0, 0, 0, 15, 120, 1440, 2880])) if reported else None
                eid = f'{pid}-D{day+1:03d}-S{slot+1}'
                stamp = lambda value: value.isoformat() if value else ''
                events.append(dict(dose_id=eid, patient_id=pid, day_index=day+1,
                    medication_demo_id=f'DEMO-MED-{slot+1}', scheduled_at=stamp(due),
                    eventual_report=report, reported_taken_at=stamp(actual) if report=='taken' else '',
                    recorded_at=stamp(recorded), uploaded_at=stamp(uploaded),
                    split=split, is_synthetic=True))
                truth.append(dict(dose_id=eid, simulator_actual_taken=taken,
                                  simulator_actual_taken_at=stamp(actual), is_synthetic=True))
    # Validate relationships before writing any files.
    ids = {p['patient_id'] for p in patients}
    assert len(ids) == 120 and len({e['dose_id'] for e in events}) == len(events)
    assert all(e['patient_id'] in ids for e in events)
    assert all(len({e['day_index'] for e in events if e['patient_id']==pid}) == 90 for pid in ids)
    assert all(not e['uploaded_at'] or e['recorded_at'] <= e['uploaded_at'] for e in events)
    assert all(e['eventual_report'] != 'not_confirmed' or not e['recorded_at'] for e in events)
    assert all(e['eventual_report'] != 'taken' or e['reported_taken_at'] <= e['recorded_at'] for e in events)
    assert {e['eventual_report'] for e in events} == {'taken', 'skipped', 'not_confirmed'}
    output.mkdir(parents=True)
    hashes = {}
    for name, rows in [('patients_SYNTHETIC.csv', patients), ('dose_events_SYNTHETIC.csv', events),
                       ('simulator_truth_DO_NOT_USE_AS_FEATURES.csv', truth)]:
        path = output / name
        with path.open('w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = dict(generator_version=VERSION, seed=seed, is_synthetic=True,
        purpose='Workflow and ML pipeline demonstration only; no real-world validation',
        patients=len(patients), days_per_patient=90, dose_events=len(events),
        patient_split_counts=dict(Counter(p['split'] for p in patients)),
        eventual_report_counts=dict(Counter(e['eventual_report'] for e in events)),
        sha256=hashes)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    generate(args.output, args.seed)
