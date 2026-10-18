"""Frozen intermediate feature cache and learned region-map readout."""
import collections,importlib.util,json,hashlib
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e023_geometry',Path(__file__).resolve().parent.parent/'pavetrack_semantic_selector/spatial.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
box=old.box;context_box=old.context_box;image_bytes=old.image_bytes;decode=old.decode

def coverage(b,ctx):
    b=box(b);x1,y1,x2,y2=ctx
    if x2<=x1 or y2<=y1:raise ValueError('empty region context')
    xs=np.linspace(x1,x2,15);ys=np.linspace(y1,y2,15)
    wx=np.maximum(0,np.minimum(xs[1:],b[2])-np.maximum(xs[:-1],b[0]))/(xs[1:]-xs[:-1]);wy=np.maximum(0,np.minimum(ys[1:],b[3])-np.maximum(ys[:-1],b[1]))/(ys[1:]-ys[:-1])
    return wy[:,None]*wx[None,:]

def describe(heat,original,corrected,ctx):
    h=np.asarray(heat,dtype=np.float64)
    if h.shape!=(14,14) or not np.isfinite(h).all() or (h<0).any() or (h>1).any():raise ValueError('pixel map shape/range')
    mass=float(h.sum());areas=[];inside=[];z=[]
    for b in [original,corrected]:
        cov=coverage(b,ctx);areas.append(float(cov.mean()));inside.append(float(np.sum(h*cov)));z.append(0. if mass<=1e-12 else inside[-1]/mass-areas[-1])
    return dict(values=[z[1],(z[1]-z[0])/2],context=ctx,mass=mass,areas=areas,inside_mass=inside,concentrations=z,degenerate='zero_mass' if mass<=1e-12 else None)

class Backend(old.SemanticBackend):
    def __init__(self,cfg,path,guard,validate):
        super().__init__(cfg,path,guard,validate)
        self.identity.update(feature_slice='features[:6]',feature_shape=[40,14,14],head_input_gradients=False)
    def features(self,image,contexts):
        t=self.bridge.torch
        if not 1<=len(contexts)<=16:raise ValueError('feature batch')
        if self.bridge.model.training or any(p.requires_grad or p.grad is not None for p in self.bridge.model.parameters()):raise ValueError('backbone freeze')
        self.guard.take('max_semantic_batches');self.guard.take('backbone_forwards',len(contexts))
        with t.no_grad(),t.autocast('cuda',enabled=False):
            crops=[]
            for ctx in contexts:
                with image.crop(ctx) as crop:crops.append(self.bridge.transform(crop))
            result=self.bridge.model.features[:6](t.stack(crops).to('cuda:0')).detach().cpu().numpy().copy()
        if result.shape!=(len(contexts),40,14,14) or result.dtype!=np.float32 or not np.isfinite(result).all():raise ValueError('native intermediate feature shape')
        self.guard.check();return result

def backend(cfg,lock,guard,core):
    path=Path(lock['E003_checkpoint'])
    if str(path)!=cfg['spatial']['checkpoint'] or lock['E003_checkpoint_sha256']!=cfg['spatial']['checkpoint_sha256']:raise ValueError('checkpoint identity')
    core.e12.checked(path,lock['E003_checkpoint_sha256'],guard.check);obj=Backend(cfg,path,guard,core.e8.m.base.validate_reranker_checkpoint);core.e12.checked(path,lock['E003_checkpoint_sha256'],guard.check);return obj

