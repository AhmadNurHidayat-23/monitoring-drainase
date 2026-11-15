import csv
import io
from sqlalchemy import select
from core.validate import date,choice
from core.security import Problem
from .models import Channel,Inspection,Job,Work,Region,User
from .repository import allowed,find

def report(db,user,f):
    start=date(f.get('from')) if f.get('from') else '0001-01-01'
    end=date(f.get('to')) if f.get('to') else '9999-12-31'
    if end<start:
        raise Problem('Periode laporan tidak valid.')
    kind=choice(f.get('kind','inspections'),('inspections','maintenance'),'Laporan')
    rows=[['Tanggal','Wilayah','Kode saluran','Saluran','Petugas','Kondisi / Status','Kerusakan / Progres','Sumbatan %','Catatan']]
    items=db.scalars(select(Inspection).order_by(Inspection.on_date,Inspection.id)) if kind=='inspections' else db.scalars(select(Work).order_by(Work.on_date,Work.id))
    for r in items:
        j=find(db,Job,r.job_id) if kind=='maintenance' else None
        c=find(db,Channel,r.channel_id if kind=='inspections' else j.channel_id)
        try:
            allowed(db,user,c)
        except Problem:
            continue
        if user['role']!='Admin' and j and j.staff_id!=user['id']:
            continue
        if not start<=r.on_date<=end or f.get('region_id') and str(c.region_id)!=str(f['region_id']):
            continue
        rows.append([r.on_date,find(db,Region,c.region_id).name,c.code,c.name,find(db,User,r.actor_id).name,r.condition if kind=='inspections' else r.status,r.damage if kind=='inspections' else r.progress,r.blockage if kind=='inspections' else '',r.note+(' / '+r.blockage_note if kind=='inspections' else '')])
    output=io.StringIO()
    writer=csv.writer(output)
    for row in rows:
        writer.writerow(["'"+str(v) if str(v).startswith(('=','+','@','-')) else v for v in row])
    return '\ufeff'+output.getvalue()
