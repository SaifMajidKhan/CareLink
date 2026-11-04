"""Opt-in HTTP smoke test against the locally running API and its Neon database."""
import argparse
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError

from .database import Audit, Connection, Record, SessionToken, User, database


def cleanup(factory, users, run_tag):
    """Delete this run's exact identities in one guarded, retryable transaction."""
    if not users:
        return
    for attempt in range(2):
        try:
            with factory() as session:
                for uid, email in users.items():
                    row = session.get(User, uid)
                    if row is not None and (row.email != email or not email.startswith(run_tag + '-')):
                        raise RuntimeError('Test cleanup identity check failed; no rows were deleted.')
                ids = list(users)
                session.execute(delete(Audit).where(Audit.actor.in_(ids)))
                session.execute(delete(Record).where(Record.owner.in_(ids)))
                session.execute(delete(Connection).where(
                    Connection.patient.in_(ids) | Connection.caregiver.in_(ids)))
                session.execute(delete(SessionToken).where(SessionToken.user_id.in_(ids)))
                session.execute(delete(User).where(User.id.in_(ids)))
                session.commit()
            print('PASS: removed only this run\'s fictional test accounts and records')
            return
        except OperationalError:
            if attempt:
                raise
            # A failed transaction rolls back; exact-ID cleanup is safe to retry.
            factory.kw['bind'].dispose()
            print('Retrying test cleanup after a database connection error.')


def run(base_url):
    factory = database()
    engine = factory.kw['bind']
    if engine.dialect.name != 'postgresql' or not (engine.url.host or '').endswith('.neon.tech'):
        engine.dispose()
        raise RuntimeError('This check requires the configured Neon PostgreSQL database.')
    run_tag = 'neon-smoke-' + uuid.uuid4().hex
    print('Fictional test run:', run_tag)
    users = {}
    client = httpx.Client(base_url=base_url, timeout=30)

    def call(method, path, expected=200, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code != expected:
            # Never print tokens, credentials or request/response bodies.
            raise RuntimeError(f'{method} {path.split("?")[0]} returned {response.status_code}, expected {expected}')
        return response.json()

    try:
        call('GET', '/health')
        headers = {}
        for role in ('patient', 'caregiver'):
            email = f'{run_tag}-{role}@example.test'
            credentials = {'email': email, 'password': secrets.token_urlsafe(24)}
            result = call('POST', '/auth/register', expected=201,
                          json=dict(credentials, name='Fictional Neon Check', role=role))
            users[result['user']['id']] = email
            signed_in = call('POST', '/auth/login', json=credentials)
            headers[role] = {'Authorization': 'Bearer ' + signed_in['token']}
        p, cg = headers['patient'], headers['caregiver']
        patient_id = next(uid for uid, email in users.items() if email.endswith('-patient@example.test'))
        print('PASS: patient and caregiver registration and sign-in through HTTP')

        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        schedule = call('POST', '/schedules', expected=201, headers=p, json={
            'name': 'Fictional Test Medicine', 'instructions': 'Fictional schedule for connection verification',
            'times': ['00:00'], 'start': today, 'timezone': 'UTC'})
        report = dict(request_id=uuid.uuid4().hex, schedule_id=schedule['id'], day=today,
                      time='00:00', outcome='taken', taken_at=(now-timedelta(seconds=30)).isoformat(),
                      recorded_at=now.isoformat())
        saved = call('POST', '/reports', headers=p, json=report)
        duplicate = call('POST', '/reports', headers=p, json=report)
        assert duplicate['id'] == saved['id'] and duplicate['version'] == 1
        dose_path = f'/patients/{patient_id}/doses?start={today}&end={today}'
        history = call('GET', dose_path, headers=p)
        assert len(history) == 1 and history[0]['status'] == 'taken'
        with factory() as session:
            row = session.get(Record, saved['id'])
            assert row is not None and row.owner == patient_id and row.kind == 'report'
        print('PASS: medicine schedule and dose report persisted in Neon; retry saved no duplicate')

        reading = call('POST', '/readings', expected=201, headers=p, json={
            'kind': 'blood_pressure', 'value': 120, 'secondary': 80, 'unit': 'mmHg',
            'measured_at': (now-timedelta(minutes=1)).isoformat()})
        rows = call('GET', f'/patients/{patient_id}/readings', headers=p)
        assert any(row['id'] == reading['id'] for row in rows)
        print('PASS: fictional BP reading saved and retrieved')

        relation = call('POST', '/connections', expected=201, headers=cg,
                        json={'patient_id': patient_id})
        call('GET', dose_path, expected=403, headers=cg)
        call('POST', f'/connections/{relation["id"]}', headers=p, json={'action': 'accept'})
        assert call('GET', dose_path, headers=cg)[0]['status'] == 'taken'
        call('POST', f'/connections/{relation["id"]}', headers=p, json={'action': 'remove'})
        call('GET', dose_path, expected=403, headers=cg)
        print('PASS: caregiver blocked before consent, allowed after approval, blocked after removal')
    finally:
        client.close()
        try:
            cleanup(factory, users, run_tag)
        finally:
            engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='http://127.0.0.1:8017')
    parser.add_argument('--allow-demo-writes', action='store_true')
    args = parser.parse_args()
    parsed = urlparse(args.api)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost'):
        parser.error('Run this check against a local API, with its Neon environment configured.')
    if not args.allow_demo_writes:
        parser.error('Pass --allow-demo-writes to create temporary fictional records and clean them up.')
    try:
        run(args.api.rstrip('/'))
    except Exception as error:
        # Database driver errors can contain sensitive connection context.
        original = getattr(error, 'orig', None)
        state = getattr(original, 'sqlstate', None)
        print(f'FAIL: {type(error).__name__}; SQLSTATE={state or "unavailable"}. No secrets printed.')
        raise SystemExit(1) from None
    print('Neon end-to-end verification passed.')


if __name__ == '__main__':
    main()