def extract(data,run,cfg,guard,core,emit,bridge):
    if (run/'spatial_started.json').exists():raise ValueError('duplicate spatial extraction')
    emit('spatial_started.json',dict(protocol=core.PROTOCOL,runtime=bridge.identity,source_images=len(data['images']),rows=len(data['candidates']),GT_free_features=True))
    n=len(data['candidates']);cache=np.lib.format.open_memmap(run/'pixel_features.npy',mode='w+',dtype=np.float32,shape=(n,40,14,14));contexts=[None]*n;by=collections.OrderedDict()
    guard.take('feature_cache_bytes',int(cache.nbytes))
    for row in data['candidates']:by.setdefault(row['image_id'],[]).append(row)
    with (run/'image_progress.jsonl').open('x') as journal:
        for im,rows in by.items():
            if len(rows)>40:raise ValueError('source image candidate cap')
            rec=data['images'][im];image=decode(image_bytes(rec,guard),rec,guard,'source_image_decodes')
            try:
                for offset in range(0,len(rows),16):
                    batch=rows[offset:offset+16];ctx=[context_box([r['row']['original_box_xyxy'],r['row']['box_xyxy']],*image.size) for r in batch]
                    if any(v[2]<=v[0] or v[3]<=v[1] for v in ctx):raise ValueError('invalid positive context')
                    f=bridge.features(image,ctx)
                    if f.shape!=(len(batch),40,14,14):raise ValueError('feature row shape')
                    for row,feature,window in zip(batch,f,ctx,strict=True):
                        i=row['index'];cache[i]=feature;contexts[i]=window;guard.take('spatial_feature_rows')
            finally:image.close()
            cache.flush();journal.write(json.dumps(dict(image_id=im,sha256=rec['prepared_image_sha256'],rows=len(rows)))+'\n');journal.flush();guard.check()
    cache.flush()
    if any(v is None for v in contexts):raise ValueError('incomplete context coverage')
    emit('pixel_contexts.json',dict(rows=contexts))
    emit('spatial_extraction_receipt.json',dict(runtime=bridge.identity,source_images=data['images'],rows=n,feature_shape=[n,40,14,14],feature_payload_bytes=int(cache.nbytes),features_sha256=core.sha(run/'pixel_features.npy',guard.check),progress_sha256=core.sha(run/'image_progress.jsonl',guard.check)))
    return cache,contexts

def maps_and_descriptors(model,cache,contexts,candidates,run,fold,cfg,guard,pixel):
    maps=np.lib.format.open_memmap(run/f'pixel_maps_fold_{fold}.npy',mode='w+',dtype=np.float32,shape=(len(candidates),14,14));descriptors=[]
    for off in range(0,len(candidates),16):
        batch=candidates[off:off+16];values=pixel.predict(model,cache[off:off+len(batch)]);guard.take('pixel_map_prediction_rows',len(batch));maps[off:off+len(batch)]=values
        for row,value in zip(batch,values,strict=True):
            desc=describe(value,row['row']['original_box_xyxy'],row['row']['box_xyxy'],contexts[row['index']]);descriptors.append(dict(index=row['index'],parent_id=row['parent_id'],image_id=row['image_id'],location=row['location'],**desc))
    maps.flush();return maps,descriptors

def cases(data,targets,added,run,cfg,guard,core,emit):
    frozen=core.read(run/'prediction_freeze_receipt.json')
    for n,h in frozen['files'].items():core.e12.checked(run/n,h,guard.check)
    if not (run/'result.json').exists():raise ValueError('case selection before evaluation')
    by={r['parent_id']:r for r in data['candidates']};originals={r['parent_id']:r for r in data['originals']};kind='OOF_appended' if added else 'FIT_opportunity_not_selected'
    keys={r['parent_id'] for r in added} if added else {r['parent_id'] for pay in data['labels'] for r in pay['rows'] if r['U']>0};keys=sorted(keys,key=lambda key:(-originals[key]['score'],by[key]['image_id'],tuple(by[key]['row']['box_xyxy']),key))[:6];rows=[];buffers=[]
    for j,key in enumerate(keys):
        row=by[key];im=row['image_id'];record=data['images'][im];fold=core.group_of(row['location'],cfg) if added else min(k for k,pay in enumerate(data['labels']) if any(v['parent_id']==key and v['U']>0 for v in pay['rows']))
        raw=image_bytes(record,guard);buffers.append(raw);dest=run/'case_images'/f'{j}.jpg';dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw);desc=dict(data['spatial_by_fold'][fold][row['index']],heatmap=data['pixel_maps'][fold][row['index']].tolist())
        rows.append(dict(parent_id=key,image_id=im,location=row['location'],kind=kind,width=record['width'],height=record['height'],original=originals[key],corrected=row['row'],GT=targets[im],GT_polygons=[v['polygon'] for v in data['annotations'][im] if v['category'] in ['Alligator Crack','Transverse Crack']],snapshot=dest.relative_to(run).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),descriptor=desc,pixel_model_fold=fold,map_scope='OOF held' if added else 'FIT own-model opportunity, not OOF detection'))
    payload=dict(rule='unchanged original-score/image/box/key top6 unique source keys; OOF appended else positive FIT opportunities',kind=kind,cases=rows,after_prediction_freeze_and_evaluation=True,used_for_learning=False)
    emit('cases.json',payload);return payload,buffers
