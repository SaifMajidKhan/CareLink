"""CareLink teaching MVP API. No treatment decisions or clinical ML claims."""
import json, os, secrets, uuid
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from .database import database, User, SessionToken, Connection, Record, Audit
from .schemas import (Registration, Credentials, Profile, Schedule, StopSchedule,
                      DoseReport, Reading, RequestConnection, Decision, Note, AccountStatus, Assignment)
from .security import password_hash, verify_password, digest, RateLimit
from .social_auth import register_social_routes
from .native_auth import register_native_routes

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def public(user): return {k: getattr(user, k) for k in ('id', 'name', 'role', 'condition')}
def unpack(record): return dict(json.loads(record.body), id=record.id, version=record.version, received_at=record.created)

def create_app(url=None):
    app = FastAPI(title='CareLink', version='0.2.0')
    sessions = database(url)
    app.state.sessions = sessions
    limiter = RateLimit()
    app.add_middleware(CORSMiddleware,
        allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:4200').split(','),
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])

    def db():
        with sessions() as session:
            yield session

    def user(authorization: str = Header(default=''), s=Depends(db)):
        token = authorization.removeprefix('Bearer ')
        row = s.get(SessionToken, digest(token))
        if not row or row.expires < now(): raise HTTPException(401, 'Please sign in again')
        result = s.get(User, row.user_id)
        if not result or not result.enabled: raise HTTPException(401, 'Account unavailable')
        return result

    def patient(u=Depends(user)):
        if u.role != 'patient': raise HTTPException(403, 'Only patients can change their records')
        return u

    def admin(u=Depends(user)):
        if u.role != 'admin': raise HTTPException(403, 'Administrator required')
        return u

    def audit(s, u, action, target, previous=''):
        s.add(Audit(id=uid(), actor=u.id, action=action, target=target, at=now(), previous=previous))

    def connection_access(s, u, patient_id):
        if u.id == patient_id and u.role == 'patient': return None
        row = s.scalar(select(Connection).where(Connection.patient == patient_id,
                Connection.caregiver == u.id, Connection.state == 'active'))
        if not row: raise HTTPException(403, 'No active patient-approved connection')
        return row

    def login_result(s, u):
        token = secrets.token_urlsafe(40)
        s.add(SessionToken(digest=digest(token), user_id=u.id,
            expires=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()))
        s.commit()
        return {'token': token, 'user': public(u)}

    register_social_routes(app, sessions, limiter, login_result)
    register_native_routes(app, sessions, limiter, login_result)

    @app.get('/health')
    def health(): return {'status': 'ok', 'mode': 'FYP demonstration; fictional data only'}

    @app.get('/research/synthetic-example')
    def synthetic_example(u=Depends(user)):
        if u.role not in ('caregiver','coordinator','admin'): raise HTTPException(403,'Portal account required')
        from .research import example_prediction
        return example_prediction()

    @app.post('/auth/register', status_code=201)
    def register(data: Registration, request: Request, s=Depends(db)):
        limiter.check(('register', request.client.host), 10)
        u = User(id='CL-' + secrets.token_hex(8).upper(), email=data.email,
                 password=password_hash(data.password), name=data.name, role=data.role)
        s.add(u)
        try: s.commit()
        except IntegrityError:
            s.rollback()
            raise HTTPException(409, 'Unable to register that email. Try signing in.')
        return login_result(s, u)

    @app.post('/auth/login')
    def login(data: Credentials, request: Request, s=Depends(db)):
        limiter.check(('login', request.client.host), 30)
        u = s.scalar(select(User).where(User.email == data.email))
        if not u or not u.enabled or not verify_password(data.password, u.password):
            raise HTTPException(401, 'Email or password is incorrect')
        return login_result(s, u)

    @app.post('/auth/logout')
    def logout(authorization: str = Header(), u=Depends(user), s=Depends(db)):
        row = s.get(SessionToken, digest(authorization.removeprefix('Bearer ')))
        if row: s.delete(row)
        s.commit()
        return {'signed_out': True}

    @app.get('/me')
    def me(u=Depends(user)): return public(u)

    @app.put('/me')
    def update_profile(data: Profile, u=Depends(user), s=Depends(db)):
        if not data.name.strip(): raise HTTPException(422, 'Name required')
        audit(s, u, 'profile.update', u.id)
        u.name, u.condition = data.name.strip(), data.condition
        s.commit()
        return public(u)

    @app.get('/patients/{patient_id}/schedules')
    def schedules(patient_id: str, u=Depends(user), s=Depends(db)):
        connection_access(s, u, patient_id)
        return [unpack(r) for r in s.scalars(select(Record).where(Record.owner == patient_id, Record.kind == 'schedule'))]

    @app.post('/schedules', status_code=201)
    def add_schedule(data: Schedule, u=Depends(patient), s=Depends(db)):
        today = datetime.now(ZoneInfo(data.timezone)).date()
        if data.start < today: raise HTTPException(422, 'New schedules start today or later')
        key = uid()
        row = Record(id=key, owner=u.id, kind='schedule', key=key,
                     body=data.model_dump_json(), created=now())
        s.add(row); audit(s, u, 'schedule.create', key); s.commit()
        return unpack(row)

    @app.post('/schedules/{schedule_id}/stop')
    def stop_schedule(schedule_id: str, data: StopSchedule, u=Depends(patient), s=Depends(db)):
        row = s.get(Record, schedule_id)
        if not row or row.owner != u.id or row.kind != 'schedule': raise HTTPException(404, 'Schedule not found')
        body = json.loads(row.body)
        today = datetime.now(ZoneInfo(body['timezone'])).date()
        if data.end < today or data.end < date.fromisoformat(body['start']): raise HTTPException(422, 'Cannot change historical schedule days')
        if body.get('end') and data.end.isoformat() > body['end']: raise HTTPException(409, 'Create a new schedule to extend it')
        audit(s, u, 'schedule.stop', row.id, row.body)
        body['end'] = data.end.isoformat(); row.body = json.dumps(body); row.version += 1
        s.commit(); return unpack(row)

    @app.get('/patients/{patient_id}/doses')
    def doses(patient_id: str, start: date, end: date, u=Depends(user), s=Depends(db)):
        connection_access(s, u, patient_id)
        if end < start or (end-start).days > 90: raise HTTPException(422, 'Choose at most 90 days')
        schedules = s.scalars(select(Record).where(Record.owner == patient_id, Record.kind == 'schedule')).all()
        reports = {r.key: unpack(r) for r in s.scalars(select(Record).where(Record.owner == patient_id, Record.kind == 'report'))}
        result = []
        for row in schedules:
            schedule = json.loads(row.body)
            day = max(start, date.fromisoformat(schedule['start']))
            finish = min(end, date.fromisoformat(schedule['end'])) if schedule.get('end') else end
            while day <= finish:
                for clock in schedule['times']:
                    key = f'{row.id}|{day}|{clock}'
                    at = datetime.fromisoformat(f'{day}T{clock}').replace(tzinfo=ZoneInfo(schedule['timezone']))
                    report = reports.get(key)
                    result.append({'key': key, 'schedule_id': row.id, 'day': str(day), 'time': clock,
                        'name': schedule['name'], 'instructions': schedule['instructions'], 'timezone': schedule['timezone'],
                        'scheduled_at': at.isoformat(), 'report': report,
                        'status': report['outcome'] if report else ('upcoming' if at > datetime.now(timezone.utc) else 'not_confirmed')})
                day += timedelta(days=1)
        return sorted(result, key=lambda d: datetime.fromisoformat(d['scheduled_at']))

    @app.post('/reports')
    def save_report(data: DoseReport, u=Depends(patient), s=Depends(db)):
        schedule_row = s.get(Record, data.schedule_id)
        if not schedule_row or schedule_row.owner != u.id or schedule_row.kind != 'schedule': raise HTTPException(404, 'Schedule not found')
        schedule = json.loads(schedule_row.body)
        if str(data.day) < schedule['start'] or (schedule.get('end') and str(data.day) > schedule['end']) or data.time not in schedule['times']:
            raise HTTPException(422, 'Dose is outside this schedule')
        if data.day > datetime.now(ZoneInfo(schedule['timezone'])).date(): raise HTTPException(422, 'Cannot report a future day')
        key = f'{data.schedule_id}|{data.day}|{data.time}'
        row = s.scalar(select(Record).where(Record.owner == u.id, Record.kind == 'report', Record.key == key).with_for_update())
        if row and json.loads(row.body)['request_id'] == data.request_id:
            old = json.loads(row.body)
            if any(old.get(k) != v for k,v in data.model_dump(mode='json').items()): raise HTTPException(409, 'Request ID was reused with different content')
            return unpack(row)
        if (row.version if row else 0) != data.expected_version: raise HTTPException(409, 'Report changed on another device. Refresh and review before correcting.')
        if row:
            audit(s, u, 'report.correct', row.id, row.body)
            row.body = data.model_dump_json(); row.version += 1; row.created = now()
        else:
            row = Record(id=uid(), owner=u.id, kind='report', key=key, body=data.model_dump_json(), created=now())
            s.add(row); audit(s, u, 'report.create', row.id)
        try: s.commit()
        except IntegrityError:
            s.rollback(); raise HTTPException(409, 'Another report was saved. Refresh and review.')
        return unpack(row)

    @app.get('/patients/{patient_id}/readings')
    def readings(patient_id: str, u=Depends(user), s=Depends(db)):
        connection_access(s, u, patient_id)
        return [unpack(r) for r in s.scalars(select(Record).where(Record.owner == patient_id, Record.kind == 'reading').order_by(Record.created.desc()))]

    @app.post('/readings', status_code=201)
    def add_reading(data: Reading, u=Depends(patient), s=Depends(db)):
        key = uid(); row = Record(id=key, owner=u.id, kind='reading', key=key, body=data.model_dump_json(), created=now())
        s.add(row); audit(s,u,'reading.create', key); s.commit(); return unpack(row)

    @app.get('/connections')
    def connections(u=Depends(user), s=Depends(db)):
        rows = s.scalars(select(Connection).where(or_(Connection.patient == u.id, Connection.caregiver == u.id))).all()
        return [dict(id=r.id, patient=r.patient, caregiver=r.caregiver, state=r.state,
                     patient_name=s.get(User,r.patient).name, caregiver_name=s.get(User,r.caregiver).name,
                     caregiver_role=s.get(User,r.caregiver).role) for r in rows]

    @app.post('/connections', status_code=201)
    def request_connection(data: RequestConnection, u=Depends(user), s=Depends(db)):
        if u.role != 'caregiver': raise HTTPException(403, 'Caregiver account required')
        limiter.check(('connection', u.id), 10)
        p = s.get(User, data.patient_id.removeprefix('carelink:patient:'))
        if not p or p.role != 'patient': raise HTTPException(404, 'Patient ID not found')
        existing = s.scalar(select(Connection).where(Connection.patient==p.id, Connection.caregiver==u.id, Connection.state.in_(['pending','active'])))
        if existing: raise HTTPException(409, 'A request or connection already exists')
        row=Connection(id=uid(),patient=p.id,caregiver=u.id,state='pending',created=now())
        s.add(row); audit(s,u,'connection.request',row.id); s.commit()
        return {'id':row.id,'state':row.state}

    @app.post('/connections/{connection_id}')
    def decide(connection_id: str, data: Decision, u=Depends(user), s=Depends(db)):
        row=s.get(Connection,connection_id)
        if not row or u.id not in (row.patient,row.caregiver): raise HTTPException(404,'Connection not found')
        if data.action in ('accept','decline'):
            if u.id != row.patient or row.state != 'pending': raise HTTPException(409,'Only the patient can decide a pending request')
            row.state='active' if data.action=='accept' else 'declined'
        else:
            required = row.patient if data.action=='remove' else row.caregiver
            if u.id != required or row.state != 'active': raise HTTPException(403,'Cannot perform this action')
            row.state='removed'
        audit(s,u,'connection.'+data.action,row.id); s.commit(); return {'state':row.state}

    @app.get('/connections/{connection_id}/notes')
    def notes(connection_id: str, u=Depends(user), s=Depends(db)):
        row=s.get(Connection,connection_id)
        if not row or row.state!='active' or u.id not in (row.patient,row.caregiver): raise HTTPException(403,'No active connection')
        return [unpack(r) for r in s.scalars(select(Record).where(Record.owner==row.patient,Record.kind=='note',Record.key.like(connection_id+'|%')).order_by(Record.created.desc()))]

    @app.post('/connections/{connection_id}/notes', status_code=201)
    def add_note(connection_id: str, data: Note, u=Depends(user), s=Depends(db)):
        row=s.get(Connection,connection_id)
        if not row or row.state!='active' or u.id!=row.caregiver: raise HTTPException(403,'Only this connected caregiver can add a note')
        if not data.text.strip(): raise HTTPException(422,'Note required')
        key=uid(); note=Record(id=key,owner=row.patient,kind='note',key=connection_id+'|'+key,
            body=json.dumps({'text':data.text.strip(),'author':u.name,'connection_id':connection_id}),created=now())
        s.add(note); audit(s,u,'note.create',key); s.commit(); return unpack(note)

    @app.get('/patients/{patient_id}/summary')
    def summary(patient_id: str, start: date, end: date, u=Depends(user), s=Depends(db)):
        rows = doses(patient_id,start,end,u,s)
        elapsed = [d for d in rows if datetime.fromisoformat(d['scheduled_at']) <= datetime.now(timezone.utc)]
        counts = {status: sum(d['status']==status for d in elapsed) for status in ('taken','skipped','not_confirmed')}
        return dict(counts, expected=len(elapsed), reporting_coverage=(counts['taken']+counts['skipped'])/len(elapsed) if elapsed else None,
                    received_at=now(), ml={'status':'not_deployed','reason':'Synthetic experiment only; no clinical prediction'},
                    definition='Elapsed scheduled doses only. No response is not a skipped dose.')

    @app.get('/patients/{patient_id}/profile')
    def shared_profile(patient_id: str, u=Depends(user), s=Depends(db)):
        connection_access(s,u,patient_id)
        p=s.get(User,patient_id)
        if not p: raise HTTPException(404,'Patient not found')
        return public(p)

    @app.get('/admin/accounts')
    def accounts(u=Depends(admin),s=Depends(db)):
        # Administrators see account metadata, never patients' health records here.
        return [dict(id=r.id,name=r.name,role=r.role,enabled=bool(r.enabled)) for r in s.scalars(select(User))]

    @app.put('/admin/accounts/{account_id}')
    def status(account_id: str,data: AccountStatus,u=Depends(admin),s=Depends(db)):
        row=s.get(User,account_id)
        if not row: raise HTTPException(404,'Account not found')
        if row.id==u.id: raise HTTPException(409,'Cannot disable your own administrator account')
        row.enabled=int(data.enabled);audit(s,u,'account.status',row.id);s.commit()
        return {'enabled':bool(row.enabled)}

    @app.post('/admin/assignments',status_code=201)
    def assign(data: Assignment,u=Depends(admin),s=Depends(db)):
        p=s.get(User,data.patient_id);co=s.get(User,data.coordinator_id)
        if not p or p.role!='patient' or not co or co.role!='coordinator': raise HTTPException(422,'Choose a patient and a coordinator')
        old=s.scalar(select(Connection).where(Connection.patient==p.id,Connection.caregiver==co.id,Connection.state.in_(['active','pending'])))
        if old: raise HTTPException(409,'Assignment already exists')
        row=Connection(id=uid(),patient=p.id,caregiver=co.id,state='pending',created=now())
        s.add(row);audit(s,u,'coordinator.assign.pending',row.id);s.commit()
        return {'id':row.id,'state':'pending','message':'Patient approval is required'}

    @app.get('/admin/activity')
    def activity(u=Depends(admin),s=Depends(db)):
        # Correction bodies may contain health information; never expose them to admins.
        return [dict(id=r.id,actor=r.actor,action=r.action,target=r.target,at=r.at)
                for r in s.scalars(select(Audit).order_by(Audit.at.desc()).limit(100))]

    @app.get('/connections/{connection_id}/alerts')
    def alerts(connection_id: str,u=Depends(user),s=Depends(db)):
        relation=s.get(Connection,connection_id)
        if not relation or relation.state!='active' or u.id not in (relation.patient,relation.caregiver): raise HTTPException(403,'No active connection')
        # One deterministic review item per explicit skipped report. No inferred skips or ML alarms.
        reports=s.scalars(select(Record).where(Record.owner==relation.patient,Record.kind=='report')).all()
        acknowledged={r.key for r in s.scalars(select(Record).where(Record.owner==u.id,Record.kind=='ack'))}
        result=[]
        for r in reports:
            body=json.loads(r.body)
            if body['outcome']=='skipped':
                key=f'{connection_id}|{r.id}|{r.version}'
                result.append({'id':key,'day':body['day'],'message':'Patient reported a skipped dose. Review the record; do not infer treatment changes.',
                               'acknowledged':key in acknowledged,'report_id':r.id})
        return result

    @app.post('/connections/{connection_id}/alerts/{report_id}/ack')
    def acknowledge(connection_id: str,report_id: str,u=Depends(user),s=Depends(db)):
        relation=s.get(Connection,connection_id)
        if not relation or relation.state!='active' or u.id!=relation.caregiver: raise HTTPException(403,'Active caregiver or coordinator required')
        report=s.get(Record,report_id)
        if not report or report.kind!='report' or report.owner!=relation.patient: raise HTTPException(404,'Report not found')
        key=f'{connection_id}|{report.id}|{report.version}'
        old=s.scalar(select(Record).where(Record.owner==u.id,Record.kind=='ack',Record.key==key))
        if not old:
            s.add(Record(id=uid(),owner=u.id,kind='ack',key=key,body='{}',created=now()))
            audit(s,u,'alert.acknowledge',key);s.commit()
        return {'acknowledged':True}

    return app

app = create_app()
