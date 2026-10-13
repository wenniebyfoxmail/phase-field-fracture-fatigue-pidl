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
from scipy.spatial import cKDTree
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

def affine_at(xy,du,points):
    dist,idx=cKDTree(xy).query(points,k=4)
    values=np.full((len(points),2),np.nan);ranks=[]
    for i,(p,neighbors) in enumerate(zip(points,idx)):
        A=np.column_stack((np.ones(4),xy[neighbors]-p))
        c,_,rank,_=np.linalg.lstsq(A,du[neighbors],rcond=1e-12);ranks.append(int(rank))
        if rank==3 and dist[i,3]<=2:values[i]=c[0]
    return values,dist[:,3],ranks

def halfheight(x,y):
    if not np.isfinite(y).all():raise ValueError('primary profile unsupported')
    i=int(np.argmax(y));peak=float(y[i]);level=peak/2
    if peak<=0:raise ValueError('nonpositive corrected opening peak')
    l=r=i
    while l>0 and y[l-1]>=level:l-=1
    while r<len(y)-1 and y[r+1]>=level:r+=1
    if l==0 or r==len(y)-1:raise ValueError('halfheight crossings absent')
    left=float(x[l-1]+(level-y[l-1])*(x[l]-x[l-1])/(y[l]-y[l-1]))
    right=float(x[r]+(level-y[r])*(x[r+1]-x[r])/(y[r+1]-y[r]))
    if not -16.2<=left<right<=16.2:raise ValueError('proxy outside fixed interior margin')
    above=y>=level
    lobes=int(above[0])+int(np.sum(above[1:]&~above[:-1]))
    return dict(left_mm=left,right_mm=right,peak_x_mm=float(x[i]),peak_mm=peak,
        halfheight_mm=level,lobes_above_halfheight=lobes,
        meaning='opening_localisation_prior_NOT_measured_crack_tips')

def profile(xy,du,b):
    p=np.column_stack((np.tile(X,2),np.repeat([b,-b],len(X))))
    v,dist,ranks=affine_at(xy,du,p);upper,lower=np.split(v,2)
    opening=upper[:,1]-lower[:,1];support=np.isfinite(opening)
    tail=(np.abs(X)>=18)&support
    coeff=None;corrected=np.full(len(X),np.nan);cross=None;issue=None
    if tail.sum()>=4:
        A=np.column_stack((np.ones(tail.sum()),X[tail]))
        c,_,rank,_=np.linalg.lstsq(A,opening[tail],rcond=1e-12)
        if rank==2:
            coeff=c.tolist();corrected=opening-c[0]-c[1]*X
            try:cross=halfheight(X,corrected)
            except ValueError as e:issue=str(e)
        else:issue='tail affine rank'
    else:issue='insufficient outer background locations'
    finite_list=lambda a:[float(v) if np.isfinite(v) else None for v in a]
    return dict(gauge_mm=b,x_mm=X.tolist(),opening_mm=finite_list(opening),
        corrected_mm=finite_list(corrected),background_coefficients=coeff,
        supported=support.tolist(),fourth_distances_mm=dist.tolist(),ranks=ranks,
        crossings=cross,issue=issue)

