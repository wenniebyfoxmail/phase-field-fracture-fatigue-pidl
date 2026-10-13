#!/usr/bin/env python3
"""E015 isolated preparation, Taobo-only static diagnostic, held validation."""
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
from aa2024_patch_mechanics import rectangular_mesh, candidate_basis, solve_patch, sample_regular_mesh
from aa2024_rigid_observable import quotient_residual

DOMAINS={'B0':dict(nx=41,ny=21,width=36.,height=18.),
         'B1':dict(nx=49,ny=29,width=43.2,height=25.2)}
PAIRS=np.array([(r,l) for l in np.linspace(0,.95,6) for r in np.linspace(0,.95,21)])
DEPENDENCIES=('aa2024_triplet_structure.py','aa2024_patch_mechanics.py','aa2024_rigid_observable.py')
ARMS=tuple(b+k for b in DOMAINS for k in ('K0','K1','d0','intact'))+('secant',)

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def write_json(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False))

def sources():return {s:sha(Path(__file__).with_name(s)) for s in DEPENDENCIES}

def completed(root,mode,names):
    r=json.loads((root/'execution_receipt.json').read_text())
    if (r.get('mode')!=mode or r.get('execution_status')!='succeeded' or
        r.get('runner_sha256')!=sha(__file__) or r.get('dependencies_sha256')!=sources()):
        raise ValueError('completion/source receipt mismatch')
    if any(r.get('artifacts_sha256',{}).get(n)!=sha(root/n) for n in names):
        raise ValueError('completion artifact mismatch')
    return r

def headers(text):
    # Only header lines converted; the held response body is never parsed here.
    out={}
    for line in text.splitlines():
        if line and not line.startswith('#'):break
        if line.startswith('#') and ':' in line:
            k,v=line.lstrip('#').split(':',1);k=k.strip();v=v.strip()
            if k in out:raise ValueError('duplicate header')
            if v.startswith('value_element'):
                if ':' not in v:raise ValueError('bad header wrapper')
                v=v.split(':',1)[1].strip()
            out[k]=v
    return out

def identity(h,s):
    for k,value in (('current_stage_index',s),('reference_stage_index',1),('cycles',Decimal('225211.5'))):
        if Decimal(h[k])!=value:raise ValueError('stage/reference/cycle mismatch')
    force=float(h['force'])
    if not np.isfinite(force):raise ValueError('nonfinite force')
    return force

def damage(d0,br,bl,r,l):return d0+(1-d0)*(1-(1-r*br)*(1-l*bl))

def error(xy,r,w):
    z=quotient_residual(xy,r,w)
    return float(np.sum(w*np.linalg.norm(z,axis=1))/w.sum())

def check_budget(start):
    if time.monotonic()-start>=600:
        raise TimeoutError('soft600s completion budget; no completed fit/held access')

