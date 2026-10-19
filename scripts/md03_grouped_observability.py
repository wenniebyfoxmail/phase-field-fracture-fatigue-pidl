"""Fixed D3 group: immutable dark baseline, saved motion, two-sided evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import numpy as np

from md03_fixed_triplet import BASE, WORK, guard
from md01_cached_stage_forecast import sha, save
from md03_motion_residual_diagnostic import warp_valid
from md01_geometric_guide_transfer import transfer
from md01_frame_geometry import extract

GROUP=BASE/'D3_grouped_20261019'
PRIOR=BASE/'D3_20261019/R001'
PROTOCOL=WORK/'docs/research/S03/S03-E049-MD03/grouped_observability_protocol.md'
OFF=np.array([24.,48.,72.])
HALF=15
RADIUS=4
XS=2750+8*np.arange(-19,20)
YS=1900+16*np.arange(-10,11)
NAMES=['motion_only','illumination','smooth_strain','illumination_smooth',
       'opening_1','opening_2','opening_4','opening_2_illum_smooth']


def now():return datetime.now(timezone.utc).isoformat()


def match(a,b,x,y):
    patch=a[y-HALF:y+HALF+1,x-HALF:x+HALF+1]
    search=b[y-HALF-RADIUS:y+HALF+RADIUS+1,x-HALF-RADIUS:x+HALF+RADIUS+1]
    if patch.shape!=(31,31) or search.shape!=(39,39):raise ValueError('Invalid fixed template support')
    if np.std(patch)<=1e-12:
        return dict(dx=np.nan,dy=np.nan,ncc=np.nan,censored=True,constant=True)
    scores=cv2.matchTemplate(search.astype(np.float32),patch.astype(np.float32),cv2.TM_CCOEFF_NORMED)
    peaks=np.argwhere(scores==scores.max())
    py,px=min(peaks.tolist(),key=lambda p:((p[1]-RADIUS)**2+(p[0]-RADIUS)**2,p[0],p[1]))
    def refine(v):
        den=float(v[0]-2*v[1]+v[2])
        return float(np.clip(.5*(v[0]-v[2])/den,-.5,.5)) if den<0 else 0.
    dx=float(px-RADIUS);dy=float(py-RADIUS)
    if 0<px<8:dx+=refine(scores[py,px-1:px+2])
    if 0<py<8:dy+=refine(scores[py-1:py+2,px])
    return dict(dx=dx,dy=dy,ncc=float(scores[py,px]),
                censored=bool(px in (0,8) or py in (0,8)),constant=False)


def intercept(values):
    v=np.asarray(values,float)
    slope=(v[2]-v[0])/48.
    at0=float(v.mean()-48*slope)
    rms=float(np.sqrt(np.mean((v-(at0+slope*OFF))**2)))
    return at0,rms


def fields(a,b,raw_a,oldmask,band):
    assert a.shape==b.shape==raw_a.shape==oldmask.shape==(360,500)
    cache={};shape=(len(YS),len(XS))
    out={k:np.full(shape,np.nan) for k in ('jump_x','jump_y','gap_contrast','ncc_min',
              'fit_rms','old_fraction','motion_abs','raw_abs')}
    censored=np.zeros(shape,bool);constant=np.zeros(shape,bool)
    d=a.astype(float)-b.astype(float);raw=raw_a.astype(float)-b.astype(float)
    def get(x,y):
        key=int(x),int(y)
        if key not in cache:cache[key]=match(a,b,*key)
        return cache[key]
    for iy,yn in enumerate(YS):
        y=int(yn-band[1])
        for ix,xn in enumerate(XS):
            x=int(xn-band[0]);left=[get(x-int(o),y) for o in OFF];right=[get(x+int(o),y) for o in OFF]
            probes=left+right
            censored[iy,ix]=any(p['censored'] for p in probes)
            constant[iy,ix]=any(p['constant'] for p in probes)
            lx,lr=intercept([p['dx'] for p in left]);rx,rr=intercept([p['dx'] for p in right])
            ly,_=intercept([p['dy'] for p in left]);ry,_=intercept([p['dy'] for p in right])
            out['jump_x'][iy,ix]=rx-lx;out['jump_y'][iy,ix]=ry-ly
            out['fit_rms'][iy,ix]=max(lr,rr);out['ncc_min'][iy,ix]=min(p['ncc'] for p in probes)
            center=np.s_[y-15:y+16,x-2:x+3]
            flank=.5*(d[y-15:y+16,x-13:x-5].mean()+d[y-15:y+16,x+6:x+14].mean())
            out['gap_contrast'][iy,ix]=float(d[center].mean()-flank)
            out['old_fraction'][iy,ix]=float(oldmask[center].mean())
            out['motion_abs'][iy,ix]=float(abs(d[center]).mean())
            out['raw_abs'][iy,ix]=float(abs(raw[center]).mean())
    out.update(censored=censored,constant=constant,valid=~(censored|constant),xs=XS,ys=YS)
    return out,len(cache)


def describe(v):
    v=np.asarray(v,float);v=v[np.isfinite(v)]
    if not len(v):return dict(n=0,median=None,p10=None,p90=None)
    return dict(n=len(v),median=float(np.median(v)),p10=float(np.percentile(v,10)),p90=float(np.percentile(v,90)))


def summarize(f):
    col=int(np.flatnonzero(XS==2750)[0]);valid=f['valid'][:,col]
    return dict(probes_total=int(f['valid'].size),assessable_probes=int(f['valid'].sum()),
         censored_probes=int(f['censored'].sum()),constant_texture_probes=int(f['constant'].sum()),
         center_x=2750,center_assessable=int(valid.sum()),center_total=len(YS),
         center={k:describe(f[k][:,col][valid]) for k in
                 ('jump_x','jump_y','gap_contrast','ncc_min','fit_rms','old_fraction','motion_abs','raw_abs')},
         spatial_ranges_are_not_confidence_intervals=True,no_crack_classification_threshold=True)


def control(base,roi,gap=0.,strain=0.,illum=False):
    yy,xx=np.indices(base.shape,dtype=np.float32)
    d=xx+roi[0]-2750
    src_x=2750+(d-np.where(d>=0,gap/2,-gap/2))/(1+strain)-roi[0]
    if gap or strain:
        b=cv2.remap(base.astype(np.float32),src_x.astype(np.float32),yy,cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    else:b=base.copy()
    if gap:
        gap_columns=(xx+roi[0]>=2750-gap/2)&(xx+roi[0]<2750+gap/2)
        b[gap_columns]=0
    if illum:b=1.05*b+8
    return np.rint(np.clip(b,0,255)).astype(np.uint8)


def tests():
    for slope,offset in [(0.,2.),(.01,-.3),(-.02,1.2)]:
        v=offset+slope*OFF;a,r=intercept(v)
        assert abs(a-offset)<1e-10 and r<1e-10
    rng=np.random.default_rng(20261019);a=rng.integers(0,256,(120,220)).astype(np.float32)
    b=cv2.warpAffine(a,np.array([[1.,0,2.],[0,1.,-1.]]),(220,120))
    m=match(a,b,100,60)
    assert abs(m['dx']-2)<.1 and abs(m['dy']+1)<.1 and not m['censored']
    same=match(a,a,100,60);assert abs(same['dx'])<.1 and abs(same['dy'])<.1
    zero=match(np.zeros_like(a),np.zeros_like(a),100,60);assert zero['constant']
    roi=[2640,1840,2860,1960]
    assert np.all(control(a,roi,gap=2)[:,109:111]==0)
    print('Separate-side linear-strain cancellation, integer-shift NCC, identity/constant and gap support tests passed.')


def run(out):
    start=time.monotonic();cpu=time.process_time()
    selection=json.loads((BASE/'R000_selection/selection_lock.json').read_text());guard(selection)
    protected=dict(selection['protected'])
    for p in BASE.rglob('*'):
        if p.is_file() and GROUP not in p.parents:protected[str(p)]=sha(p)
    for p in (Path(__file__),PROTOCOL,WORK/'scripts/md03_motion_residual_diagnostic.py',
              WORK/'scripts/md03_fixed_triplet.py'):protected[str(p)]=sha(p)
    cfg=json.loads((BASE/'history_support.json').read_text());band,roi=cfg['band'],cfg['roi']
    spec=json.loads((PRIOR/'input_specification.json').read_text())
    x0,y0,x1,y1=np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
    sl=np.s_[y0:y1,x0:x1]
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(execution='running',started_utc=now(),host=socket.gethostname(),pid=os.getpid(),
        command=sys.argv,runtime=sys.executable,commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
        dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
        code_sha256=sha(__file__),protocol_sha256=sha(PROTOCOL),global_transform_refits=0,
        source_downloads=0,trained_models=0,new_real_masks=0,new_forecast_scores=0)
    save(out/'start_receipt.json',receipt);save(out/'protected_inputs.json',protected)
    save(out/'specification.json',dict(roi=roi,band=band,xs=XS.tolist(),ys=YS.tolist(),
         offsets=OFF.tolist(),patch=31,search_radius=4,control_order=NAMES,
         protocol_sha256=sha(PROTOCOL),no_data_adaptive_thresholds=True))
    def check():
        if max(time.monotonic()-start,time.process_time()-cpu)>300:raise TimeoutError('300s grouped analysis cap')
        if any(sha(p)!=v for p,v in protected.items()):raise ValueError('Protected old input changed')
    try:
        rows=[]
        for a,b in [(89,132),(132,175)]:
            with np.load(PRIOR/f'{a}_{b}/residual_arrays.npz') as z:
                old={k:z[k] for k in z.files}
            assert old['common_valid'].all()
            f,nmatch=fields(old['warped_a'],old['b'],old['a'],old['old_mask_b'],band)
            name=f'real_{a}_{b}';case=out/name;case.mkdir()
            np.savez_compressed(case/'evidence.npz',**f,b_image=old['b'],reference=old['warped_a'],
                  motion_residual=old['d1'],old_mask=old['old_mask_b'])
            row=dict(case=name,role='design' if a==89 else 'exposed_development',known_gap=None,
                     cached_texture_matches=nmatch,**summarize(f));save(case/'summary.json',row);rows.append(row)
            check()
        with np.load(BASE/'R002_history/89/arrays.npz') as z:source_roi=z['roi_rgb'][:,:,0].astype(np.float32)
        matrix=np.array(spec['matrices'][0]);base,valid=warp_valid(source_roi,matrix)
        with np.load(PRIOR/'89_132/residual_arrays.npz') as z:assert np.array_equal(base[sl],z['warped_a'])
        assert valid[sl].all()
        strain=float(np.hypot(matrix[0,0],matrix[1,0])-1)
        combinations=[(0,0,False),(0,0,True),(0,strain,False),(0,strain,True),
                      (1,0,False),(2,0,False),(4,0,False),(2,strain,True)]
        for name,(gap,eps,light) in zip(NAMES,combinations):
            full=control(base,roi,gap,eps,light);rgb=np.repeat(full[:,:,None],3,axis=2)
            support,diag,_,_=transfer(rgb,cfg['support'],roi,band)
            mask,_,_=extract(rgb,support,roi);oldmask=mask[sl]
            f,nmatch=fields(base[sl],full[sl],source_roi[sl],oldmask,band)
            case=out/name;case.mkdir()
            np.savez_compressed(case/'evidence.npz',**f,b_image=full[sl],reference=base[sl],
                  motion_residual=base[sl]-full[sl].astype(float),old_mask=oldmask)
            row=dict(case=name,role='synthetic_control_from89',known_gap=gap,strain=eps,illumination=light,
                     cached_texture_matches=nmatch,old_synthetic_observer_diagnostic=diag,**summarize(f))
            save(case/'summary.json',row);rows.append(row);check()
        summary=dict(rows=rows,protected_files=len(protected),old_observer_scores_halfdepth_unchanged=True,
            real_images=[89,132,175],target175_development_only=True,grouped_question='observability, not forecast scores',
            no_new_classification_threshold=True,design_strain=strain)
        save(out/'summary.json',summary);check()
        receipt.update(execution='succeeded',retrieval='verified_local',protected_files_verified=len(protected),
                       real_pairs=2,synthetic_controls=8)
        print(json.dumps([dict(case=r['case'],gap=r['known_gap'],valid=r['center_assessable'],
                   J=r['center']['jump_x'],Q=r['center']['gap_contrast']) for r in rows],indent=2))
    except Exception as error:receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        save(out/'receipt.json',receipt)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['self-test','run']);p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.phase=='self-test':tests()
    else:run(args.output)
