from core.db import connect
from core.migrate import migrate
from conftest import channel,inspection,job,day

def test_channel_crud_validation_archive_and_unique(env):
    _,clients,_=env
    c,h=clients['admin']
    assert c.put('/api/channels/1',json=channel(name='Saluran Diubah'),headers=h).status_code==200
    assert c.post('/api/channels',json=channel(code='demo-01'),headers=h).status_code==409
    for bad in [channel(lat=91),channel(lng=-181),channel(lat='NaN'),channel(length=0),channel(length=True),channel(staff_id=1),channel(region_id=99)]:
        assert c.post('/api/channels',json=bad,headers=h).status_code in (400,404)
    assert c.post('/api/channels',json=channel(code='NOL',lat=0,lng=0),headers=h).status_code==200
    assert c.request('DELETE','/api/regions/1',json={},headers=h).status_code==409
    assert c.request('DELETE','/api/channels/1',json={},headers=h).status_code==200
    assert len(c.get('/api/state').json()['channels'])==2
    assert len(c.get('/api/state?archived=1').json()['channels'])==1
    assert c.post('/api/channels/1/restore',json={},headers=h).status_code==200

def test_inspection_rules_chronology_and_history(env):
    _,clients,_=env
    c,h=clients['satu']
    assert c.get('/api/state').json()['channels'][0]['condition']=='Belum Diperiksa'
    for values in [inspection(damage=2,blockage=80,blockage_note='Contoh sumbatan'),inspection(on_date=day(-1))]:
        assert c.post('/api/inspections',json=values,headers=h).status_code==200
    state=c.get('/api/state').json()
    assert state['channels'][0]['condition']=='Kritis'
    assert state['summary']['attention']==1
    assert len(c.get('/api/channels/1/history').json()['inspections'])==2
    assert c.post('/api/inspections',json=inspection(on_date=day(1)),headers=h).status_code==400
    assert c.post('/api/inspections',json=inspection(blockage=25),headers=h).status_code==400
    assert c.request('DELETE','/api/inspections/1',json={},headers=h).status_code==405

def test_inspection_plans_assign_access_and_completion(env):
    _,clients,_=env
    c,h=clients['admin']
    plan={'channel_id':2,'staff_id':2,'on_date':day(2),'note':'Penugasan demonstrasi'}
    assert c.post('/api/plans',json=plan,headers=h).status_code==200
    staff,sh=clients['satu']
    assert len(staff.get('/api/state').json()['channels'])==2
    assert len(staff.get('/api/state').json()['upcoming'])==1
    assert staff.post('/api/inspections',json=inspection(channel_id=2,plan_id=1),headers=sh).status_code==200
    assert staff.get('/api/state').json()['plans'][0]['done'] is True
    assert staff.post('/api/inspections',json=inspection(channel_id=2,plan_id=1),headers=sh).status_code==403
    assert c.post('/api/plans',json=plan,headers=h).status_code==200
    assert c.request('DELETE','/api/plans/2',json={},headers=h).status_code==200

def test_jobs_status_history_optimistic_version_and_archive(env):
    _,clients,_=env
    c,h=clients['admin']
    assert c.post('/api/jobs',json=job(),headers=h).status_code==200
    assert c.put('/api/jobs/1',json=job(version=1,task='Pekerjaan diubah'),headers=h).status_code==200
    assert c.request('DELETE','/api/channels/1',json={},headers=h).status_code==409
    staff,sh=clients['satu']
    work={'job_id':1,'on_date':day(),'status':'Dikerjakan','progress':40,'note':'Laporan contoh','version':2}
    assert staff.post('/api/works',json=work,headers=sh).status_code==200
    assert staff.post('/api/works',json=work,headers=sh).status_code==409
    assert staff.post('/api/works',json={**work,'version':3,'status':'Selesai'},headers=sh).status_code==400
    assert staff.post('/api/works',json={**work,'version':3,'on_date':day(-3)},headers=sh).status_code==400
    assert staff.post('/api/works',json={**work,'version':3,'status':'Ditunda','progress':60},headers=sh).status_code==200
    assert staff.post('/api/works',json={**work,'version':4,'status':'Selesai','progress':100},headers=sh).status_code==200
    assert staff.get('/api/state').json()['jobs'][0]['status']=='Selesai'
    assert staff.post('/api/works',json={**work,'version':5},headers=sh).status_code==409
    assert len(staff.get('/api/channels/1/history').json()['works'])==3
    assert c.request('DELETE','/api/channels/1',json={},headers=h).status_code==200

def test_reports_filters_database_values_and_csv(env):
    _,clients,_=env
    c,h=clients['admin']
    c.post('/api/inspections',json=inspection(damage=1,note='=FORMULA DEMO'),headers=h)
    assert len(c.get('/api/state?q=contoh&condition=Perlu%20Penanganan&region_id=1').json()['channels'])==1
    assert c.get('/api/state?q=tidakada').json()['channels']==[]
    r=c.get('/api/export?kind=inspections&from='+day()+'&to='+day()+'&region_id=1')
    assert r.status_code==200 and "'=FORMULA DEMO" in r.text
    assert 'DEMO-01' in r.text
    assert c.get('/api/export?from='+day(1)+'&to='+day(-1)).status_code==400
    c.post('/api/jobs',json=job(),headers=h)
    c.post('/api/works',json={'job_id':1,'on_date':day(),'status':'Dikerjakan','progress':30,'note':'Laporan pemeliharaan','version':1},headers=h)
    r=c.get('/api/export?kind=maintenance')
    assert 'Laporan pemeliharaan' in r.text and 'Dikerjakan' in r.text

def test_restart_sqlalchemy_migration_and_integrity(env):
    app,clients,folder=env
    c,h=clients['satu']
    c.post('/api/inspections',json=inspection(),headers=h)
    engine=migrate(folder)
    engine.dispose()
    assert c.get('/api/state').json()['summary']['good']==1
    raw=connect(folder)
    assert raw.execute('SELECT COUNT(*) FROM inspections').fetchone()[0]==1
    assert raw.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert raw.execute('PRAGMA foreign_key_check').fetchall()==[]
    raw.close()