def prepare(archive,out):
    if archive.stat().st_size!=EXPECTED_SIZE:raise ValueError('archive size mismatch')
    h=hashlib.md5()
    with archive.open('rb') as f:
        for b in iter(lambda:f.read(8388608),b''):h.update(b)
    if h.hexdigest()!=EXPECTED_MD5:raise ValueError('archive identity mismatch')
    with zipfile.ZipFile(archive) as z:
        texts=[read_member(z,f'global_3d_dic/Nodemaps/global_3d_dic_results_1_{s}.txt') for s in (10,11,12)]
        connection=read_member(z,'global_3d_dic/Connections/global_3d_dic_results_1_10_connections.txt')
    forces=[identity(headers(t),s) for t,s in zip(texts,(10,11,12))]
    if not 0<forces[0]<forces[1]<forces[2]:raise ValueError('load order mismatch')
    a,b=[parse_nodemap(t,allow_displacements=True) for t in texts[:2]]
    ids=a['ids']
    if not np.array_equal(ids,b['ids']) or not np.array_equal(ids,np.arange(1,len(ids)+1)):
        raise ValueError('training identity/order mismatch')
    fit=a['finite_xyz']&b['finite_xyz']&a['finite_u']&b['finite_u']
    if not np.allclose(a['xyz'][fit],b['xyz'][fit],atol=1e-6,rtol=0):
        raise ValueError('training reference coordinates mismatch')
    xy=a['xyz'][:,:2];v=b['u'][:,:2]-a['u'][:,:2]
    lines=[x for x in connection.splitlines() if x.strip()]
    if [x.strip() for x in lines[0].split(';')]!=['Type','Element #','Node 1','Node 2','Node 3']:
        raise ValueError('connection schema')
    arr=np.asarray([[int(x.strip()) for x in line.split(';')] for line in lines[1:]],dtype=int)
    if arr.ndim!=2 or arr.shape[1]!=5 or np.any(arr[:,0]!=3):raise ValueError('Type3 required')
    t=arr[:,2:];padding=np.all(t==-1,axis=1);t=t[~padding]
    if np.any(t<0) or np.any(t>=len(ids)) or any(len(set(row))!=3 for row in t):
        raise ValueError('invalid nonpadding connection')
    if len({tuple(sorted(row)) for row in t})!=len(t):raise ValueError('duplicate source triangle')
    t=t[np.all(fit[t],axis=1)];p=xy[t]
    areas=np.abs((p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0]))/2
    if np.any(areas<=1e-12):raise ValueError('source triangle degeneracy')
    w=np.bincount(t.ravel(),weights=np.repeat(areas/3,3),minlength=len(ids))
    obs=fit&(np.abs(xy[:,0])<16.2)&(np.abs(xy[:,1])<7.2)&(w>0)
    if obs.sum()<10:raise ValueError('insufficient observations')
    data=dict(ids=ids[obs],xy=xy[obs],weights=w[obs],train_v=v[obs],u10=a['u'][obs,:2],
              alpha=(forces[2]-forces[0])/(forces[1]-forces[0]))
    asset={}
    for name,params in DOMAINS.items():
        mesh,tri,bd=rectangular_mesh(**params)
        dist,idx=cKDTree(xy[fit]).query(mesh[bd],k=4)
        if np.any(dist[:,3]>2):raise ValueError('boundary fourth neighbour exceeds2mm')
        bc=[]
        for point,neighbors in zip(mesh[bd],idx):
            A=np.column_stack((np.ones(4),xy[fit][neighbors]-point))
            coeff,_,rank,_=np.linalg.lstsq(A,v[fit][neighbors],rcond=1e-12)
            if rank!=3:raise ValueError('boundary affine rank')
            bc.append(coeff[0])
        d0,br=candidate_basis(mesh);bl=np.exp(-((mesh[:,0]+9)**2+mesh[:,1]**2)/18)
        for k,value in dict(mesh=mesh,tri=tri,boundary=bd,bc=np.array(bc),d0=d0,br=br,bl=bl).items():
            data[name+'_'+k]=value
        asset[name]={'nodes':len(mesh),'triangles':len(tri),'boundary_nodes':int(bd.sum()),
            'fourth_neighbour_max_mm':float(dist[:,3].max()),'domain':params}
    np.savez_compressed(out/'prepared.npz',**data)
    write_json(out/'preparation.json',dict(cycle='225211.5',reference=1,forces=forces,assets=asset,
        observations=int(obs.sum()),weight_area_mm2=float(w[obs].sum()),
        held_member_sha256=hashlib.sha256(texts[2].encode('utf-8')).hexdigest(),
        archive=str(archive),archive_size=EXPECTED_SIZE,archive_md5=EXPECTED_MD5))

