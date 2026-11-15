from sqlalchemy import select
from core.security import Problem,add_user
from core.validate import text,integer
from .models import User,Channel,Job
from .repository import find,latest
from .models import Work

def update(db,id,b):
    u=find(db,User,id)
    if u.role!='Petugas':
        raise Problem('Hanya akun Petugas dapat dikelola melalui halaman ini.',403)
    active=integer(b.get('active'),'Keaktifan',0,1)
    if not active:
        if db.scalar(select(Channel).where(Channel.staff_id==id,Channel.archived==0)):
            raise Problem('Alihkan saluran aktif sebelum menonaktifkan Petugas.',409)
        for j in db.scalars(select(Job).where(Job.staff_id==id,Job.canceled==0)):
            w=latest(db,Work,Work.job_id,j.id)
            if not w or w.status!='Selesai':
                raise Problem('Alihkan pekerjaan aktif sebelum menonaktifkan Petugas.',409)
    u.name,u.active=text(b.get('name'),'Nama petugas',80),active

def create(raw,b):
    add_user(raw,b.get('username'),text(b.get('name'),'Nama petugas',80),'Petugas',b.get('password'))
