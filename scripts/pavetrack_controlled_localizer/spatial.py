"""One RGB decode per pinned source; scoped labels and qualification metrics."""
import collections,importlib.util,json
from pathlib import Path
import numpy as np
from PIL import Image
s=importlib.util.spec_from_file_location('e025_old_spatial',Path(__file__).resolve().parent.parent/'pavetrack_pixel_selector/spatial.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
s=importlib.util.spec_from_file_location('e025_old_pixel',Path(__file__).resolve().parent.parent/'pavetrack_pixel_selector/pixels.py');pixel=importlib.util.module_from_spec(s);s.loader.exec_module(pixel)
box=old.box;context_box=old.context_box;image_bytes=old.image_bytes;decode=old.decode

def target(mask,ctx,size=32):
    x1,y1,x2,y2=ctx;xs=np.floor(x1+(np.arange(size)+.5)*(x2-x1)/size).astype(int);ys=np.floor(y1+(np.arange(size)+.5)*(y2-y1)/size).astype(int)
    return mask[np.ix_(np.clip(ys,0,mask.shape[0]-1),np.clip(xs,0,mask.shape[1]-1))]

def extract(data,run,cfg,g,c,emit):
    path=run/'rgb_contexts.npy'
    if path.exists():raise ValueError('duplicate RGB extraction')
    n=len(data['candidates']);cache=np.lib.format.open_memmap(path,mode='w+',dtype=np.uint8,shape=(n,3,128,128));ctx=[None]*n;by=collections.OrderedDict()
    g.take('feature_cache_bytes',int(cache.nbytes))
    for row in data['candidates']:by.setdefault(row['image_id'],[]).append(row)
    with (run/'image_progress.jsonl').open('x') as journal:
        for im,rows in by.items():
            if len(rows)>40:raise ValueError('image context cap')
            rec=data['images'][im];image=decode(image_bytes(rec,g),rec,g,'source_image_decodes')
            try:
                for row in rows:
                    i=row['index'];window=context_box([row['row']['original_box_xyxy'],row['row']['box_xyxy']],*image.size)
                    if window[2]<=window[0] or window[3]<=window[1]:raise ValueError('empty context')
                    with image.crop(window) as crop:
                        with crop.resize((128,128),Image.Resampling.BILINEAR) as resized:cache[i]=np.asarray(resized,dtype=np.uint8).transpose(2,0,1)
                    ctx[i]=window;g.take('spatial_feature_rows')
            finally:image.close()
            cache.flush();journal.write(json.dumps(dict(image_id=im,sha256=rec['prepared_image_sha256'],rows=len(rows)))+'\n');journal.flush();g.check()
    cache.flush();emit('pixel_contexts.json',dict(rows=ctx));emit('spatial_extraction_receipt.json',dict(images=data['images'],rows=n,shape=list(cache.shape),payload_bytes=int(cache.nbytes),features_sha256=c.sha(path,g.check),progress_sha256=c.sha(run/'image_progress.jsonl',g.check),E003_loaded=False))
    return cache,ctx

def references(data,fold,run,cfg,g,c,emit):
    locs=set(cfg['localizer']['train_locations'][fold]+cfg['localizer']['qual_locations'][fold]);chosen=[r for r in data['candidates'] if r['location'] in locs];indices=[r['index'] for r in chosen];bank=np.lib.format.open_memmap(run/f'FIT_masks_fold_{fold}.npy',mode='w+',dtype=np.uint8,shape=(len(chosen),32,32));last=None;arr=None
    for j,row in enumerate(chosen):
        im=row['image_id']
        if im!=last:
            mask=pixel.raster(data['annotations'][im],data['images'][im]);arr=np.asarray(mask,dtype=np.uint8).copy();mask.close();last=im
        bank[j]=target(arr,data['contexts'][row['index']]);g.take('localizer_mask_rows')
    bank.flush();g.take('localizer_mask_bytes',int(bank.nbytes));emit(f'FIT_reference_index_fold_{fold}.json',dict(indices=indices,locations=sorted(locs,key=int),shape=list(bank.shape),sha256=c.sha(run/f'FIT_masks_fold_{fold}.npy',g.check)))
    return dict(indices=indices,lookup={i:j for j,i in enumerate(indices)},values=bank)

def infer(backend,model,cache,indices,path,counter,cfg,g):
    result=np.lib.format.open_memmap(path,mode='w+',dtype=np.float32,shape=(len(indices),32,32))
    for start in range(0,len(indices),cfg['spatial']['batch_size']):
        ids=indices[start:start+cfg['spatial']['batch_size']];out=backend.predict(model,np.asarray(cache[ids]));g.take('max_semantic_batches');g.take(counter,len(ids));result[start:start+len(ids)]=out
    result.flush();return result

def component(p,y,constant):
    result=pixel.component(p,y,constant)
    result['zero_Brier']=float(np.mean(np.asarray(y,dtype=float)**2));result['one_Brier']=float(np.mean((1-np.asarray(y,dtype=float))**2));return result

def aggregate(records,locations):
    keys=['Brier','constant_Brier','zero_Brier','one_Brier','Dice','constant_Dice','all_background_Dice','all_foreground_Dice'];images=[]
    for im in sorted({r['image_id'] for r in records}):
        rows=[r for r in records if r['image_id']==im];fg=[r for r in rows if r['has_reference_foreground']]
        images.append(dict(image_id=im,location=rows[0]['location'],contexts=len(rows),foreground_contexts=len(fg),**{k:float(np.mean([r[k] for r in rows])) for k in keys},foreground={k:None if not fg else float(np.mean([r[k] for r in fg])) for k in ['Dice','constant_Dice','all_background_Dice','all_foreground_Dice']}))
    sites=[]
    for loc in locations:
        rows=[r for r in images if r['location']==loc];fg=[r for r in rows if r['foreground_contexts']]
        sites.append(dict(location=loc,images=len(rows),**{k:None if not rows else float(np.mean([r[k] for r in rows])) for k in keys},foreground={k:None if not fg else float(np.mean([r['foreground'][k] for r in fg])) for k in ['Dice','constant_Dice','all_background_Dice','all_foreground_Dice']}))
    return images,sites

def qualification(backend,model,data,bank,run,cfg,g,c,emit,fold):
    locs=cfg['localizer']['qual_locations'][fold];chosen=[r for r in data['candidates'] if r['location'] in locs]
    if len(chosen)!=cfg['localizer']['qual_rows'][fold]:raise ValueError('qualification scope')
    maps=infer(backend,model,data['rgb'],[r['index'] for r in chosen],run/f'qualification_maps_fold_{fold}.npy','localizer_qualification_rows',cfg,g);records=[]
    for j,row in enumerate(chosen):records.append(dict(index=row['index'],image_id=row['image_id'],location=row['location'],**component(maps[j],bank['values'][bank['lookup'][row['index']]],model['train_prevalence'])))
    images,sites=aggregate(records,locs);missing=any(v['foreground']['Dice'] is None for v in sites)
    means={k:float(np.mean([r[k] for r in sites])) for k in ['Brier','constant_Brier','zero_Brier','one_Brier']};dice={k:None if missing else float(np.mean([r['foreground'][k] for r in sites])) for k in ['Dice','constant_Dice','all_background_Dice','all_foreground_Dice']};margin=cfg['localizer']['qualification']['margin'];brier_gain=min(means[k] for k in ['constant_Brier','zero_Brier','one_Brier'])-means['Brier'];dice_gain=None if missing else dice['Dice']-max(dice[k] for k in ['constant_Dice','all_background_Dice','all_foreground_Dice']);passed=not missing and brier_gain>margin and dice_gain>margin
    g.take('localizer_qualifications');payload=dict(fold=fold,qualified=passed,status='inconclusive' if missing else 'pass' if passed else 'negative',locations=locs,contexts=records,images=images,sites=sites,macro=means,foreground_macro=dice,Brier_gain=brier_gain,foreground_Dice_gain=dice_gain,model_state_digest=model['state_digest'],map_sha256=c.sha(run/f'qualification_maps_fold_{fold}.npy',g.check),GT_in_prediction=False,used_for_training=False)
    emit(f'qualification_fold_{fold}.json',payload);return payload,maps,chosen

def describe(h,original,corrected,ctx):
    h=np.asarray(h,dtype=np.float64)
    if h.shape!=(32,32) or not np.isfinite(h).all() or (h<0).any() or (h>1).any():raise ValueError('regional map')
    x1,y1,x2,y2=ctx;xs=np.linspace(x1,x2,33);ys=np.linspace(y1,y2,33);mass=float(h.sum());areas=[];inside=[];z=[]
    for b in [original,corrected]:
        b=box(b);wx=np.maximum(0,np.minimum(xs[1:],b[2])-np.maximum(xs[:-1],b[0]))/(xs[1:]-xs[:-1]);wy=np.maximum(0,np.minimum(ys[1:],b[3])-np.maximum(ys[:-1],b[1]))/(ys[1:]-ys[:-1]);cov=wy[:,None]*wx[None,:];areas.append(float(cov.mean()));inside.append(float(np.sum(h*cov)));z.append(0. if mass<=1e-12 else inside[-1]/mass-areas[-1])
    return dict(values=[z[1],(z[1]-z[0])/2],context=ctx,mass=mass,areas=areas,inside_mass=inside,concentrations=z,degenerate='zero_mass' if mass<=1e-12 else None)
