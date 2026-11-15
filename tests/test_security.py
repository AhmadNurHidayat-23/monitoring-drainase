import io
import secrets
from PIL import Image
from fastapi.testclient import TestClient
from core.db import connect
from conftest import inspection,job,day

def picture():
    out=io.BytesIO()
    image=Image.new('RGB',(200,120),'#376A73')
    exif=image.getexif()
    exif[270]='Metadata demonstrasi yang harus dihapus'
    image.save(out,'JPEG',exif=exif)
    return out.getvalue()

def upload(c,h,**extra):
    return c.post('/api/photos',data={'kind':'inspection','record_id':1,'stage':'Kondisi','caption':'Foto demonstrasi',**extra},files={'file':('contoh.jpg',picture(),'image/jpeg')},headers=h)

def test_staff_only_assigned_channels_jobs_and_photos(env):
    _,clients,_=env
    a,ah=clients['admin']
    c,h=clients['satu']
    other,oh=clients['dua']
    assert len(c.get('/api/state').json()['channels'])==1
    assert c.get('/api/channels/2/history').status_code==403
    assert c.post('/api/inspections',json=inspection(channel_id=2),headers=h).status_code==403
    assert c.post('/api/channels',json={},headers=h).status_code==403
    a.post('/api/jobs',json=job(),headers=ah)
    assert other.post('/api/works',json={'job_id':1,'on_date':day(),'status':'Dikerjakan','progress':20,'note':'Uji','version':1},headers=oh).status_code==403
    c.post('/api/inspections',json=inspection(),headers=h)
    assert upload(c,h).status_code==200
    assert other.get('/api/photos/1').status_code==403
    assert upload(other,oh).status_code==403

def test_photos_validation_metadata_removed_and_before_after(env):
    _,clients,folder=env
    c,h=clients['satu']
    c.post('/api/inspections',json=inspection(),headers=h)
    assert upload(c,h).status_code==200
    r=c.get('/api/photos/1')
    image=Image.open(io.BytesIO(r.content))
    assert image.format=='JPEG' and not image.getexif()
    assert c.post('/api/photos',data={'kind':'inspection','record_id':1,'stage':'Kondisi','caption':'Uji'},files={'file':('fake.jpg',b'<svg>bad</svg>','image/jpeg')},headers=h).status_code==400
    assert c.post('/api/photos',data={'kind':'inspection','record_id':1,'stage':'Kondisi','caption':'Uji'},files={'file':('large.jpg',b'x'*(6*1024*1024),'image/jpeg')},headers=h).status_code==413
    a,ah=clients['admin']
    a.post('/api/jobs',json=job(),headers=ah)
    r=c.post('/api/works',json={'job_id':1,'on_date':day(),'status':'Dikerjakan','progress':30,'note':'Uji','version':1},headers=h)
    for stage in ['Sebelum','Sesudah']:
        assert upload(c,h,kind='work',record_id=r.json()['id'],stage=stage).status_code==200
    assert len(list((folder/'photos').glob('*.jpg')))==3

def test_photo_failure_rolls_back_file_and_database(env):
    _,clients,folder=env
    c,h=clients['satu']
    c.post('/api/inspections',json=inspection(),headers=h)
    raw=connect(folder)
    raw.execute("CREATE TRIGGER reject_photo BEFORE INSERT ON photos BEGIN SELECT RAISE(ABORT,'test photo rollback'); END")
    raw.commit()
    raw.close()
    assert upload(c,h).status_code==409
    assert not list((folder/'photos').glob('*.jpg'))

def test_auth_csrf_origin_isolated_sessions_and_disabled_user(env):
    app,clients,folder=env
    c,h=clients['satu']
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/state').status_code==401
        assert anonymous.get('/api/photos/1').status_code==401
        anonymous.cookies.set('app_session',c.cookies.get('monitoring_drainase_session'))
        assert anonymous.get('/api/state').status_code==401
    assert c.post('/api/inspections',json=inspection()).status_code==403
    assert c.post('/api/inspections',json=inspection(),headers={**h,'Origin':'https://example.invalid'}).status_code==403
    raw=connect(folder)
    raw.execute("UPDATE users SET active=0 WHERE username='satu'")
    raw.commit()
    raw.close()
    assert c.get('/api/state').status_code==401

def test_admin_staff_management_and_assignment_guard(env):
    _,clients,_=env
    c,h=clients['admin']
    password=secrets.token_hex(20)
    assert c.post('/api/staff',json={'username':'baru','name':'Petugas Baru Contoh','password':password},headers=h).status_code==200
    assert c.put('/api/staff/4',json={'name':'Petugas Diubah','active':0},headers=h).status_code==200
    assert c.put('/api/staff/2',json={'name':'Petugas Satu','active':0},headers=h).status_code==409
    assert c.put('/api/staff/1',json={'name':'Admin','active':0},headers=h).status_code==403
    staff,sh=clients['satu']
    assert staff.post('/api/staff',json={'username':'terlarang','name':'Contoh','password':password},headers=sh).status_code==403
