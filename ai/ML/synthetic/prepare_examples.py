"""Prepare synthetic-only daily examples without using future uploads as features."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

FEATURES = ['scheduled_doses_14d', 'taken_reports_14d', 'skipped_reports_14d',
            'unconfirmed_doses_14d', 'taken_reports_3d', 'skipped_reports_3d',
            'unconfirmed_doses_3d']

def timestamp(value):
    return datetime.fromisoformat(value) if value else None

def status_at(event, cutoff):
    uploaded = timestamp(event['uploaded_at'])
    if uploaded is None or uploaded > cutoff:
        return 'not_confirmed'
    return event['eventual_report']

def history_features(events, cutoff):
    history = [e for e in events if cutoff-timedelta(days=14) <= timestamp(e['scheduled_at']) < cutoff]
    recent = [e for e in history if timestamp(e['scheduled_at']) >= cutoff-timedelta(days=3)]
    result = {'scheduled_doses_14d': len(history)}
    for suffix, rows in [('14d', history), ('3d', recent)]:
        counts = Counter(status_at(e, cutoff) for e in rows)
        result.update({f'taken_reports_{suffix}': counts['taken'],
                       f'skipped_reports_{suffix}': counts['skipped'],
                       f'unconfirmed_doses_{suffix}': counts['not_confirmed']})
    return result

def outcome(events, target_start):
    target_end = target_start + timedelta(days=1)
    deadline = target_end + timedelta(hours=48)
    target = [e for e in events if target_start <= timestamp(e['scheduled_at']) < target_end]
    statuses = [status_at(e, deadline) for e in target]
    if 'skipped' in statuses:
        return 'reported_skip', 1
    if statuses and all(s == 'taken' for s in statuses):
        return 'all_reported_taken', 0
    return 'unknown', ''

def build(source, output):
    if output.exists():
        raise SystemExit('Choose a new output directory; existing output will not be overwritten.')
    path = source/'dose_events_SYNTHETIC.csv'
    with path.open(encoding='utf-8-sig', newline='') as file:
        events = list(csv.DictReader(file))
    by_patient = defaultdict(list)
    ids = set()
    for event in events:
        if event['is_synthetic'] != 'True':
            raise ValueError('This builder only accepts the synthetic demo format.')
        if event['dose_id'] in ids:
            raise ValueError('Duplicate dose ID')
        ids.add(event['dose_id'])
        if event['eventual_report'] not in {'taken', 'skipped', 'not_confirmed'}:
            raise ValueError('Invalid status')
        due = timestamp(event['scheduled_at'])
        if due.tzinfo is None or due.utcoffset() != timedelta(0):
            raise ValueError('v1 requires UTC timestamps')
        by_patient[event['patient_id']].append(event)
    examples = []
    for patient, rows in sorted(by_patient.items()):
        splits = {e['split'] for e in rows}
        if len(splits) != 1 or not splits <= {'train', 'validation', 'test'}:
            raise ValueError('Invalid patient split')
        dates = {timestamp(e['scheduled_at']).date() for e in rows}
        first = min(timestamp(e['scheduled_at']) for e in rows).replace(hour=0, minute=0, second=0, microsecond=0)
        last = max(timestamp(e['scheduled_at']) for e in rows).replace(hour=0, minute=0, second=0, microsecond=0)
        if len(dates) != (last-first).days+1:
            raise ValueError('Missing schedule days; cannot assume a complete history')
        target = first+timedelta(days=14)
        while target <= last:
            label, y = outcome(rows, target)
            examples.append(dict(patient_id=patient, split=next(iter(splits)),
                prediction_cutoff=target.isoformat(), target_day=target.date().isoformat(),
                label_deadline=(target+timedelta(days=3)).isoformat(),
                **history_features(rows, target), outcome=label, target_reported_skip=y,
                eligible_for_training=(label!='unknown'), is_synthetic=True))
            target += timedelta(days=1)
    if not examples:
        raise ValueError('At least 15 consecutive days are needed')
    output.mkdir(parents=True)
    with (output/'daily_examples_SYNTHETIC.csv').open('w', encoding='utf-8', newline='') as file:
        writer=csv.DictWriter(file, fieldnames=list(examples[0]))
        writer.writeheader(); writer.writerows(examples)
    report = dict(is_synthetic=True, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        feature_allowlist=FEATURES, examples=len(examples),
        outcomes=dict(Counter(e['outcome'] for e in examples)),
        split_outcomes={s:dict(Counter(e['outcome'] for e in examples if e['split']==s))
                        for s in ['train','validation','test']},
        unknown_fraction=sum(e['outcome']=='unknown' for e in examples)/len(examples),
        observation_assumption='Completed synthetic simulation, observed through each label deadline; not for live extracts',
        warning='Synthetic-only pipeline demonstration; no model trained or real-world accuracy established')
    (output/'preparation_report.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output)
