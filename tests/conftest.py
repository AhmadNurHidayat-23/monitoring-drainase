import secrets
from datetime import date,timedelta
import pytest
from fastapi.testclient import TestClient
from app import create_app
from app.repository import today
from core.db import connect
from core.security import add_user

def day(offset=0):
    return (date.fromisoformat(today())+timedelta(days=offset)).isoformat()

def channel(**extra):
    return {'code':'DEMO-01','name':'Saluran Contoh','address':'Lokasi demonstrasi','region_id':1,'length':125.5,'kind':'Terbuka','lat':-6.2,'lng':106.82,'staff_id':2,**extra}

def inspection(**extra):
    return {'channel_id':1,'on_date':day(),'damage':0,'blockage':0,'blockage_note':'','note':'Inspeksi demonstrasi',**extra}

def job(**extra):
    return {'channel_id':1,'staff_id':2,'starts_on':day(-2),'target_on':day(7),'task':'Pembersihan contoh',**extra}

@pytest.fixture
def env(tmp_path):
    app=create_app({'INSTANCE_DIR':str(tmp_path)})
    raw=connect(tmp_path)
    password=secrets.token_hex(20)
    for name,role in [('admin','Admin'),('satu','Petugas'),('dua','Petugas')]:
        add_user(raw,name,'Penguji '+name,role,password)
    raw.close()
    clients={}
    for name in ['admin','satu','dua']:
        c=TestClient(app)
        response=c.post('/api/login',json={'username':name,'password':password})
        assert response.status_code==200
        clients[name]=(c,{'X-CSRF-Token':response.json()['csrf']})
    c,h=clients['admin']
    assert c.post('/api/regions',json={'name':'Wilayah Demonstrasi'},headers=h).status_code==200
    assert c.post('/api/channels',json=channel(),headers=h).status_code==200
    assert c.post('/api/channels',json=channel(code='DEMO-02',name='Saluran Kedua',staff_id=3),headers=h).status_code==200
    yield app,clients,tmp_path
    for c,_ in clients.values():
        c.close()
    app.state.engine.dispose()
