from datetime import datetime,timezone,timedelta
from sqlalchemy import select
from core.security import Problem
from .models import Channel,Region,User,Job,Inspection,InspectionPlan,Work,Photo

def today():
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()

def find(db,model,id):
    item=db.get(model,id)
    if not item:
        raise Problem('Data tidak ditemukan.',404)
    return item

def record(item):
    return {c.name:getattr(item,c.name) for c in item.__table__.columns}

def allowed(db,user,channel,write=False):
    if user['role']=='Admin' or channel.staff_id==user['id']:
        return
    jobs=db.scalars(select(Job).where(Job.channel_id==channel.id,Job.staff_id==user['id'],Job.canceled==0)).all()
    for job in jobs:
        if not write or latest(db,Work,Work.job_id,job.id) is None or latest(db,Work,Work.job_id,job.id).status!='Selesai':
            return
    for plan in db.scalars(select(InspectionPlan).where(InspectionPlan.channel_id==channel.id,InspectionPlan.staff_id==user['id'],InspectionPlan.canceled==0)):
        if not write or not db.scalar(select(Inspection).where(Inspection.plan_id==plan.id)):
            return
    raise Problem('Saluran ini tidak ditugaskan kepada Anda.',403)

def latest(db,model,field,id):
    return db.scalar(select(model).where(field==id).order_by(model.on_date.desc(),model.id.desc()))

def job_record(db,j):
    r=record(j)
    work=latest(db,Work,Work.job_id,j.id)
    r.update(status=work.status if work else 'Dijadwalkan',progress=work.progress if work else None,performed_on=work.on_date if work else '',channel=find(db,Channel,j.channel_id).name,staff=find(db,User,j.staff_id).name)
    return r

def state(db,user,f):
    channels=[]
    q=str(f.get('q','')).lower().strip()[:120]
    for c in db.scalars(select(Channel).where(Channel.archived==int(f.get('archived')=='1')).order_by(Channel.name)):
        try:
            allowed(db,user,c)
        except Problem:
            continue
        i=latest(db,Inspection,Inspection.channel_id,c.id)
        r=record(c)
        r.update(condition=i.condition if i else 'Belum Diperiksa',inspected_on=i.on_date if i else '',region=find(db,Region,c.region_id).name,staff=find(db,User,c.staff_id).name)
        if (q and not any(q in r[k].lower() for k in ('name','code','address'))) or (f.get('region_id') and str(c.region_id)!=str(f['region_id'])) or (f.get('condition') and r['condition']!=f['condition']):
            continue
        channels.append(r)
    ids={c['id'] for c in channels}
    jobs=[job_record(db,j) for j in db.scalars(select(Job).order_by(Job.starts_on.desc(),Job.id.desc())) if j.channel_id in ids and (user['role']=='Admin' or j.staff_id==user['id'])]
    plans=[]
    for p in db.scalars(select(InspectionPlan).order_by(InspectionPlan.on_date,InspectionPlan.id)):
        if p.channel_id in ids and (user['role']=='Admin' or p.staff_id==user['id']):
            r=record(p)
            r.update(channel=find(db,Channel,p.channel_id).name,staff=find(db,User,p.staff_id).name,done=bool(db.scalar(select(Inspection).where(Inspection.plan_id==p.id))))
            plans.append(r)
    counts={k:sum(c['condition']==k for c in channels) for k in ('Baik','Perlu Penanganan','Kritis','Belum Diperiksa')}
    return {'channels':channels,'jobs':jobs,'plans':plans,'upcoming':[p for p in plans if not p['done'] and not p['canceled'] and p['on_date']>=today()][:5],'regions':[record(r) for r in db.scalars(select(Region).order_by(Region.name))],'staff':[{'id':u.id,'name':u.name,'username':u.username,'active':u.active} for u in db.scalars(select(User).where(User.role=='Petugas').order_by(User.name))] if user['role']=='Admin' else [],'summary':{'total':len(channels),'good':counts['Baik'],'attention':counts['Perlu Penanganan']+counts['Kritis'],'working':sum(j['status']=='Dikerjakan' and not j['canceled'] for j in jobs)},'conditions':counts}

def history(db,user,id):
    channel=find(db,Channel,id)
    allowed(db,user,channel)
    inspections=[record(i)|{'actor':find(db,User,i.actor_id).name} for i in db.scalars(select(Inspection).where(Inspection.channel_id==id).order_by(Inspection.on_date.desc(),Inspection.id.desc()))]
    jobs=[j for j in db.scalars(select(Job).where(Job.channel_id==id)) if user['role']=='Admin' or j.staff_id==user['id']]
    works=[record(w)|{'actor':find(db,User,w.actor_id).name,'task':j.task} for j in jobs for w in db.scalars(select(Work).where(Work.job_id==j.id).order_by(Work.on_date.desc(),Work.id.desc()))]
    photos=[record(p) for p in db.scalars(select(Photo)) if p.inspection_id in {i['id'] for i in inspections} or p.work_id in {w['id'] for w in works}]
    for p in photos:
        p.pop('token')
    return {'channel':record(channel),'inspections':inspections,'works':works,'photos':photos}
