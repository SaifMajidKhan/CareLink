from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import create_app

def setup(tmp_path):
    return TestClient(create_app('sqlite:///' + str(tmp_path / 'test.db')))

def register(c, email, role='patient'):
    r=c.post('/auth/register',json={'email':email,'password':'A-test-password-123','name':email.split('@')[0],'role':role})
    assert r.status_code==201,r.text
    data=r.json()
    return {'Authorization':'Bearer '+data['token']},data['user']['id']

def schedule(c,h):
    today=datetime.now(timezone.utc).date().isoformat()
    r=c.post('/schedules',headers=h,json={'name':'Demo A','instructions':'1 demo tablet','times':['08:00','20:00'],'start':today,'timezone':'UTC'})
    assert r.status_code==201,r.text
    return r.json(),today

def connection(c,p,cg,pid):
    r=c.post('/connections',headers=cg,json={'patient_id':pid})
    assert r.status_code==201,r.text
    cid=r.json()['id']
    assert c.post('/connections/'+cid,headers=p,json={'action':'accept'}).status_code==200
    return cid

def report(sid,today):
    t=datetime.now(timezone.utc).isoformat()
    return dict(request_id='request-00001',schedule_id=sid,day=today,time='08:00',outcome='taken',taken_at=t,recorded_at=t)

def test_full_consent_reporting_and_revocation(tmp_path):
    c=setup(tmp_path)
    p,pid=register(c,'patient@example.test')
    cg,_=register(c,'caregiver@example.test','caregiver')
    stranger,_=register(c,'other@example.test','caregiver')
    sc,today=schedule(c,p)
    path=f'/patients/{pid}/doses?start={today}&end={today}'
    assert c.get(path,headers=cg).status_code==403
    cid=connection(c,p,cg,pid)
    rows=c.get(path,headers=cg).json();assert len(rows)==2
    assert c.get(path,headers=stranger).status_code==403
    assert c.post('/schedules',headers=cg,json={'name':'A','instructions':'B','times':['08:00'],'start':today}).status_code==403
    body=report(sc['id'],today)
    r=c.post('/reports',headers=p,json=body);assert r.status_code==200,r.text
    retry=c.post('/reports',headers=p,json=body);assert retry.json()['id']==r.json()['id']
    assert c.post('/reports',headers=cg,json=body).status_code==403
    assert c.get(path,headers=cg).json()[0]['status']=='taken'
    assert c.post(f'/connections/{cid}/notes',headers=cg,json={'text':'Demo check-in'}).status_code==201
    assert c.get(f'/connections/{cid}/notes',headers=stranger).status_code==403
    assert c.post(f'/connections/{cid}',headers=p,json={'action':'remove'}).status_code==200
    assert c.get(path,headers=cg).status_code==403
    assert c.post(f'/connections/{cid}/notes',headers=cg,json={'text':'Blocked'}).status_code==403
    cid2=connection(c,p,cg,pid)
    assert c.get(f'/connections/{cid2}/notes',headers=cg).json()==[]
    assert c.get(f'/connections/{cid}/notes',headers=cg).status_code==403

def test_conflicts_corrections_and_audit(tmp_path):
    c=setup(tmp_path);p,pid=register(c,'p@example.test');sc,today=schedule(c,p)
    body=report(sc['id'],today)
    assert c.post('/reports',headers=p,json=body).status_code==200
    conflicting=dict(body,request_id='request-00002',outcome='skipped',taken_at=None)
    assert c.post('/reports',headers=p,json=conflicting).status_code==409
    corrected=dict(conflicting,expected_version=1,reason='Tapped the wrong choice')
    r=c.post('/reports',headers=p,json=corrected);assert r.status_code==200,r.text
    assert r.json()['version']==2
    assert c.post('/reports',headers=p,json=corrected).status_code==200
    from sqlalchemy import select
    from app.database import Audit
    with c.app.state.sessions() as s:
        audits=s.scalars(select(Audit).where(Audit.action=='report.correct')).all()
        assert len(audits)==1 and 'taken' in audits[0].previous