def segment_prior(xy,left,right):
    distance=np.hypot(np.maximum(np.maximum(left-xy[:,0],xy[:,0]-right),0),xy[:,1])
    return np.exp(-distance/1.5)

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
    a,b=[parse_nodemap(t,allow_displacements=True) for t in texts[:2]]
    ids=a['ids'];finite=a['finite_xyz']&b['finite_xyz']&a['finite_u']&b['finite_u']
    if not np.array_equal(ids,b['ids']) or not np.array_equal(ids,np.arange(1,len(ids)+1)):
        raise ValueError('training ID/order')
    if finite.sum()<10:raise ValueError('insufficient finite training')
    xyz=a['xyz'][finite];coordinate_difference=np.abs(xyz-b['xyz'][finite]).max(0)
    if np.any(coordinate_difference>1e-6):raise ValueError('reference coordinates mismatch')
    xy=a['xyz'][:,:2];du3=b['u']-a['u'];du=du3[:,:2]
    w=area_weights(connection,xy,finite)
    obs=finite&(np.abs(xy[:,0])<16.2)&(np.abs(xy[:,1])<7.2)&(w>0)
    if obs.sum()<10:raise ValueError('insufficient common observations')
    profiles={str(band):profile(xy[finite],du[finite],band) for band in (3.6,1.8,2.7)}
    A=np.column_stack((np.ones(len(xyz)),xyz[:,:2]))
    c,_,rank,_=np.linalg.lstsq(A,xyz[:,2],rcond=1e-12)
    if rank!=3:raise ValueError('reference plane rank')
    zres=xyz[:,2]-np.einsum('ij,j->i',A,c)
    audit=dict(cycle='292018.5',stages=[13,14],profiles=profiles,
        coordinate_max_abs_difference_mm=coordinate_difference.tolist(),joint_finite=int(finite.sum()),
        plane_coefficients=c.tolist(),reference_z_plane_RMS_mm=float(np.sqrt(np.mean(zres**2))),
        increment_RMS_xyz_mm=np.sqrt(np.mean(du3[finite]**2,axis=0)).tolist(),
        training_headers=[a['headers'],b['headers']],frame='serialized_reference_xy_no_header_reapplication',
        assumptions='y0/xaxis retained; plane stress/small strain/static damage not validated')
    np.savez_compressed(out/'training_geometry.npz',xy=xy[finite],du=du3[finite],ids=ids[finite])
    write_json(out/'geometry_audit.json',audit)
    primary=profiles['3.6']
    if primary['crossings'] is None:raise ValueError('primary geometry admission: '+str(primary['issue']))
    mesh,tri,bd=rectangular_mesh();bc,dist,ranks=affine_at(xy[finite],du[finite],mesh[bd])
    if not np.isfinite(bc).all():raise ValueError('BC support/rank')
    cross=primary['crossings']
    np.savez_compressed(out/'prepared.npz',ids=ids[obs],xy=xy[obs],weights=w[obs],
        train_v=du[obs],u13=a['u'][obs,:2],alpha=(forces[2]-forces[0])/(forces[1]-forces[0]),
        mesh=mesh,tri=tri,boundary=bd,bc=bc,old=segment_prior(mesh,-9.,6.),
        proxy=segment_prior(mesh,cross['left_mm'],cross['right_mm']))
    write_json(out/'preparation.json',dict(cycle='292018.5',reference=1,forces=forces,
        observations=int(obs.sum()),weight_area_mm2=float(w[obs].sum()),proxy_geometry=cross,
        boundary_fourth_max_mm=float(dist.max()),boundary_ranks=ranks,
        held_member_sha256=hashlib.sha256(texts[2].encode('utf-8')).hexdigest(),
        training_member_sha256=[hashlib.sha256(t.encode('utf-8')).hexdigest() for t in texts[:2]],
        archive=str(archive),archive_size=EXPECTED_SIZE,archive_md5=EXPECTED_MD5))

def fit(root,out,start):
    completed(root,'prepare',PREP);a=load(root/'prepared.npz');meta=json.loads((root/'preparation.json').read_text())
    pred={k:a[k] for k in ('ids','xy','weights','u13','alpha')};fields={};records={}
    for k in ('old','proxy','intact'):
        check_budget(start);d=np.zeros(len(a['mesh'])) if k=='intact' else a[k]
        u,res=solve_patch(a['mesh'],a['tri'],a['boundary'],a['bc'],d);check_budget(start)
        sample=sample_regular_mesh(u,a['xy']);fields[k]=u;fields[k+'_sampled']=sample;fields[k+'_damage']=d
        pred[k]=a['alpha']*sample
        records[k]=dict(relative_residual=res,train_MAE_mm=error(a['xy'],sample-a['train_v'],a['weights']))
    pred['secant']=a['alpha']*a['train_v'];check_budget(start)
    np.savez_compressed(out/'frozen_predictions.npz',**pred);np.savez_compressed(out/'solved_fields.npz',**fields)
    write_json(out/'fit.json',dict(status='four_predictions_frozen_before_held_response',
        records=records,source_prepare=bindings(root,PREP),cycle=meta['cycle'],
        held_member_sha256=meta['held_member_sha256'],held_force=meta['forces'][2],proxy_geometry=meta['proxy_geometry']))
    check_budget(start)

def validate(root,high,out):
    completed(root,'fit',FIT);meta=json.loads((root/'fit.json').read_text())
    if meta['status']!='four_predictions_frozen_before_held_response':raise ValueError('not frozen')
    if high.stat().st_size>16000000 or sha(high)!=meta['held_member_sha256']:raise ValueError('held identity mismatch')
    h=parse_nodemap(high.read_text(),allow_displacements=True)
    if identity(h['headers'],15)!=meta['held_force']:raise ValueError('held force mismatch')
    a=load(root/'frozen_predictions.npz');lookup={int(v):i for i,v in enumerate(h['ids'])}
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