def load(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def sensitivity(fields,xy,w):
    J=[]
    for i,step in ((1,PAIRS[1,0]),(21,PAIRS[21,1])):
        J.append(quotient_residual(xy,(fields[i]-fields[0])/step,w).ravel())
    J=np.column_stack(J)*np.repeat(np.sqrt(w/w.sum()),2)[:,None]
    sv=np.linalg.svd(J,compute_uv=False)
    norms=np.linalg.norm(J,axis=0)
    cosine=float(np.dot(J[:,0],J[:,1])/np.prod(norms)) if np.prod(norms)>0 else None
    return dict(secant_singular_values_mm_per_q=sv.tolist(),column_norms_mm_per_q=norms.tolist(),
        cosine=cosine,meaning='finite_secants_not_tangent_noise_rank_or_physical_identifiability')

def fit(root,out):
    completed(root,'prepare',('preparation.json','prepared.npz'))
    a=load(root/'prepared.npz');meta=json.loads((root/'preparation.json').read_text())
    predictions={k:a[k] for k in ('ids','xy','weights','u10','alpha')}
    all_fields={};states={};records={};start=time.monotonic()
    for name,params in DOMAINS.items():
        get=lambda k:a[name+'_'+k]
        fields=[];rows=[]
        for r,l in PAIRS:
            check_budget(start)
            d=damage(get('d0'),get('br'),get('bl'),r,l)
            u,res=solve_patch(get('mesh'),get('tri'),get('boundary'),get('bc'),d)
            check_budget(start)
            sampled=sample_regular_mesh(u,a['xy'],**params)
            fields.append(sampled);rows.append(dict(qR=float(r),qL=float(l),
                train_MAE_mm=error(a['xy'],sampled-a['train_v'],a['weights']),relative_residual=res))
        fields=np.array(fields);loss=np.array([row['train_MAE_mm'] for row in rows])
        chosen={'K0':int(np.argmin(loss[:21])),'K1':int(np.argmin(loss))}
        check_budget(start)
        intact,res=solve_patch(get('mesh'),get('tri'),get('boundary'),get('bc'),np.zeros(len(get('mesh'))))
        check_budget(start)
        predictions[name+'intact']=a['alpha']*sample_regular_mesh(intact,a['xy'],**params)
        predictions[name+'d0']=a['alpha']*fields[0]
        for k,i in chosen.items():
            predictions[name+k]=a['alpha']*fields[i]
            states[name+k]=damage(get('d0'),get('br'),get('bl'),*PAIRS[i])
        span=max(error(a['xy'],f-fields[0],a['weights']) for f in fields)
        records[name]=dict(profile=rows,selected=chosen,sensitivity=sensitivity(fields,a['xy'],a['weights']),
            response_span_mm=span,numerically_unresolved=span<=1e-10,intact_relative_residual=res)
        all_fields[name]=fields
        print(name,'completed126pairs',chosen,flush=True)
    predictions['secant']=a['alpha']*a['train_v']
    check_budget(start)
    np.savez_compressed(out/'frozen_predictions.npz',**predictions)
    np.savez_compressed(out/'candidate_fields.npz',pairs=PAIRS,**all_fields)
    np.savez_compressed(out/'conditional_states.npz',**states)
    write_json(out/'profiles.json',records)
    check_budget(start)
    write_json(out/'fit.json',dict(status='all_predictions_frozen_before_held_response',
        held_member_sha256=meta['held_member_sha256'],held_force=meta['forces'][2],cycle=meta['cycle'],
        prepare_npz_sha256=sha(root/'prepared.npz'),scope='conditional_2x2_diagnostic_NOT_physical_identification'))

def contrasts(m):
    a,b,c,d=[m[k] for k in ('B0K0','B1K0','B0K1','B1K1')]
    gb,gk=a-b,a-c
    if max(gb,gk)<=0:lever='neither_single_change_improves'
    elif gb==gk:lever='equal_improving_single_changes'
    elif gb>max(gk,0):lever='boundary_placement_larger_single_gain'
    else:lever='basis_capacity_larger_single_gain'
    return dict(primary_boundary_only_minus_basis_only_mm=b-c,
        boundary_mean_gain_mm=((a-b)+(c-d))/2,basis_mean_gain_mm=((a-c)+(b-d))/2,
        interaction_mm=d-b-c+a,boundary_only_gain_mm=a-b,basis_only_gain_mm=a-c,
        combined_gain_mm=a-d,descriptive_single_lever=lever,
        no_selected_factorial_arm_beats_secant=all(m[k]>=m['secant'] for k in ('B0K0','B1K0','B0K1','B1K1')))

def validate(root,high,out):
    completed(root,'fit',('fit.json','profiles.json','frozen_predictions.npz','candidate_fields.npz','conditional_states.npz'))
    meta=json.loads((root/'fit.json').read_text())
    if meta['status']!='all_predictions_frozen_before_held_response':raise ValueError('not frozen')
    if high.stat().st_size>16000000 or sha(high)!=meta['held_member_sha256']:raise ValueError('held identity mismatch')
    h=parse_nodemap(high.read_text(),allow_displacements=True)
    if identity(h['headers'],12)!=meta['held_force']:raise ValueError('held force mismatch')
    a=load(root/'frozen_predictions.npz');lookup={int(v):i for i,v in enumerate(h['ids'])}
    if any(int(v) not in lookup for v in a['ids']):raise ValueError('held facet absent')
    idx=np.array([lookup[int(v)] for v in a['ids']])
    valid=np.isfinite(h['xyz'][idx,:2]).all(1)&np.isfinite(h['u'][idx,:2]).all(1)
    if valid.sum()<10 or not np.allclose(h['xyz'][idx[valid],:2],a['xy'][valid],atol=1e-6,rtol=0):
        raise ValueError('held support/reference mismatch')
    xy,w=a['xy'][valid],a['weights'][valid];target=h['u'][idx[valid],:2]-a['u10'][valid]
    data=dict(ids=a['ids'][valid],xy=xy,weights=w,target=target);metrics={}
    for k in ARMS:
        value=a[k][valid];r=quotient_residual(xy,value-target,w)
        metrics[k]=float(np.sum(w*np.linalg.norm(r,axis=1))/w.sum())
        data[k]=value;data[k+'_residual']=r
    np.savez_compressed(out/'validation_fields.npz',**data)
    write_json(out/'metrics.json',dict(MAE_mm=metrics,contrasts=contrasts(metrics),eligible=int(valid.sum()),
        frozen_support=len(valid),missing_ids=a['ids'][~valid].tolist(),area_coverage=float(w.sum()/a['weights'].sum()),
        scope='descriptive_intervention_comparison_NOT_causal_boundary_or_true_damage_identification'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prepare','fit','validate'));p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--high-member',type=Path)
    p.add_argument('--run-id',required=True);p.add_argument('--source-commit',required=True)
    args=p.parse_args()
    if args.mode=='fit' and socket.gethostname()!='GPUServer8':raise ValueError('Taobo-only real fit')
    args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    r=dict(mode=args.mode,run_id=args.run_id,source_commit_declared=args.source_commit,
        hostname=socket.gethostname(),pid=os.getpid(),command=sys.argv,start_utc=datetime.now(timezone.utc).isoformat(),
        runner_sha256=sha(__file__),dependencies_sha256=sources(),numpy_version=np.__version__,
        thread_environment={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
        execution_status='running')
    try:
        if args.mode=='prepare':prepare(args.input,args.output)
        elif args.mode=='fit':fit(args.input,args.output)
        else:
            if args.high_member is None:raise ValueError('high member required')
            validate(args.input,args.high_member,args.output)
        r['execution_status']='succeeded'
    except Exception as e:
        r['execution_status']='failed';r['error']=str(e);raise
    finally:
        r.update(elapsed_seconds=time.monotonic()-start,end_utc=datetime.now(timezone.utc).isoformat(),
            artifacts_sha256={p.name:sha(p) for p in args.output.iterdir() if p.is_file() and p.name!='execution_receipt.json'})
        write_json(args.output/'execution_receipt.json',r)

if __name__=='__main__':main()