def test_validation_and_account_boundaries(tmp_path):
    c=setup(tmp_path);p,pid=register(c,'p@example.test');other,_=register(c,'o@example.test')
    sc,today=schedule(c,p)
    assert c.post('/reports',headers=other,json=report(sc['id'],today)).status_code==404
    assert c.post('/schedules',headers=p,json={'name':'A','instructions':'B','times':['08:00','08:00'],'start':today}).status_code==422
    invalid=dict(report(sc['id'],today),taken_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    assert c.post('/reports',headers=p,json=invalid).status_code==422
    assert c.post('/auth/register',json={'email':'admin@example.test','password':'Valid-password-123','name':'X','role':'admin'}).status_code==422
    assert c.post('/schedules/'+sc['id']+'/stop',headers=p,json={'end':str(datetime.now(timezone.utc).date()-timedelta(days=1))}).status_code==422
    assert c.post('/auth/logout',headers=p).status_code==200
    assert c.get('/me',headers=p).status_code==401

def test_readings_and_summary_do_not_infer_skips(tmp_path):
    c=setup(tmp_path);p,pid=register(c,'p@example.test');sc,today=schedule(c,p)
    reading={'kind':'blood_pressure','value':120,'secondary':80,'unit':'mmHg','measured_at':datetime.now(timezone.utc).isoformat()}
    assert c.post('/readings',headers=p,json=reading).status_code==201
    assert c.post('/readings',headers=p,json=dict(reading,secondary=130)).status_code==422
    summary=c.get(f'/patients/{pid}/summary?start={today}&end={today}',headers=p).json()
    assert summary['skipped']==0
    assert summary['ml']['status']=='not_deployed'

def test_admin_assignments_still_require_consent_and_have_no_health_access(tmp_path):
    c=setup(tmp_path);p,pid=register(c,'patient@example.test')
    ah,aid=register(c,'admin@example.test','caregiver')
    co,cid=register(c,'coordinator@example.test','caregiver')
    from app.database import User
    with c.app.state.sessions() as s:
        s.get(User,aid).role='admin';s.get(User,cid).role='coordinator';s.commit()
    sc,today=schedule(c,p)
    assert c.get('/admin/accounts',headers=co).status_code==403
    accounts=c.get('/admin/accounts',headers=ah).json()
    assert all('password' not in a and 'condition' not in a for a in accounts)
    assigned=c.post('/admin/assignments',headers=ah,json={'patient_id':pid,'coordinator_id':cid})
    assert assigned.status_code==201
    path=f'/patients/{pid}/doses?start={today}&end={today}'
    assert c.get(path,headers=ah).status_code==403
    assert c.get(path,headers=co).status_code==403
    relation=assigned.json()['id']
    assert c.post('/connections/'+relation,headers=p,json={'action':'accept'}).status_code==200
    assert c.get(path,headers=co).status_code==200
    assert c.post('/reports',headers=co,json=report(sc['id'],today)).status_code==403
    assert c.post(f'/connections/{relation}/notes',headers=co,json={'text':'Follow-up recorded'}).status_code==201
    assert c.put('/admin/accounts/'+cid,headers=ah,json={'enabled':False}).status_code==200
    assert c.get(path,headers=co).status_code==401

def test_review_items_are_deduplicated_and_permission_checked(tmp_path):
    c=setup(tmp_path);p,pid=register(c,'patient@example.test');cg,_=register(c,'care@example.test','caregiver')
    other,_=register(c,'other@example.test','caregiver');relation=connection(c,p,cg,pid)
    sc,today=schedule(c,p)
    body=dict(report(sc['id'],today),outcome='skipped',taken_at=None)
    c.post('/reports',headers=p,json=body);c.post('/reports',headers=p,json=body)
    path=f'/connections/{relation}/alerts'
    alerts=c.get(path,headers=cg).json();assert len(alerts)==1
    ack=f'{path}/{alerts[0]["report_id"]}/ack'
    assert c.post(ack,headers=other).status_code==403
    assert c.post(ack,headers=cg).status_code==200
    assert c.post(ack,headers=cg).status_code==200
    assert c.get(path,headers=cg).json()[0]['acknowledged']

def test_synthetic_lab_is_separate_from_patient_predictions(tmp_path):
    c=setup(tmp_path);p,_=register(c,'patient@example.test');cg,_=register(c,'care@example.test','caregiver')
    assert c.get('/research/synthetic-example',headers=p).status_code==403
    r=c.get('/research/synthetic-example',headers=cg)
    assert r.status_code==200,r.text
    assert r.json()['is_synthetic'] is True
    assert 0<r.json()['score']<1
    assert 'patient_id' not in r.json()
