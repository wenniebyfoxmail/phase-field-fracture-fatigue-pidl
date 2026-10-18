"""Fixed E026 translations, input validation, and saved-array metrics. No torch."""
import hashlib
import json
import numpy as np

TEST_SHIFTS = np.array([[0,0],[0,8],[8,0],[8,8]], np.int64)


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()


def shift_rgb(a, shift):
    return np.roll(a, tuple(4*np.asarray(shift)), axis=(-2,-1))


def shift_mask(a, shift):
    return np.roll(a, tuple(shift), axis=(-2,-1))


def flow(seed):
    held = {tuple(s) for s in TEST_SHIFTS}
    allowed = np.array([(y,x) for y in range(32) for x in range(32) if (y,x) not in held],np.int64)
    rng = np.random.default_rng(seed)
    return np.stack([allowed[rng.permutation(len(allowed))[:128]] for _ in range(8)],axis=1)


def position_prior(masks, shifts):
    sums = np.zeros((32,32), np.float64)
    for step in shifts:
        for y,s in zip(masks,step,strict=True):
            sums += shift_mask(y,s)
    return (sums / (len(shifts)*len(masks))).astype(np.float32)


def shared_seam_mask(shift):
    """One mask for correct/phase/identity; excludes all their seams and border."""
    keep = np.ones((32,32),bool)
    keep[:4] = keep[-4:] = False
    keep[:,:4] = keep[:,-4:] = False
    for s in [np.asarray(shift), (np.asarray(shift)+16)%32]:
        for axis,c in enumerate(s):
            # Cyclic distance also covers the seam at0 without a clipped half-band.
            distance = np.minimum((np.arange(32)-c)%32,(c-np.arange(32))%32)
            if axis==0:keep[distance<=2,:]=False
            else:keep[:,distance<=2]=False
    return keep


def validate_packet(packet, meta, lock):
    if set(packet)!= {'rgb','masks','source_indices','fold_indices'}:
        raise ValueError('packet member inventory')
    rgb,y,src,fold = (packet[k] for k in ['rgb','masks','source_indices','fold_indices'])
    if rgb.shape!=(16,3,128,128) or rgb.dtype!=np.uint8 or y.shape!=(16,32,32) or y.dtype!=np.uint8:
        raise ValueError('packet shapes/dtypes')
    if src.shape!=(16,) or fold.shape!=(3,8) or src.dtype!=np.int64 or fold.dtype!=np.int64:
        raise ValueError('packet indices')
    if len(set(src.tolist()))!=16 or set(np.unique(y).tolist())!={0,1} or not np.all((y.sum((1,2))>0)&(y.sum((1,2))<1024)):
        raise ValueError('packet support')
    if not np.all((fold>=0)&(fold<16)) or any(len(set(ids.tolist()))!=8 for ids in fold):
        raise ValueError('fold scope')
    if [src[ids].tolist() for ids in fold]!=lock['fold_source_indices'] or meta['fold_source_indices']!=lock['fold_source_indices']:
        raise ValueError('original control identity')
    if len(meta['rows'])!=16 or len({r['image_id'] for r in meta['rows']})!=16 or not np.array_equal(fold[0],fold[2]):
        raise ValueError('unique/repeated images')
    for j,r in enumerate(meta['rows']):
        if r['source_index']!=int(src[j]) or hashlib.sha256(rgb[j].tobytes()).hexdigest()!=r['rgb_sha256'] or hashlib.sha256(y[j].tobytes()).hexdigest()!=r['mask_sha256']:
            raise ValueError('control array identity')


def component(p,y,keep=None):
    p = np.asarray(p,np.float64)
    y = np.asarray(y,np.uint8)
    if p.shape!=y.shape or not np.isfinite(p).all() or (p<0).any() or (p>1).any():
        raise ValueError('prediction shape/range')
    if keep is not None:p,y=p[keep],y[keep]
    if not len(p.ravel()):return None
    binary=p>=.5; fg=y>0
    tp=int((binary&fg).sum()); fp=int((binary&~fg).sum()); fn=int((~binary&fg).sum()); den=2*tp+fp+fn
    return dict(Brier=float(np.mean((p-y)**2)),Dice=1. if den==0 else 2*tp/den,
                TP=tp,FP=fp,FN=fn,foreground_cells=int(fg.sum()),pixels=int(y.size),
                soft_foreground=None if not fg.any() else float(p[fg].mean()),
                soft_background=None if fg.all() else float(p[~fg].mean()),maximum=float(p.max()))


def evaluate(maps,masks,prior,margin=1e-6):
    if maps.shape!=(3,4,8,32,32):raise ValueError('576map contract')
    records=[];p=float(masks.mean());baseline_maps=[np.full((32,32),p),np.zeros((32,32)),np.ones((32,32)),prior]
    names=['correct','phase_mismatch','identity_mismatch','prevalence','zero','one','position_prior']
    for phase,s in enumerate(TEST_SHIFTS):
        keep=shared_seam_mask(s)
        for j,y0 in enumerate(masks):
            y=shift_mask(y0,s)
            for name,pred in zip(names,[*maps[:,phase,j],*baseline_maps],strict=True):
                full=component(pred,y);inner=component(pred,y,keep)
                # Aux comparisons use identical pixels and require reference dual class.
                if inner is not None and not 0<inner['foreground_cells']<inner['pixels']:inner=None
                records.append(dict(phase=phase,context=j,kind=name,full=full,shared_seam_excluded=inner))
    averages={}
    for name in names:
        rr=[r for r in records if r['kind']==name]
        averages[name]={k:float(np.mean([r['full'][k] for r in rr])) for k in ['Brier','Dice']}
        aux=[r['shared_seam_excluded'] for r in rr if r['shared_seam_excluded'] is not None]
        averages[name]['shared_seam_excluded']=dict(context_phase_rows=len(aux),**{k:None if not aux else float(np.mean([r[k] for r in aux])) for k in ['Brier','Dice']})
        averages[name]['unshifted']={k:float(np.mean([r['full'][k] for r in rr if r['phase']==0])) for k in ['Brier','Dice']}
    correct=averages['correct'];base=[averages[n] for n in names[3:]]
    gains=dict(Brier_gain=min(r['Brier'] for r in base)-correct['Brier'],
               Dice_gain=correct['Dice']-max(r['Dice'] for r in base),
               phase_pairing_gain=averages['phase_mismatch']['Brier']-correct['Brier'])
    parts={k:bool(v>margin) for k,v in gains.items()};passed=all(parts.values())
    level='L2' if passed else 'L1' if parts['Brier_gain'] or parts['phase_pairing_gain'] else 'L0'
    return dict(averages=averages,gains=gains,components_pass=parts,passed=passed,level=level,records=records)
