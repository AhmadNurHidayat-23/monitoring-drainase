from fastapi import APIRouter,Request,Depends
from fastapi.responses import FileResponse,Response
from sqlalchemy.orm import Session
from core.auth import context,require,data
from core.validate import text
from core.security import Problem
from . import repository as repo,service,photos,staff,reports
from .models import Region,Job,InspectionPlan
api=APIRouter()

@api.get('/api/state')
async def state(request:Request,ctx=Depends(context)):
    user=require(ctx,request)
    with Session(request.app.state.engine) as db:
        return repo.state(db,user,request.query_params)

@api.get('/api/channels/{id}/history')
async def history(request:Request,id:int,ctx=Depends(context)):
    user=require(ctx,request)
    with Session(request.app.state.engine) as db:
        return repo.history(db,user,id)

@api.get('/api/photos/{id}')
async def photo(request:Request,id:int,ctx=Depends(context)):
    user=require(ctx,request)
    with Session(request.app.state.engine) as db:
        target=photos.photo_path(db,user,request.app.state.folder,id)
    return FileResponse(target,media_type='image/jpeg',headers={'Content-Disposition':'inline; filename=documentation.jpg'})

@api.post('/api/photos')
async def upload(request:Request,ctx=Depends(context)):
    user=require(ctx,request)
    form=await request.form(max_files=1,max_fields=8,max_part_size=65536)
    file=form.get('file')
    if not file or not hasattr(file,'read'):
        raise Problem('Pilih gambar dokumentasi.')
    payload=await file.read(5*1024*1024+1)
    target=None
    try:
        with Session(request.app.state.engine) as db,db.begin():
            target=photos.save(db,user,request.app.state.folder,form,payload,file.content_type)
    except Exception:
        if target:
            target.unlink(missing_ok=True)
        raise
    return {'message':'Foto tersimpan. Metadata lokasi foto dihapus saat pengolahan.'}

@api.post('/api/{kind}')
@api.put('/api/{kind}/{id}')
@api.delete('/api/{kind}/{id}')
async def save(request:Request,kind:str,id:int=None,ctx=Depends(context)):
    user=require(ctx,request,('Admin','Petugas') if kind in ('inspections','works') else ('Admin',))
    if kind not in ('channels','regions','jobs','plans','staff','inspections','works'):
        raise Problem('Alamat tidak tersedia.',404)
    b=await data(request)
    if kind=='staff' and request.method=='POST':
        staff.create(ctx.db,b)
        return {'message':'Akun Petugas dibuat.'}
    result_id=None
    with Session(request.app.state.engine) as db,db.begin():
        if request.method=='DELETE':
            if kind=='channels':
                service.archive(db,id)
            elif kind=='regions':
                db.delete(repo.find(db,Region,id))
            elif kind in ('jobs','plans'):
                repo.find(db,Job if kind=='jobs' else InspectionPlan,id).canceled=1
            else:
                raise Problem('Riwayat dan akun dipertahankan.',405)
        elif kind in ('inspections','works'):
            if request.method!='POST':
                raise Problem('Riwayat dipertahankan; buat catatan koreksi baru.',405)
            result_id=service.inspect(db,user,b) if kind=='inspections' else service.work(db,user,b)
        elif kind=='channels':
            result_id=service.channel(db,b,id)
        elif kind=='jobs':
            service.job(db,b,id)
        elif kind=='plans':
            if id:
                raise Problem('Batalkan dan buat jadwal baru untuk menjaga riwayat.',405)
            service.plan(db,b)
        elif kind=='staff':
            staff.update(db,id,b)
        else:
            name=text(b.get('name'),'Wilayah',100)
            if id:
                repo.find(db,Region,id).name=name
            else:
                db.add(Region(name=name))
    return {'message':'Data drainase disimpan.','id':result_id}

@api.post('/api/channels/{id}/restore')
async def restore(request:Request,id:int,ctx=Depends(context)):
    require(ctx,request,('Admin',))
    with Session(request.app.state.engine) as db,db.begin():
        service.archive(db,id,True)
    return {'message':'Saluran dipulihkan.'}

@api.get('/api/export')
async def export(request:Request,ctx=Depends(context)):
    user=require(ctx,request)
    with Session(request.app.state.engine) as db:
        content=reports.report(db,user,request.query_params)
    return Response(content,media_type='text/csv;charset=utf-8',headers={'Content-Disposition':'attachment; filename=laporan-drainase.csv'})
