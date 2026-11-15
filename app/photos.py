import io
import uuid
import warnings
from pathlib import Path
from PIL import Image,UnidentifiedImageError
from core.security import Problem
from core.validate import text,integer,choice
from .models import Photo,Inspection,Work,Job,Channel
from .repository import find,allowed
Image.MAX_IMAGE_PIXELS=20000000

def convert(content):
    if not content or len(content)>5*1024*1024:
        raise Problem('Gambar maksimal 5 MB.',413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in ('JPEG','PNG','WEBP') or getattr(image,'n_frames',1)!=1:
                    raise ValueError()
                image.load()
                image.thumbnail((2000,2000))
                output=io.BytesIO()
                image.convert('RGB').save(output,'JPEG',quality=85)
                return output.getvalue()
    except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise Problem('Gambar JPEG/PNG/WebP tunggal yang valid diperlukan; maksimal 20 juta piksel.') from None

def save(db,user,folder,b,content,mime):
    if mime not in ('image/jpeg','image/png','image/webp'):
        raise Problem('Jenis gambar tidak didukung.')
    kind=choice(b.get('kind'),('inspection','work'),'Jenis dokumentasi')
    id=integer(b.get('record_id'),'Catatan',1)
    if kind=='inspection':
        r=find(db,Inspection,id)
        c=find(db,Channel,r.channel_id)
        allowed(db,user,c,True)
        if user['role']!='Admin' and r.actor_id!=user['id']:
            raise Problem('Dokumentasi hanya untuk inspeksi Anda.',403)
    else:
        r=find(db,Work,id)
        j=find(db,Job,r.job_id)
        c=find(db,Channel,j.channel_id)
        if user['role']!='Admin' and (j.staff_id!=user['id'] or r.actor_id!=user['id']):
            raise Problem('Dokumentasi hanya untuk pekerjaan Anda.',403)
    if c.archived:
        raise Problem('Saluran diarsipkan.',409)
    stage=choice(b.get('stage'),('Kondisi',) if kind=='inspection' else ('Sebelum','Sesudah'),'Tahap foto')
    payload=convert(content)
    directory=(Path(folder)/'photos').resolve()
    directory.mkdir(exist_ok=True,parents=True)
    target=directory/(uuid.uuid4().hex+'.jpg')
    try:
        target.write_bytes(payload)
        item=Photo(inspection_id=id if kind=='inspection' else None,work_id=id if kind=='work' else None,token=target.name,stage=stage,caption=text(b.get('caption'),'Keterangan foto',300),actor_id=user['id'])
        db.add(item)
        db.flush()
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise

def photo_path(db,user,folder,id):
    p=find(db,Photo,id)
    c=find(db,Channel,find(db,Inspection,p.inspection_id).channel_id) if p.inspection_id else find(db,Channel,find(db,Job,find(db,Work,p.work_id).job_id).channel_id)
    allowed(db,user,c)
    directory=(Path(folder)/'photos').resolve()
    target=(directory/p.token).resolve()
    if target.parent!=directory or not target.is_file():
        raise Problem('Foto tidak tersedia.',404)
    return target
