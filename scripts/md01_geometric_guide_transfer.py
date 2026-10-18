"""E045 image-only guide transfer, unchanged extraction thresholds; no forecasts."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import distance_transform_edt

from md01_cached_stage_forecast import ROOT, WORK, sha, save, table
from md01_frame_geometry import read_frame, extract
from md01_support_mass_forecast import observe

OLD=ROOT/'local_archive/experiments/S03-E044-MD01/runs'
PROTOCOL=WORK/'docs/research/S03/S03-E045-MD01/experiment.md'
CONTROL=[4380,1700,4510,1950]
OMISSION=[4020,1700,4210,1770]
SHADOW=[4250,1700,4335,1770]


def path_dp(reward,allowed,max_step):
    """Exact bounded-step longest path; deterministic straight-first tie order."""
    h,w=reward.shape
    steps=[0]+[s for d in range(1,max_step+1) for s in (-d,d)]
    score=np.where(allowed[0],reward[0],-np.inf)
    back=np.zeros((h,w),np.int16)
    for y in range(1,h):
        options=np.full((len(steps),w),-np.inf)
        for i,d in enumerate(steps):
            if d==0:options[i]=score
            elif d>0:options[i,d:]=score[:-d]-abs(d)
            else:options[i,:d]=score[-d:]-abs(d)
        choice=options.argmax(axis=0)
        score=np.where(allowed[y],options[choice,np.arange(w)]+reward[y],-np.inf)
        back[y]=np.asarray(steps)[choice]
    end=int(np.argmax(score))
    if not np.isfinite(score[end]):raise ValueError('No feasible guide path')
    x=np.zeros(h,int);x[-1]=end
    for y in range(h-1,0,-1):x[y-1]=x[y]-back[y,x[y]]
    assert allowed[np.arange(h),x].all() and np.all(abs(np.diff(x))<=max_step)
    return x,float(score[end])


def transfer(rgb,support,roi,band):
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float32)
    bg=cv2.boxFilter(gray,-1,(101,101),borderType=cv2.BORDER_REFLECT)
    excluded=np.zeros(gray.shape,np.uint8)
    for poly in support['exclude_polygons']:
        cv2.fillPoly(excluded,[np.rint(np.array(poly)-np.array(roi[:2])).astype(np.int32)],1)
    eligible=(gray<=100)&(bg-gray>=20)&~excluded.astype(bool)
    points=np.array(support['coarse_guide_xy'],float)
    step=int(np.ceil(2*np.max(abs(np.diff(points[:,0])/np.diff(points[:,1])))))
    ys=np.arange(band[1]-60,band[3]+60+1)
    ylocal=ys-roi[1];xs=np.arange(rgb.shape[1])+roi[0]
    oldx=np.interp(ys,points[:,1],points[:,0])
    allowed=abs(xs[None,:]-oldx[:,None])<=240
    reward=np.minimum(distance_transform_edt(eligible)[ylocal],60)
    changed=copy.deepcopy(support)
    if not np.any(reward[allowed]>0):
        return changed,dict(fallback=True,reason='no_eligible_dark_geometry',max_step=step),eligible,np.column_stack((oldx,ys))
    path,score=path_dp(reward,allowed,step)
    native=np.column_stack((path+roi[0],ys))
    changed['coarse_guide_xy']=points[points[:,1]<ys[0]].tolist()+native.tolist()+points[points[:,1]>ys[-1]].tolist()
    diag=dict(fallback=False,max_step=step,search_radius=240,path_score=score,
              guide_shift_mean_abs_px=float(np.mean(abs(native[:,0]-oldx))),
              guide_shift_max_abs_px=float(np.max(abs(native[:,0]-oldx))),
              path_on_eligible_fraction=float(np.mean(eligible[ylocal,path])),path_rows=len(path))
    return changed,diag,eligible,native


def tests():
    reward=np.zeros((30,50));reward[:,20]=3;allowed=np.ones_like(reward,bool)
    x,_=path_dp(reward,allowed,3);assert np.all(x==20)
    reward[10:12,35:45]=4;x,_=path_dp(reward,allowed,3);assert np.all(x==20)
    reward=np.zeros((30,50))
    for y in range(30):reward[y,10+y//3]=4
    x,_=path_dp(reward,allowed,3);assert np.max(abs(x-(10+np.arange(30)//3)))==0
    allowed[:,:8]=False;reward[:]=0;x,_=path_dp(reward,allowed,3);assert np.all(x==8)
    # DP optimum agrees with exhaustive path enumeration on a tiny deterministic grid.
    import itertools
    r=np.array([[1.,0,2],[0,3,0],[2,0,1]]);a=np.ones_like(r,bool);p,v=path_dp(r,a,1)
    scores=[sum(r[y,q[y]] for y in range(3))-sum(abs(q[y]-q[y-1]) for y in (1,2))
            for q in itertools.product(range(3),repeat=3) if all(abs(q[y]-q[y-1])<=1 for y in (1,2))]
    assert v==max(scores)
    print('DP straight/isolated-blob/sloping/ties/bounds and exhaustive-optimum tests passed; no real data.')


def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    oldlock=OLD/'S03-E044-MD01-R000/selection_lock.json';j=json.loads(oldlock.read_text())
    protected=dict(j['protected_inputs'])
    for p in sorted(OLD.rglob('*')):
        if p.is_file():protected[str(p)]=sha(p)
    for p in (PROTOCOL,Path(__file__),WORK/'scripts/md01_frame_geometry.py',WORK/'scripts/md01_support_mass_forecast.py'):
        protected[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in protected.items())
    lock=dict(protocol='E045-geometry-guide-v1',frames=j['frames'],roi=j['roi'],band=j['band'],
              original_support=j['new_stage_support'],protected_inputs=protected,
              control=CONTROL,stage26_omission=OMISSION,stage26_shadow_risk=SHADOW,
              prepared_utc=datetime.now(timezone.utc).isoformat(),no_new_candidate_computed=True)
    save(out/'input_lock.json',lock)
    save(out/'prepare_receipt.json',dict(execution='succeeded',input_lock_sha256=sha(out/'input_lock.json'),
                                        protected_files=len(protected),no_new_candidate_computed=True))
    print('Frozen geometry transfer and review regions; protected files:',len(protected))


def run(lockpath,out):
    start,cpu=time.monotonic(),time.process_time();out.mkdir(parents=True,exist_ok=False)
    lock=json.loads(lockpath.read_text());protected=lock['protected_inputs']
    receipt=dict(execution='running',started_utc=datetime.now(timezone.utc).isoformat(),
                 host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,command=sys.argv,
                 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
                 dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
                 lock_sha256=sha(lockpath))
    save(out/'run_start_receipt.json',receipt)
    def guard():assert all(sha(p)==h for p,h in protected.items()) and sha(lockpath)==receipt['lock_sha256']
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>90:raise TimeoutError('90s single-candidate cap')
    roi,band=lock['roi'],lock['band']
    def sl(box):
        x0,y0,x1,y1=np.array(box)-np.array([roi[0],roi[1],roi[0],roi[1]])
        return np.s_[y0:y1,x0:x1]
    try:
        guard();rows=[];regions=[]
        for f in lock['frames']:
            budget();s=f['stage'];case=out/f'step{s}';case.mkdir()
            rgb=read_frame(f,roi);old,ex,_=extract(rgb,lock['original_support'],roi)
            with np.load(OLD/f'S03-E044-MD01-R001/W{s}/observation_arrays.npz') as z:
                assert np.array_equal(old,z['mask']) and np.array_equal(ex,z['excluded'])
            support,diag,eligible,path=transfer(rgb,lock['original_support'],roi,band)
            save(case/'guide_before_extraction.json',dict(support=support,diagnostic=diag,
                    algorithm_inputs='current image gates/geometry only; no prediction/score file parsed'))
            new,exnew,_=extract(rgb,support,roi)
            assert np.array_equal(ex,exnew) and not np.any(new&~eligible)
            added=new&~old;removed=old&~new;oldv,_=observe(old[sl(band)]);newv,_=observe(new[sl(band)])
            seed=np.zeros(old.shape,np.uint8)
            p=np.rint(np.array(lock['original_support']['coarse_guide_xy'])-np.array(roi[:2])).astype(np.int32)
            cv2.polylines(seed,[p],False,1,thickness=1);dist=distance_transform_edt(~seed.astype(bool))
            r=dict(stage=s,old_area=oldv['area'],new_area=newv['area'],added=int(added[sl(band)].sum()),
                   removed=int(removed[sl(band)].sum()),old_support=oldv['support'],new_support=newv['support'],
                   old_row_mass=oldv['mass'],new_row_mass=newv['mass'],
                   new_pixels_outside_old_corridor=int((new&(dist>60))[sl(band)].sum()),
                   **diag)
            boxes={'right_background_control':lock['control']}
            if s==26:boxes.update(upper_omission_review=lock['stage26_omission'],shadow_risk_review=lock['stage26_shadow_risk'])
            rr=[]
            for name,box in boxes.items():
                z=sl(box);rr.append(dict(stage=s,region=name,box=box,old_pixels=int(old[z].sum()),
                                        new_pixels=int(new[z].sum()),added=int(added[z].sum()),removed=int(removed[z].sum()),
                                        reference_role='source-informed mixed-pixel review box; not truth'))
            regions.extend(rr);rows.append(r)
            np.savez_compressed(case/'comparison_arrays.npz',old_mask=old,new_mask=new,excluded=ex,
                                added=added,removed=removed,band_rgb=rgb[sl(band)],guide_path_native=path)
            save(case/'summary.json',dict(measures=r,regions=rr,old_observation=oldv,new_observation=newv))
        summary=dict(role='one image-geometry candidate,3 already-exposed frames, no forecast scoring',
                     rows=rows,regions=regions,all_baselines_exact=True,exclusions_unchanged=True,
                     old_halfdepth_and_scores_unchanged=True,region_counts_are_not_accuracy=True,
                     no_predictive_error_selection=True)
        save(out/'summary.json',summary);table(out/'measures.csv',rows)
        # CSV serialises box as a descriptive list; exact coordinates also saved inJSON.
        table(out/'review_regions.csv',regions);guard();budget()
        receipt.update(execution='succeeded',retrieval='verified_local',protected_files_verified=len(protected),
                       baseline_reconstructions_exact=3,candidate_extractions=3)
        print(json.dumps(summary,indent=2))
    except Exception as e:receipt.update(execution='failed',error=repr(e));raise
    finally:
        receipt.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat());save(out/'run_receipt.json',receipt)


def plot(source,lockpath,out):
    out.mkdir(parents=True,exist_ok=False)
    j=json.loads((source/'summary.json').read_text());lock=json.loads(lockpath.read_text());roi,band=lock['roi'],lock['band']
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
    def crop(a,box):
        x0,y0,x1,y1=np.array(box)-np.array([roi[0],roi[1],roi[0],roi[1]])
        return a[y0:y1,x0:x1]
    def overlay(ax,rgb,mask,color):
        ax.imshow(rgb);o=np.zeros((*mask.shape,4));o[mask]=(*color,.75);ax.imshow(o)
    prov=f'\n## Data provenance\nE045 R001: {source}. Inputlock: {lockpath}. Renderer scripts/md01_geometric_guide_transfer.py. '
    limits=('\n## Limitations and claim boundary\nAlready-viewed development images, no independent truth or shadow classifier. '
            'New guide uses currentimage, not a futureprediction. Shadows/pores can formeligible darkridges; reviewROI counts are NOT TP/FP/recall. '
            'Nativepixel geometry only; unchanged half-depth and oldscores. No forecasterror parsed or rescoring.\n')
    def export(fig,stem,text):
        fig.savefig(out/f'{stem}.png',dpi=300);fig.savefig(out/f'{stem}.pdf');plt.close(fig)
        (out/f'{stem}.md').write_text(text)
    for row in j['rows']:
        s=row['stage']
        with np.load(source/f'step{s}/comparison_arrays.npz') as z:
            rgb=z['band_rgb'];old=crop(z['old_mask'],band);new=crop(z['new_mask'],band)
            added=crop(z['added'],band);removed=crop(z['removed'],band);path=z['guide_path_native']
        fig,axes=plt.subplots(4,1,figsize=(10,12.2),layout='constrained')
        axes[0].imshow(rgb);axes[0].set_title(f'A  Step{s} original fixed image band')
        overlay(axes[1],rgb,old,(0,.55,.8));axes[1].set_title(f"B  Frozen E044 guide | {row['old_area']} candidate px²")
        overlay(axes[2],rgb,new,(.35,.25,.65));axes[2].set_title(f"C  Image-geometric guide | {row['new_area']} candidate px²")
        p=path[(path[:,1]>=band[1])&(path[:,1]<band[3])];axes[2].plot(p[:,0]-band[0],p[:,1]-band[1],color='#E69F00',ls='--',lw=1)
        overlay(axes[3],rgb,added,(.9,.6,0));o=np.zeros((*removed.shape,4));o[removed]=(0,.6,.5,.85);axes[3].imshow(o)
        axes[3].set_title(f"D  Orange added {row['added']} | green removed {row['removed']} (not truth labels)")
        for ax in axes:ax.set_axis_off()
        fig.suptitle(f'E045 | Step{s}: same thresholds/exclusions, one fixed guide-transfer rule\nPixel candidates, not physical crack width or validated segmentation',fontsize=13)
        export(fig,f'F01_step{s}_guide_comparison',f'# How to read: Step{s} frozen vs geometric guide\n\n## Figure question\nWhere did moving only the guide add or remove candidates?\n'+prov+
               '\n## Visual grammar and panels\nA originalRGB, B saved/reproducedE044cyanmask, C geometricguidepurplemask andorange dashedDPcentreline, '
               'D orangeadditions/greenremovals. Same nativeband[3900,1700,4600,1950], same scale, no favourablecropselection. '
               'Colourdoesnotindicatetruth.\n\n## Key numerical takeaway\n'+json.dumps(row,indent=2)+limits)
    with np.load(source/'step26/comparison_arrays.npz') as z:
        old=z['old_mask'];new=z['new_mask'];rgb_band=z['band_rgb']
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for i,(name,box) in enumerate([('Upper omission review',lock['stage26_omission']),('Background / shadow-risk review',lock['stage26_shadow_risk'])]):
        x0,y0,x1,y1=np.array(box)-np.array([band[0],band[1],band[0],band[1]])
        rgb=rgb_band[y0:y1,x0:x1]
        axes[i,0].imshow(rgb);overlay(axes[i,1],rgb,crop(old,box),(0,.55,.8));overlay(axes[i,2],rgb,crop(new,box),(.35,.25,.65))
        rr=next(r for r in j['regions'] if r['stage']==26 and r['region']==('upper_omission_review' if i==0 else 'shadow_risk_review'))
        axes[i,0].set_title(name+'\nSource only')
        axes[i,1].set_title(f"Frozen: {rr['old_pixels']} candidate px²")
        axes[i,2].set_title(f"Transferred: {rr['new_pixels']} candidate px²")
        for ax in axes[i]:ax.set_axis_off()
    fig.suptitle('E045 Step26 | Pre-fixed source-informed review boxes, NOT pixel truth\nTop: possible recovery; bottom: background/shadow-risk tradeoff',fontsize=13)
    export(fig,'F02_step26_review_regions','# How to read: stage26 fixed omission and shadow-risk review regions\n\n## Figure question\nDoes the same rule restore visible uppertrace while changing nearby suspicious background?\n'+prov+
           '\n## Visual grammar and panel guide\nTop fixednativebox[4020,1700,4210,1770], bottom[4250,1700,4335,1770]. '
           'Columns source /frozen cyan /transferred purple. Regioncounts describe mixedpixels, not independent crackannotation. '
           'These source-informed rectangles predate candidatecomputation but were chosen afterE044sources alreadyviewed; no blindclaim.\n'
           '\n## Key numerical takeaway\n'+json.dumps([r for r in j['regions'] if r['stage']==26],indent=2)+limits)
    save(out/'render_receipt.json',dict(execution='succeeded',source_summary_sha256=sha(source/'summary.json'),
         renderer_sha256=sha(Path(__file__)),figures=4,numerical_rerun=False,
         output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['self-test','prepare','run','plot'])
    p.add_argument('--output',type=Path);p.add_argument('--source',type=Path);p.add_argument('--lock',type=Path);a=p.parse_args()
    if a.mode=='self-test':tests()
    elif a.mode=='prepare':prepare(a.output)
    elif a.mode=='run':run(a.lock,a.output)
    else:plot(a.source,a.lock,a.output)
