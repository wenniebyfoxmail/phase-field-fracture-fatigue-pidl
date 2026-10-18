"""Small supervised region head; array storage and own-FIT-only label construction."""
import collections,math
import numpy as np
from PIL import Image,ImageDraw

def raster(rows,record):
    mask=Image.new('L',(record['width'],record['height']),0);draw=ImageDraw.Draw(mask)
    for row in rows:
        if row['category'] in ['Alligator Crack','Transverse Crack']:draw.polygon([tuple(p) for p in row['polygon']],fill=1)
    return mask

def centers(context,size):
    x1,y1,x2,y2=context
    return np.floor(x1+(np.arange(size)+.5)*(x2-x1)/size).astype(int),np.floor(y1+(np.arange(size)+.5)*(y2-y1)/size).astype(int)

def labels(mask,context,indices=None):
    xs,ys=centers(context,14)
    if indices is not None:xs=xs[indices];ys=ys[indices]
    xs=np.clip(xs,0,mask.width-1);ys=np.clip(ys,0,mask.height-1);a=np.asarray(mask,dtype=np.uint8)
    return a[np.ix_(ys,xs)]

def fit(cache,contexts,candidates,annotations,images,locations,cfg,guard,ridge):
    locs=set(locations);chosen=[row for row in candidates if row['location'] in locs];n=len(chosen)*16
    if set(annotations)!={row['image_id'] for row in chosen}:raise ValueError('pixel annotation scope must equal own FIT images')
    X=np.empty((n,40),dtype=np.float64);Y=np.empty(n,dtype=np.float64);sites=[];ims=[];parents=[];offset=0;previous=None;mask=None
    for row in chosen:
        im=row['image_id']
        if im!=previous:
            if mask is not None:mask.close()
            mask=raster(annotations[im],images[im]);previous=im
        i=row['index'];idx=cfg['spatial']['sample_indices'];X[offset:offset+16]=cache[i][:,idx,:][:,:,idx].transpose(1,2,0).reshape(16,40)
        Y[offset:offset+16]=labels(mask,contexts[i],idx).reshape(16);sites.extend([row['location']]*16);ims.extend([im]*16);parents.extend([row['parent_id']]*16);offset+=16;guard.check()
    if mask is not None:mask.close()
    if set(Y)!={0.,1.}:raise ValueError('pixel supervision needs both region classes')
    counts=collections.Counter(zip(Y,sites,ims,parents));groups=collections.defaultdict(set);images_by=collections.defaultdict(set);parents_by=collections.defaultdict(set)
    for y,loc,im,parent in counts:groups[y].add(loc);images_by[y,loc].add(im);parents_by[y,loc,im].add(parent)
    weights=np.asarray([1/(2*len(groups[y])*len(images_by[y,loc])*len(parents_by[y,loc,im])*counts[y,loc,im,parent]) for y,loc,im,parent in zip(Y,sites,ims,parents)],dtype=np.float64)
    guard.take('pixel_head_fits');guard.take('linear_solves');guard.take('pixel_training_sample_rows',n)
    head=ridge(X,Y,weights,cfg['spatial']['pixel_ridge'],cfg['spatial']['pixel_numerical_tolerance'])
    support=[dict(value=int(y),cells=int(np.count_nonzero(Y==y)),locations=sorted(groups[y],key=int),images=len({im for yy,im in zip(Y,ims) if yy==y}),contexts=len({parent for yy,parent in zip(Y,parents) if yy==y}),weight_mass=float(weights[Y==y].sum())) for y in [0.,1.]]
    return dict(**head,strata_support=support,coefficient_count=41,training_locations=list(locations),training_images=len(annotations),training_contexts=len(chosen),sample_rows=n,positive_samples=int(Y.sum()),negative_samples=int(n-Y.sum()),FIT_foreground_rate=float(Y.mean()),frozen_backbone=True,reference='polygon region envelope, not visible crack width')

