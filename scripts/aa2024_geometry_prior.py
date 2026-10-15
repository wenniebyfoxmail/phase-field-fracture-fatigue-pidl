#!/usr/bin/env python3
"""E016 training-opening-defined prior; no claim of independently measured tips."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import numpy as np
from aa2024_triplet_structure import read_member, parse_nodemap, EXPECTED_SIZE, EXPECTED_MD5
from aa2024_patch_mechanics import rectangular_mesh, solve_patch, sample_regular_mesh
from aa2024_boundary_basis import sha, load, bindings, write_json, headers, error, check_budget
from aa2024_rigid_observable import quotient_residual

DEPS=('aa2024_boundary_basis.py','aa2024_triplet_structure.py','aa2024_patch_mechanics.py','aa2024_rigid_observable.py')
X=.9*np.arange(-26,27)
ARMS=('old','proxy','intact','secant')
PREP=('preparation.json','prepared.npz','geometry_audit.json','training_geometry.npz')
FIT=('fit.json','frozen_predictions.npz','solved_fields.npz')

def sources():return {n:sha(Path(__file__).with_name(n)) for n in DEPS}

def completed(root,mode,names):
    r=json.loads((root/'execution_receipt.json').read_text())
    if (r.get('mode')!=mode or r.get('execution_status')!='succeeded' or
        r.get('runner_sha256')!=sha(__file__) or r.get('dependencies_sha256')!=sources()):
        raise ValueError('completion/source mismatch')
    if any(r.get('artifacts_sha256',{}).get(n)!=sha(root/n) for n in names):
        raise ValueError('completion artifact mismatch')
    return r

def identity(h,s):
    for k,v in (('current_stage_index',s),('reference_stage_index',1),('cycles',Decimal('292018.5'))):
        if Decimal(h[k])!=v:raise ValueError('stage/reference/cycle mismatch')
    f=float(h['force'])
    if not np.isfinite(f):raise ValueError('nonfinite force')
    return f

def affine_at(xy,du,points,*,ids=None,same_side=False,diagnostics=None):
    ids=np.arange(1,len(xy)+1) if ids is None else np.asarray(ids)
    if (xy.shape!=(len(ids),2) or du.shape!=(len(ids),2) or len(set(ids))!=len(ids)
        or not np.isfinite(xy).all() or not np.isfinite(du).all()):
        raise ValueError('interpolation input identity/finite/shape')
    values=np.full((len(points),2),np.nan);dist=np.full(len(points),np.inf);ranks=[]
    for i,p in enumerate(points):
        pool=np.flatnonzero(xy[:,1]>0 if p[1]>0 else xy[:,1]<0) if same_side else np.arange(len(xy))
        d2=np.sum((xy[pool]-p)**2,axis=1)
        # Exact computed XY-distance ties are resolved by original facet ID.
        neighbors=pool[np.lexsort((ids[pool],d2))[:4]]
        note=dict(query_xy_mm=p.tolist(),neighbor_ids=ids[neighbors].tolist(),rank=0,
            condition_number=None,coefficients=None,coefficient_L1=None,coefficient_L2=None)
        rank=0
        if len(neighbors)==4:
            dist[i]=float(np.sqrt(np.sum((xy[neighbors[-1]]-p)**2)))
            A=np.column_stack((np.ones(4),xy[neighbors]-p))
            c,_,rank,svals=np.linalg.lstsq(A,du[neighbors],rcond=1e-12)
            note['rank']=int(rank)
            if rank==3:
                weights=np.linalg.lstsq(A.T,np.array([1.,0.,0.]),rcond=1e-12)[0]
                if not np.isfinite(c).all() or not np.isfinite(weights).all():
                    raise ValueError('nonfinite affine coefficients')
                note.update(condition_number=float(svals[0]/svals[-1]),coefficients=weights.tolist(),
                    coefficient_L1=float(np.abs(weights).sum()),coefficient_L2=float(np.linalg.norm(weights)))
                if dist[i]<=2:values[i]=c[0]
        ranks.append(int(rank));note['fourth_distance_mm']=float(dist[i]) if np.isfinite(dist[i]) else None
        note['supported']=bool(np.isfinite(values[i]).all())
        if diagnostics is not None:diagnostics.append(note)
    return values,dist,ranks

def halfheight(x,y,*,allow_missing=False):
    finite=np.isfinite(y)
    if not finite.any() or (not allow_missing and not finite.all()):raise ValueError('primary profile unsupported')
    i=int(np.argmax(np.where(finite,y,-np.inf)));peak=float(y[i]);level=peak/2
    if peak<=0:raise ValueError('nonpositive corrected opening peak')
    l=r=i
    while l>0 and finite[l-1] and y[l-1]>=level:l-=1
    while r<len(y)-1 and finite[r+1] and y[r+1]>=level:r+=1
    if l==0 or r==len(y)-1:raise ValueError('halfheight crossings absent')
    if not finite[l-1] or not finite[r+1]:raise ValueError('halfheight interrupted by missing support')
    left=float(x[l-1]+(level-y[l-1])*(x[l]-x[l-1])/(y[l]-y[l-1]))
    right=float(x[r]+(level-y[r])*(x[r+1]-x[r])/(y[r+1]-y[r]))
    if not -16.2<=left<right<=16.2:raise ValueError('proxy outside fixed interior margin')
    above=y>=level
    lobes=int(above[0])+int(np.sum(above[1:]&~above[:-1]))
    return dict(left_mm=left,right_mm=right,peak_x_mm=float(x[i]),peak_mm=peak,
        halfheight_mm=level,lobes_above_halfheight=lobes,
        left_bracket_mm=[float(x[l-1]),float(x[l])],right_bracket_mm=[float(x[r]),float(x[r+1])],
        center_mm=(left+right)/2,length_mm=right-left,
        center_change_from_old_mm=(left+right)/2+1.5,length_change_from_old_mm=right-left-15,
        left_change_from_old_mm=left+9,right_change_from_old_mm=right-6,
        meaning='opening_localisation_prior_NOT_measured_crack_tips')

def profile(xy,du,b,*,ids=None):
    p=np.column_stack((np.tile(X,2),np.repeat([b,-b],len(X))))
    interpolation=[]
    v,dist,ranks=affine_at(xy,du,p,ids=ids,same_side=True,diagnostics=interpolation);upper,lower=np.split(v,2)
    opening=upper[:,1]-lower[:,1];support=np.isfinite(opening)
    tail=(np.abs(X)>=18)&support
    coeff=None;corrected=np.full(len(X),np.nan);cross=None;issue=None;trend=None;tail_residual=None
    primary=b==3.6
    eligible=(support.all() if primary else (np.any(tail&(X<0)) and np.any(tail&(X>0))))
    if eligible and tail.sum()>=2:
        A=np.column_stack((np.ones(tail.sum()),X[tail]))
        c,_,rank,_=np.linalg.lstsq(A,opening[tail],rcond=1e-12)
        if rank==2:
            coeff=c.tolist();trend=c[0]+c[1]*X;corrected=opening-trend
            tail_residual=(opening[tail]-trend[tail]).tolist()
            try:cross=halfheight(X,corrected,allow_missing=not primary)
            except ValueError as e:issue=str(e)
        else:issue='tail affine rank'
    else:issue='primary support incomplete' if primary else 'outer trend requires supported locations on both sides'
    finite_list=lambda a:[float(v) if np.isfinite(v) else None for v in a]
    return dict(gauge_mm=b,x_mm=X.tolist(),opening_mm=finite_list(opening),
        corrected_mm=finite_list(corrected),background_coefficients=coeff,
        outer_trend_mm=None if trend is None else finite_list(trend),outer_indices=np.flatnonzero(tail).tolist(),
        outer_residual_mm=tail_residual,interpolation=interpolation,
        supported=support.tolist(),fourth_distances_mm=finite_list(dist),ranks=ranks,
        crossings=cross,issue=issue)

def plane_diagnostic(xyz,du3):
    A=np.column_stack((np.ones(len(xyz)),xyz[:,:2]))
    c,_,rank,_=np.linalg.lstsq(A,xyz[:,2],rcond=1e-12)
    if rank!=3 or not np.isfinite(c).all():raise ValueError('reference plane rank/finite')
    normal=np.array([-c[1],-c[2],1.]);normal/=np.linalg.norm(normal)
    residual=(xyz[:,2]-np.einsum('ij,j->i',A,c))*normal[2]
    return dict(region='common_training_scoring_ROI_absx<16.2_absy<7.2_positive_area',
        reference_coordinates='stage13_serialized_reference_XYZ',
        plane_fit='equal_weight_OLS_z_on_1_x_y_not_orthogonal_best_fit',
        displacement_increment='stage14_UVW_minus_stage13_UVW',
        displacement_component_order=['delta_U','delta_V','delta_W'],
        points=len(xyz),plane_coefficients=c.tolist(),unit_normal_xyz=normal.tolist(),
        tilt_degrees=float(np.degrees(np.arctan(np.hypot(c[1],c[2])))),
        OLS_plane_orthogonal_RMS_mm=float(np.sqrt(np.mean(residual**2))),
        OLS_plane_orthogonal_max_abs_mm=float(np.abs(residual).max()),
        raw_displacement_increment_RMS_UVW_mm=np.sqrt(np.mean(du3**2,axis=0)).tolist())

def prior_coverage(mesh,tri,d):
    p=mesh[tri];area=((p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0]))/2
    avg=d[tri].mean(1);g=(1-avg)**2+1e-6
    return dict(discrete_prior_integral_mm2=float(np.sum(area*avg)),
        degradation_area_integral_mm2=float(np.sum(area*g)),
        area_mean_local_stiffness_multiplier=float(np.sum(area*g)/area.sum()),
        area_mean_local_degradation_fraction=float(1-np.sum(area*g)/((1+1e-6)*area.sum())),
        meaning='artificial_mesh_prior_and_local_multiplier_NOT_crack_area_or_effective_patch_stiffness')

def segment_prior(xy,left,right):
    distance=np.hypot(np.maximum(np.maximum(left-xy[:,0],xy[:,0]-right),0),xy[:,1])
    return np.exp(-distance/1.5)

def finite_predictions(a):
    """Reject invalid frozen numerics before the held response parser is reachable."""
    n=len(a['ids'])
    if np.shape(a['alpha'])!=() or not np.isfinite(a['alpha']) or a['alpha']<=1:
        raise ValueError('nonfinite/invalid load extrapolation alpha')
    if a['xy'].shape!=(n,2) or a['weights'].shape!=(n,) or np.any(a['weights']<=0):
        raise ValueError('prediction support shape/weight mismatch')
    for k in ('xy','weights','u13')+ARMS:
        if (k not in ('weights',) and a[k].shape!=(n,2)) or not np.isfinite(a[k]).all():
            raise ValueError('nonfinite/invalid frozen prediction '+k)

def area_weights(text,xy,finite):
    lines=[s for s in text.splitlines() if s.strip()]
    if [s.strip() for s in lines[0].split(';')]!=['Type','Element #','Node 1','Node 2','Node 3']:
        raise ValueError('connection schema')
    arr=np.asarray([[int(v.strip()) for v in s.split(';')] for s in lines[1:]],dtype=int)
    if arr.ndim!=2 or arr.shape[1]!=5 or np.any(arr[:,0]!=3):raise ValueError('Type3 required')
    t=arr[:,2:];t=t[~np.all(t==-1,axis=1)]
    if np.any(t<0) or np.any(t>=len(xy)) or any(len(set(row))!=3 for row in t):
        raise ValueError('invalid nonpadding connection')
    if len({tuple(sorted(row)) for row in t})!=len(t):raise ValueError('duplicate triangle')
    t=t[np.all(finite[t],axis=1)];p=xy[t]
    area=np.abs((p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0]))/2
    if np.any(area<=1e-12):raise ValueError('source degeneracy')
    return np.bincount(t.ravel(),weights=np.repeat(area/3,3),minlength=len(xy))

def prepare(archive,out):
    if archive.stat().st_size!=EXPECTED_SIZE:raise ValueError('archive size mismatch')
    h=hashlib.md5()
    with archive.open('rb') as f:
        for v in iter(lambda:f.read(8388608),b''):h.update(v)
    if h.hexdigest()!=EXPECTED_MD5:raise ValueError('archive identity mismatch')
    with zipfile.ZipFile(archive) as z:
        texts=[read_member(z,f'global_3d_dic/Nodemaps/global_3d_dic_results_1_{s}.txt') for s in (13,14,15)]
        connection=read_member(z,'global_3d_dic/Connections/global_3d_dic_results_1_13_connections.txt')
    forces=[identity(headers(t),s) for t,s in zip(texts,(13,14,15))]
    if not 0<forces[0]<forces[1]<forces[2]:raise ValueError('load order')
    alpha=(forces[2]-forces[0])/(forces[1]-forces[0])
    if not np.isfinite(alpha) or alpha<=1:raise ValueError('nonfinite/invalid load extrapolation alpha')
    a,b=[parse_nodemap(t,allow_displacements=True) for t in texts[:2]]
    ids=a['ids'];finite=a['finite_xyz']&b['finite_xyz']&a['finite_u']&b['finite_u']
    if not np.array_equal(ids,b['ids']) or not np.array_equal(ids,np.arange(1,len(ids)+1)):
        raise ValueError('training ID/order')
    if finite.sum()<10:raise ValueError('insufficient finite training')
    xyz=a['xyz'][finite];coordinate_difference=np.abs(xyz-b['xyz'][finite]).max(0)
    if np.any(coordinate_difference>1e-6):raise ValueError('reference coordinates mismatch')
    # Stage13 alone defines every spatial operator; stage14 XYZ only checks identity.
    xy=a['xyz'][:,:2];du3=b['u']-a['u'];du=du3[:,:2]
    w=area_weights(connection,xy,finite)
    obs=finite&(np.abs(xy[:,0])<16.2)&(np.abs(xy[:,1])<7.2)&(w>0)
    if obs.sum()<10:raise ValueError('insufficient common observations')
    profiles={str(band):profile(xy[finite],du[finite],band,ids=ids[finite]) for band in (3.6,1.8,2.7)}
    audit=dict(cycle='292018.5',stages=[13,14],profiles=profiles,
        coordinate_max_abs_difference_mm=coordinate_difference.tolist(),joint_finite=int(finite.sum()),
        plane=plane_diagnostic(a['xyz'][obs],du3[obs]),
        training_headers=[a['headers'],b['headers']],frame='stage13_serialized_reference_xy_no_header_reapplication',
        assumptions='y0/xaxis retained; plane stress/small strain/static damage not validated')
    np.savez_compressed(out/'training_geometry.npz',xy=xy[finite],xyz=xyz,du=du3[finite],ids=ids[finite])
    write_json(out/'geometry_audit.json',audit)
    primary=profiles['3.6']
    if primary['crossings'] is None:raise ValueError('primary geometry admission: '+str(primary['issue']))
    mesh,tri,bd=rectangular_mesh();bc_notes=[]
    bc,dist,ranks=affine_at(xy[finite],du[finite],mesh[bd],ids=ids[finite],diagnostics=bc_notes)
    if not np.isfinite(bc).all():raise ValueError('BC support/rank')
    cross=primary['crossings']
    old=segment_prior(mesh,-9.,6.);proxy=segment_prior(mesh,cross['left_mm'],cross['right_mm'])
    np.savez_compressed(out/'prepared.npz',ids=ids[obs],xy=xy[obs],weights=w[obs],
        train_v=du[obs],u13=a['u'][obs,:2],alpha=alpha,
        mesh=mesh,tri=tri,boundary=bd,bc=bc,old=old,proxy=proxy)
    write_json(out/'preparation.json',dict(cycle='292018.5',reference=1,forces=forces,
        observations=int(obs.sum()),weight_area_mm2=float(w[obs].sum()),proxy_geometry=cross,
        boundary_fourth_max_mm=float(dist.max()),boundary_ranks=ranks,boundary_interpolation=bc_notes,
        prior_coverage={k:prior_coverage(mesh,tri,d) for k,d in (('old',old),('proxy',proxy))},
        held_member_sha256=hashlib.sha256(texts[2].encode('utf-8')).hexdigest(),
        training_member_sha256=[hashlib.sha256(t.encode('utf-8')).hexdigest() for t in texts[:2]],
        archive=str(archive),archive_size=EXPECTED_SIZE,archive_md5=EXPECTED_MD5))

def fit(root,out,start):
    completed(root,'prepare',PREP);a=load(root/'prepared.npz');meta=json.loads((root/'preparation.json').read_text())
    if np.shape(a['alpha'])!=() or not np.isfinite(a['alpha']) or a['alpha']<=1:
        raise ValueError('nonfinite/invalid load extrapolation alpha')
    pred={k:a[k] for k in ('ids','xy','weights','u13','alpha')};fields={};records={}
    for k in ('old','proxy','intact'):
        check_budget(start);d=np.zeros(len(a['mesh'])) if k=='intact' else a[k]
        u,res=solve_patch(a['mesh'],a['tri'],a['boundary'],a['bc'],d);check_budget(start)
        sample=sample_regular_mesh(u,a['xy']);fields[k]=u;fields[k+'_sampled']=sample;fields[k+'_damage']=d
        if not np.isfinite(u).all() or not np.isfinite(res) or res>1e-8 or not np.isfinite(sample).all():
            raise ValueError('nonfinite solve/sample or residual failure')
        pred[k]=a['alpha']*sample
        records[k]=dict(relative_residual=res,train_MAE_mm=error(a['xy'],sample-a['train_v'],a['weights']))
    pred['secant']=a['alpha']*a['train_v'];check_budget(start)
    finite_predictions(pred)
    np.savez_compressed(out/'frozen_predictions.npz',**pred);np.savez_compressed(out/'solved_fields.npz',**fields)
    write_json(out/'fit.json',dict(status='four_predictions_frozen_before_held_response',
        records=records,source_prepare=bindings(root,PREP),cycle=meta['cycle'],
        held_member_sha256=meta['held_member_sha256'],held_force=meta['forces'][2],proxy_geometry=meta['proxy_geometry']))
    check_budget(start)

def validate(root,high,out):
    completed(root,'fit',FIT);meta=json.loads((root/'fit.json').read_text())
    if meta['status']!='four_predictions_frozen_before_held_response':raise ValueError('not frozen')
    a=load(root/'frozen_predictions.npz');finite_predictions(a)
    if high.stat().st_size>16000000 or sha(high)!=meta['held_member_sha256']:raise ValueError('held identity mismatch')
    h=parse_nodemap(high.read_text(),allow_displacements=True)
    if identity(h['headers'],15)!=meta['held_force']:raise ValueError('held force mismatch')
    lookup={int(v):i for i,v in enumerate(h['ids'])}
    if any(int(v) not in lookup for v in a['ids']):raise ValueError('held ID absent')
    idx=np.array([lookup[int(v)] for v in a['ids']])
    valid=np.isfinite(h['xyz'][idx,:2]).all(1)&np.isfinite(h['u'][idx,:2]).all(1)
    if valid.sum()<10 or not np.allclose(h['xyz'][idx[valid],:2],a['xy'][valid],atol=1e-6,rtol=0):
        raise ValueError('held support/reference mismatch')
    xy,w=a['xy'][valid],a['weights'][valid];target=h['u'][idx[valid],:2]-a['u13'][valid]
    data=dict(ids=a['ids'][valid],xy=xy,weights=w,target=target);metrics={}
    for k in ARMS:
        r=quotient_residual(xy,a[k][valid]-target,w);data[k]=a[k][valid];data[k+'_residual']=r
        metrics[k]=float(np.sum(w*np.linalg.norm(r,axis=1))/w.sum())
    delta=metrics['old']-metrics['proxy']
    np.savez_compressed(out/'validation_fields.npz',**data)
    write_json(out/'metrics.json',dict(MAE_mm=metrics,primary_old_minus_proxy_mm=delta,
        descriptive_outcome='improves' if delta>0 else 'equal' if delta==0 else 'worsens',
        source_fit=bindings(root,FIT),target_member_sha256=meta['held_member_sha256'],
        eligible=int(valid.sum()),frozen_support=len(valid),missing_ids=a['ids'][~valid].tolist(),
        area_coverage=float(w.sum()/a['weights'].sum()),scope='opening-defined prior procedure_NOT_true_tip_recovery'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','fit','validate'))
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--high-member',type=Path);p.add_argument('--source-commit',required=True);p.add_argument('--run-id',required=True)
    args=p.parse_args()
    if args.mode=='fit' and socket.gethostname()!='GPUServer8':raise ValueError('Taobo-only real solve')
    args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    r=dict(mode=args.mode,run_id=args.run_id,source_commit_declared=args.source_commit,hostname=socket.gethostname(),
        pid=os.getpid(),command=sys.argv,start_utc=datetime.now(timezone.utc).isoformat(),runner_sha256=sha(__file__),
        dependencies_sha256=sources(),numpy_version=np.__version__,execution_status='running',
        thread_environment={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')})
    try:
        if args.mode=='prepare':prepare(args.input,args.output)
        elif args.mode=='fit':
            completed(args.input,'prepare',PREP);r['input_bindings']=bindings(args.input,PREP);fit(args.input,args.output,start)
        else:
            if args.high_member is None:raise ValueError('high member required')
            completed(args.input,'fit',FIT);r['input_bindings']=bindings(args.input,FIT);validate(args.input,args.high_member,args.output)
        if args.mode=='fit':check_budget(start)
        r['execution_status']='succeeded'
    except Exception as e:r['execution_status']='failed';r['error']=str(e);raise
    finally:
        hashes={p.name:sha(p) for p in args.output.iterdir() if p.is_file() and p.name!='execution_receipt.json'}
        elapsed=time.monotonic()-start;late=args.mode=='fit' and r['execution_status']=='succeeded' and elapsed>=600
        if late:r['execution_status']='failed';r['error']='soft600s finalization overrun; no held access'
        r.update(elapsed_seconds=elapsed,end_utc=datetime.now(timezone.utc).isoformat(),artifacts_sha256=hashes)
        write_json(args.output/'execution_receipt.json',r)
        if late:raise TimeoutError(r['error'])

if __name__=='__main__':main()
