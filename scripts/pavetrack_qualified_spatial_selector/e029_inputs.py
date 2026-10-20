"""Role-scoped legacy member access and immutable geometry; no global GT load."""
import collections,hashlib,json,zipfile
from pathlib import Path
import e029_support as c

BANK_MEMBERS={'input_snapshot/qualification.json','input_snapshot/candidate_identity.json','input_snapshot/scores.json'}
def members(role,fold=None):
    if role=='bank':return BANK_MEMBERS
    if role=='fit' and type(fold) is int and fold in range(3):return {f'input_snapshot/fit8_fold_{fold}.json',f'supervision_fold_{fold}.json',f'context_fold_{fold}.json'}
    raise PermissionError('no ZIP capability in '+role)

def zip_values(path,lock,role,fold=None):
    allowed=members(role,fold);out={}
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('duplicate source member')
        for name in sorted(allowed):
            if z.getinfo(name).file_size>128*1024**2:raise ValueError('source member cap')
            raw=z.read(name)
            if hashlib.sha256(raw).hexdigest()!=lock['source_files'][name]:raise ValueError('source member identity')
            out[name]=raw
    return out

def bank(paths,lock,cfg,guard,out):
    c.checked(paths['E017_zip'],lock['source_zip_sha256'])
    raw=zip_values(paths['E017_zip'],lock,'bank');q=out/'qualification_prefix_source.json';q.write_bytes(raw['input_snapshot/qualification.json'])
    originals=c.legacy.originals_from_file(q,43347,lambda p:c.core.e12.a.scoped.Cursor(p,guard.check));q.unlink()
    if c.digest(originals)!=lock['original_rows_digest']:raise ValueError('E003 original digest')
    manifest=json.loads(raw['input_snapshot/candidate_identity.json'])['rows'];scores=json.loads(raw['input_snapshot/scores.json']);del raw
    if len(manifest)!=31156 or scores['source_keys']!=[r['source_parent_key'] for r in manifest]:raise ValueError('candidate source keys')
    rows=c.core.features(originals,manifest,scores['probabilities'],cfg)
    for row in rows:row['positive_intersection']=c.locality.positive_intersection(row['row'])
    ims={r['image_id']:r['reid'] for r in originals};images={}
    for m,row in zip(manifest,rows,strict=True):
        if (row['index'],row['parent_id'],row['image_id'],row['location'])!=(m['index'] if 'index' in m else row['index'],m['source_parent_key'],m['image_id'],m['location']):raise ValueError('candidate mapping')
        rec={k:m[k] for k in ['image_id','location','prepared_image','prepared_image_sha256','width','height']}
        if m['width']!=1920 or m['height']!=1080 or rec['location']!=ims[rec['image_id']]:raise ValueError('image dimensions/location')
        if rec['image_id'] in images and images[rec['image_id']]!=rec:raise ValueError('image duplicate identity')
        if Path(rec['prepared_image']).parent!=Path(lock['source_image_root']) or Path(rec['prepared_image']).name!=rec['image_id']:raise ValueError('source image path')
        images[rec['image_id']]=rec
    if len(ims)!=835 or set(images)!=set(ims) or sum(r['eligible'] for r in rows)!=19384 or set(ims.values())!=set(cfg['locations']):raise ValueError('bank scope/count')
    c.checked(paths['contexts'],lock['contexts_sha256']);contexts=c.read(paths['contexts'])['rows']
    geometry=c.core.module('e029_context_geometry',c.ROOT/'scripts/pavetrack_spatial_selector/spatial.py')
    if len(contexts)!=len(rows):raise ValueError('context row count')
    for r,ctx in zip(rows,contexts,strict=True):
        if ctx!=geometry.context_box([r['row']['original_box_xyxy'],r['row']['box_xyxy']],1920,1080):raise ValueError('old context identity')
    return dict(originals=originals,candidates=rows,image_locations=ims,images=images,contexts=contexts,original_digest=c.digest(originals))

def targets(path,locations,image_locations,guard,decode=None):
    """Scoped byte reader skips other locations without deserialising their GT."""
    cursor=c.core.e12.a.scoped.Cursor(path,guard.check)
    if decode is not None:cursor.decode=decode(cursor.decode)
    try:
        top=dict(cursor.fields());rows=list(cursor.selected_rows(top['records'],set(locations)))
    finally:cursor.close()
    expected={im for im,loc in image_locations.items() if loc in locations}
    if {r['image_id'] for r in rows}!=expected or len(rows)!=len(expected):raise ValueError('role target scope')
    out={}
    for r in rows:
        if r['split']!='train' or r['reid']!=image_locations[r['image_id']] or r['width']!=1920 or r['height']!=1080:raise ValueError('GT identity')
        for b in r['crack_boxes_xyxy']:c.core.e12.a.box(b,r)
        out[r['image_id']]=r['crack_boxes_xyxy']
    return out

def inference_from_saved(path):
    """Decode only trained numeric heads/gate, never FIT policy/GT fields."""
    q=c.core.e12.a.scoped.Cursor(path)
    try:
        fields=dict(q.fields());heads={}
        for name,span in q.fields(fields['heads'][0]):
            if name not in ['Q','N','A']:raise ValueError('saved head name')
            fields_h=dict(q.fields(span[0]));heads[name]={k:q.decode(fields_h[k]) for k in ['coefficients','columns','verified']}
        return dict(heads=heads,threshold=q.decode(fields['threshold']))
    finally:q.close()
