"""Fixed box-relative pixel measurements; no GT or fitted representation."""
import collections,hashlib,io,json,math
from pathlib import Path
import numpy as np
from PIL import Image

def box(value):
    b=np.asarray(value,dtype=np.float64)
    if b.shape!=(4,) or not np.isfinite(b).all() or b[2]<=b[0] or b[3]<=b[1]:raise ValueError('spatial box geometry')
    return b.tolist()

def context_box(boxes,width,height,padding=.25):
    bs=[box(b) for b in boxes];x1=min(b[0] for b in bs);y1=min(b[1] for b in bs);x2=max(b[2] for b in bs);y2=max(b[3] for b in bs);w=x2-x1;h=y2-y1
    return [max(0,min(width,math.floor(x1-padding*w))),max(0,min(height,math.floor(y1-padding*h))),max(0,min(width,math.ceil(x2+padding*w))),max(0,min(height,math.ceil(y2+padding*h)))]

def response(gray):
    g=np.asarray(gray,dtype=np.float64)
    if g.shape!=(128,128) or not np.isfinite(g).all() or (g<0).any() or (g>1).any():raise ValueError('fixed grayscale grid')
    r=np.zeros_like(g);middle=g[1:-1,1:-1];v=np.zeros_like(middle)
    for dx,dy in [(1,0),(0,1),(1,1),(1,-1)]:
        v=np.maximum(v,(g[1-dy:127-dy,1-dx:127-dx]+g[1+dy:127+dy,1+dx:127+dx])/2-middle)
    r[1:-1,1:-1]=v;return r

def describe(gray,original,corrected,cfg):
    spec=cfg['spatial']
    if spec['grid_size']!=128 or spec['context_padding_fraction']!=.25 or spec['directions']!=[[1,0],[0,1],[1,1],[1,-1]] or spec['offset']!=1 or spec['mass_floor']!=1e-12 or gray.mode!='L':raise ValueError('fixed pixel recipe')
    original=box(original);corrected=box(corrected);ctx=context_box([original,corrected],*gray.size)
    if ctx[2]<=ctx[0] or ctx[3]<=ctx[1]:return dict(values=[0.,0.],context=ctx,degenerate='empty_context',mass=0.,areas=[0.,0.],inside_mass=[0.,0.],concentrations=[0.,0.])
    with gray.crop(ctx) as crop:
        with crop.resize((128,128),Image.Resampling.BILINEAR) as resized:r=response(np.asarray(resized,dtype=np.float64)/255)
    mass=float(r.sum());xs=ctx[0]+(np.arange(128)+.5)*(ctx[2]-ctx[0])/128;ys=ctx[1]+(np.arange(128)+.5)*(ctx[3]-ctx[1])/128;areas=[];inside=[];z=[]
    for b in [original,corrected]:
        mask=((ys>=b[1])&(ys<b[3]))[:,None]&((xs>=b[0])&(xs<b[2]))[None,:];areas.append(float(mask.mean()));inside.append(float(r[mask].sum()));z.append(0. if mass<=spec['mass_floor'] else inside[-1]/mass-areas[-1])
    values=[z[1],(z[1]-z[0])/2]
    if not np.isfinite(values).all() or any(abs(v)>1 for v in values):raise ValueError('pixel descriptor bounds')
    return dict(values=values,context=ctx,degenerate='zero_mass' if mass<=spec['mass_floor'] else None,mass=mass,areas=areas,inside_mass=inside,concentrations=z)

def image_bytes(record,guard):
    guard.take('source_image_reads');guard.take('pixel_reads');raw=Path(record['prepared_image']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=record['prepared_image_sha256']:raise ValueError('source image hash')
    return raw

def decode(raw,record,guard,counter):
    guard.take(counter)
    with Image.open(io.BytesIO(raw)) as src:
        src.load()
        if src.size!=(record['width'],record['height']):raise ValueError('source image dimensions')
        return src.convert('L' if counter=='source_image_decodes' else 'RGB')

def extract(data,run,cfg,guard,core,emit):
    marker=run/'spatial_started.json'
    if marker.exists():raise ValueError('duplicate spatial extraction')
    emit('spatial_started.json',dict(protocol=core.PROTOCOL,images=len(data['images']),rows=len(data['candidates']),GT_free=True,fitted_parameters=0))
    by=collections.OrderedDict()
    for row in data['candidates']:by.setdefault(row['image_id'],[]).append(row)
    output=[None]*len(data['candidates'])
    with (run/'image_progress.jsonl').open('x',encoding='utf8') as journal:
        for im,rows in by.items():
            guard.check();record=data['images'][im];raw=image_bytes(record,guard);image=decode(raw,record,guard,'source_image_decodes');del raw
            try:
                for row in rows:
                    guard.take('spatial_feature_rows');desc=describe(image,row['row']['original_box_xyxy'],row['row']['box_xyxy'],cfg)
                    output[row['index']]=dict(index=row['index'],parent_id=row['parent_id'],image_id=im,location=row['location'],**desc)
            finally:image.close()
            journal.write(json.dumps(dict(image_id=im,sha256=record['prepared_image_sha256'],rows=len(rows)))+'\n');journal.flush()
    if any(v is None or v['index']!=i for i,v in enumerate(output)):raise ValueError('incomplete pixel descriptors')
    emit('spatial_features.json',dict(protocol=core.PROTOCOL,GT_free=True,fitted_parameters=0,rows=output))
    emit('spatial_extraction_receipt.json',dict(images=len(by),rows=len(output),progress_sha256=core.sha(run/'image_progress.jsonl',guard.check),features_sha256=core.sha(run/'spatial_features.json',guard.check),source_images=data['images']))
    return output

def cases(data,targets,added,run,cfg,guard,core,emit):
    # Called only after complete OOF freeze and evaluation, never for learning.
    frozen=core.read(run/'prediction_freeze_receipt.json')
    for n,h in frozen['files'].items():core.e12.checked(run/n,h,guard.check)
    if not (run/'result.json').is_file():raise ValueError('case selection before evaluation')
    by={r['parent_id']:r for r in data['candidates']};originals={r['parent_id']:r for r in data['originals']};kind='OOF_appended' if added else 'FIT_opportunity_not_selected'
    keys={r['parent_id'] for r in added} if added else {r['parent_id'] for payload in data['labels'] for r in payload['rows'] if r['U']>0}
    keys=sorted(keys,key=lambda key:(-originals[key]['score'],by[key]['image_id'],tuple(by[key]['row']['box_xyxy']),key))[:cfg['spatial']['case_limit']];rows=[];buffers=[]
    for j,key in enumerate(keys):
        row=by[key];record=data['images'][row['image_id']];raw=image_bytes(record,guard)
        # One case decode occurs in rendering from this same verified buffer.
        buffers.append(raw);dest=run/'case_images'/f'{j}.jpg';dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw)
        rows.append(dict(parent_id=key,image_id=row['image_id'],location=row['location'],kind=kind,width=record['width'],height=record['height'],original=originals[key],corrected=row['row'],GT=targets[row['image_id']],snapshot=dest.relative_to(run).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),descriptor=data['spatial'][row['index']]))
    payload=dict(rule='actual OOF additions else known FIT opportunities; descending original score,image,box,key; unique source keys; at most6',kind=kind,cases=rows,after_prediction_freeze_and_evaluation=True,used_for_learning=False)
    emit('cases.json',payload);return payload,buffers