def predict(model,features):
    x=np.asarray(features,dtype=np.float32);b=np.asarray(model['coefficients'],dtype=np.float64)
    if not model['verified'] or b.shape!=(41,) or x.ndim!=4 or tuple(x.shape[1:])!=(40,14,14) or not np.isfinite(x).all():raise ValueError('pixel prediction shape/numerics')
    values=b[0]+np.einsum('bkij,k->bij',x,b[1:],optimize=False)
    if not np.isfinite(values).all():raise ValueError('nonfinite pixel prediction')
    return np.clip(values,0,1).astype(np.float32)

def component(values,target,constant):
    p=np.asarray(values,dtype=np.float64);y=np.asarray(target,dtype=np.uint8);binary=p>=.5
    def dice(pred):
        tp=int(np.count_nonzero(pred&(y>0)));fp=int(np.count_nonzero(pred&(y==0)));fn=int(np.count_nonzero((~pred)&(y>0)));den=2*tp+fp+fn
        return 1. if den==0 else 2*tp/den
    tp=int(np.count_nonzero(binary&(y>0)));fp=int(np.count_nonzero(binary&(y==0)));fn=int(np.count_nonzero((~binary)&(y>0)))
    return dict(TP=tp,FP=fp,FN=fn,Brier=float(np.mean((p-y)**2)),constant_Brier=float(np.mean((constant-y)**2)),Dice=dice(binary),constant_Dice=dice(np.full(y.shape,constant>=.5)),all_background_Dice=dice(np.zeros_like(y,dtype=bool)),all_foreground_Dice=dice(np.ones_like(y,dtype=bool)),has_reference_foreground=bool(y.any()))

def evaluate(data,models,maps,cfg,guard):
    # Caller must already have frozen all models and OOF predictions.
    records=[]
    for k,held in enumerate(cfg['held_groups']):
        previous=None;mask=None
        for row in data['candidates']:
            if row['location'] not in held:continue
            im=row['image_id']
            if im!=previous:
                if mask is not None:mask.close()
                mask=raster(data['annotations'][im],data['images'][im]);previous=im
            i=row['index'];y=labels(mask,data['contexts'][i]);guard.take('pixel_evaluation_rows')
            records.append(dict(index=i,parent_id=row['parent_id'],image_id=im,location=row['location'],fold=k,**component(maps[k][i],y,models[k]['FIT_foreground_rate'])))
        if mask is not None:mask.close()
    keys=['Brier','constant_Brier','Dice','constant_Dice','all_background_Dice','all_foreground_Dice'];by=collections.defaultdict(list)
    for row in records:by[row['image_id']].append(row)
    image_rows=[]
    for im,rows in by.items():
        fg=[row for row in rows if row['has_reference_foreground']]
        image_rows.append(dict(image_id=im,location=rows[0]['location'],contexts=len(rows),foreground_contexts=len(fg),foreground_context_Dice=None if not fg else float(np.mean([v['Dice'] for v in fg])),**{key:float(np.mean([r[key] for r in rows])) for key in keys}))
    sites=[]
    for loc in cfg['locations']:
        rows=[r for r in image_rows if r['location']==loc];fg=[r['foreground_context_Dice'] for r in rows if r['foreground_context_Dice'] is not None]
        sites.append(dict(location=loc,images=len(rows),foreground_context_Dice=None if not fg else float(np.mean(fg)),**{key:float(np.mean([r[key] for r in rows])) for key in keys}))
    return dict(scope='frozen OOF pixel component only; overlapping contexts not independent',threshold=.5,comparison='>=',empty_empty_Dice=1,used_to_choose_model_or_gate=False,contexts=records,images=image_rows,locations=sites,macro={key:float(np.mean([r[key] for r in sites])) for key in keys},pooled_repeated_context_counts={key:sum(r[key] for r in records) for key in ['TP','FP','FN']})
