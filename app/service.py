import math
from sqlalchemy import select
from core.validate import text,integer,date,choice
from core.security import Problem
from .models import Channel,Region,User,Job,Inspection,InspectionPlan,Work
from .repository import find,allowed,latest,today

def numeric(v,label,minimum,maximum):
    try:
        if isinstance(v,bool) or str(v).strip()=='':
            raise ValueError()
        value=float(v)
        if not math.isfinite(value) or not minimum<=value<=maximum:
            raise ValueError()
        return value
    except (ValueError,TypeError,OverflowError):
        raise Problem(label+' harus angka antara '+str(minimum)+' dan '+str(maximum)+'.') from None

def staff(db,id):
    u=find(db,User,integer(id,'Petugas',1))
    if u.role!='Petugas' or not u.active:
        raise Problem('Pilih Petugas yang aktif.')
    return u.id

def channel(db,b,id=None):
    values={'code':text(b.get('code'),'Kode',40),'name':text(b.get('name'),'Nama saluran',120),'address':text(b.get('address'),'Alamat',250),'region_id':integer(b.get('region_id'),'Wilayah',1),'length':numeric(b.get('length'),'Panjang meter',0.01,1000000),'kind':choice(b.get('kind'),('Terbuka','Tertutup','Gorong-gorong'),'Jenis'),'lat':numeric(b.get('lat'),'Lintang',-90,90),'lng':numeric(b.get('lng'),'Bujur',-180,180),'staff_id':staff(db,b.get('staff_id'))}
    find(db,Region,values['region_id'])
    item=find(db,Channel,id) if id else Channel()
    if id and item.archived:
        raise Problem('Pulihkan saluran sebelum mengedit.',409)
    for k,v in values.items():
        setattr(item,k,v)
    db.add(item)
    db.flush()
    return item.id

def inspect(db,user,b):
    c=find(db,Channel,integer(b.get('channel_id'),'Saluran',1))
    allowed(db,user,c,True)
    on=date(b.get('on_date'))
    if c.archived or on>today():
        raise Problem('Saluran diarsipkan atau tanggal inspeksi mendatang.')
    damage,blockage=integer(b.get('damage'),'Kerusakan',0,3),integer(b.get('blockage'),'Penyumbatan',0,100)
    plan_id=integer(b['plan_id'],'Jadwal inspeksi',1) if b.get('plan_id') else None
    if plan_id:
        p=find(db,InspectionPlan,plan_id)
        if p.channel_id!=c.id or p.canceled or user['role']!='Admin' and p.staff_id!=user['id']:
            raise Problem('Jadwal inspeksi tidak sesuai penugasan.',403)
    item=Inspection(channel_id=c.id,plan_id=plan_id,on_date=on,damage=damage,blockage=blockage,condition='Kritis' if damage==3 or blockage>=75 else 'Perlu Penanganan' if damage>0 or blockage>=25 else 'Baik',blockage_note=text(b.get('blockage_note',''),'Keterangan sumbatan',1000,blockage>0),note=text(b.get('note'),'Catatan inspeksi',2000),actor_id=user['id'])
    db.add(item)
    db.flush()
    return item.id

def plan(db,b):
    c=find(db,Channel,integer(b.get('channel_id'),'Saluran',1))
    if c.archived:
        raise Problem('Saluran diarsipkan.',409)
    item=InspectionPlan(channel_id=c.id,staff_id=staff(db,b.get('staff_id')),on_date=date(b.get('on_date')),note=text(b.get('note'),'Catatan jadwal',1000))
    db.add(item)

def job(db,b,id=None):
    c=find(db,Channel,integer(b.get('channel_id'),'Saluran',1))
    start,target=date(b.get('starts_on')),date(b.get('target_on'))
    if c.archived or target<start:
        raise Problem('Saluran diarsipkan atau rentang jadwal tidak valid.')
    item=find(db,Job,id) if id else Job()
    if id:
        if integer(b.get('version'),'Versi',1)!=item.version:
            raise Problem('Jadwal telah berubah. Muat ulang dan coba kembali.',409)
        if latest(db,Work,Work.job_id,id) and (item.channel_id!=c.id or item.starts_on!=start):
            raise Problem('Saluran dan tanggal mulai yang memiliki riwayat dipertahankan.',409)
        item.version+=1
    item.channel_id,item.staff_id,item.starts_on,item.target_on,item.task=c.id,staff(db,b.get('staff_id')),start,target,text(b.get('task'),'Pekerjaan',1000)
    db.add(item)

def work(db,user,b):
    j=find(db,Job,integer(b.get('job_id'),'Pekerjaan',1))
    c=find(db,Channel,j.channel_id)
    if user['role']!='Admin' and j.staff_id!=user['id']:
        raise Problem('Pekerjaan ini tidak ditugaskan kepada Anda.',403)
    on=date(b.get('on_date'))
    if c.archived or j.canceled or on<j.starts_on or on>today():
        raise Problem('Pekerjaan tidak aktif atau tanggal pelaksanaan tidak valid.')
    if integer(b.get('version'),'Versi',1)!=j.version:
        raise Problem('Pekerjaan telah berubah. Muat ulang dan coba kembali.',409)
    status=choice(b.get('status'),('Dikerjakan','Selesai','Ditunda'),'Status pekerjaan')
    progress=integer(b.get('progress'),'Progres',0,100)
    if (status=='Selesai')!=(progress==100):
        raise Problem('Status Selesai harus 100%; status lain harus di bawah 100%.')
    old=latest(db,Work,Work.job_id,j.id)
    if old and old.status=='Selesai' and user['role']!='Admin':
        raise Problem('Pekerjaan selesai hanya dapat dibuka kembali oleh Admin.',409)
    item=Work(job_id=j.id,on_date=on,status=status,progress=progress,note=text(b.get('note'),'Hasil pemeliharaan',2000),actor_id=user['id'])
    db.add(item)
    j.version+=1
    db.flush()
    return item.id

def archive(db,id,restore=False):
    c=find(db,Channel,id)
    if not restore:
        for j in db.scalars(select(Job).where(Job.channel_id==id,Job.canceled==0)):
            w=latest(db,Work,Work.job_id,j.id)
            if not w or w.status!='Selesai':
                raise Problem('Selesaikan atau batalkan pekerjaan aktif sebelum mengarsipkan.',409)
    c.archived=0 if restore else 1
