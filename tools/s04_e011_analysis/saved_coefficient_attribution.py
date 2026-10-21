"""CPU algebra of immutable frozen-profile arrays. No producer imports/operators.
CONFIG is supplied via stdin with this script; stdout is one compact tar stream.
"""
import os,sys,time,signal,resource,json,hashlib,io,tarfile,socket,pwd
from pathlib import Path
START=time.monotonic();CPU0=time.process_time()
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
resource.setrlimit(resource.RLIMIT_CPU,(220,220));resource.setrlimit(resource.RLIMIT_AS,(16*1024**3,16*1024**3))
def stop(sig,frame):raise TimeoutError('saved attribution wall envelope')
signal.signal(signal.SIGALRM,stop);signal.alarm(max(1,int(min(60,CONFIG['deadline_epoch']-time.time()-90))))
assert socket.gethostname()=='GPUServer8' and pwd.getpwuid(os.geteuid()).pw_name=='drtao'
ROOT=Path(CONFIG['source_root']);A=Path(CONFIG['archive_root']);OUT=Path(CONFIG['output_root'])
assert not OUT.exists() and ROOT.name==CONFIG['source_run'] and A.name==CONFIG['source_run']
READ=0;HASHREAD=0;SOLVES=0;INPUTS=[]
def sha(p):
 global HASHREAD
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);HASHREAD+=len(b)
 return h.hexdigest()
assert sha(ROOT/'export_manifest.json')==CONFIG['manifest_sha256']
assert sha(ROOT.parent/'.s04_e011_profiled_hidden_claims'/(ROOT.name+'.outer_return.json'))==CONFIG['outer_sha256']
for row in CONFIG['inputs']:
 rel=Path(row['path']);assert row['root'] in ['run','archive'] and not rel.is_absolute() and '..' not in rel.parts
 p=(ROOT if row['root']=='run' else A)/rel;assert not p.is_symlink() and p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];INPUTS.append(row)
terminal=json.loads((A/'measurement_terminal.json').read_text());assert terminal['completed'] and terminal['source_network_B0_physics_unchanged'] and terminal['state_error'] is None
import numpy as np
from scipy.linalg import cho_solve
assert np.__version__=='1.24.4'
assert time.monotonic()-START<60
MECHANICAL=time.monotonic()-START
remaining_wall=min(480-(time.monotonic()-START),CONFIG['deadline_epoch']-time.time()-90)
if remaining_wall<=0:raise TimeoutError('no remaining remote wall')
signal.alarm(max(1,int(remaining_wall)))
OUT.mkdir();free=np.load(A/'free_dofs.npy',allow_pickle=False);phis={s:np.load(A/'shared'/(s+'_phi.npy'),mmap_mode='r',allow_pickle=False) for s in ['source','plus','minus']};N,R=phis['source'].shape
assert all(p.dtype==np.float64 and p.shape==(N,R) for p in phis.values())
def load(rel):
 global READ
 p=A/(rel+'.npy');x=np.load(p,allow_pickle=False);READ+=x.nbytes
 assert x.dtype.kind in 'fiu' and (x.dtype.kind!='f' or (x.dtype==np.float64 and np.isfinite(x).all()))
 return x
r={s:load('shared/'+s+'_qraw') for s in phis}
def norm(x):return float(np.sqrt(np.sum(x*x)))
def apply(side,z):
 global READ
 p=phis[side];coeff=z.reshape(2,R).T;out=np.empty((N,2),dtype=np.float64)
 for st in range(0,N,2048):
  block=np.asarray(p[st:st+2048]);READ+=block.nbytes;out[st:st+2048]=block@coeff
 return np.concatenate((out[:,0],out[:,1]))[free]
def save(name,v):
 p=OUT/(name+'.npy');p.parent.mkdir(exist_ok=True)
 with p.open('xb') as f:np.save(f,v,allow_pickle=False)
 if sum(q.stat().st_size for q in OUT.rglob('*') if q.is_file())>512*1024**2:raise RuntimeError('new output cap')
SUMMARY=[];METRICS=[];LIN=[];h=1e-6;D=2*h
mapping={'constant':{'plus':'0004','minus':'0010'},'zero':{'plus':'0007','minus':'0013'}}
for kind in ['constant','zero']:
 arm='frozen_'+kind;z0=load(arm+'/source_z');H0=load(arm+'/H');L0=load(arm+'/factor');J=load(arm+'/Jv');U=load(arm+'/U');Q=load(arm+'/Qv');FD=load(arm+'/FD');difference=load(arm+'/difference')
 assert np.array_equal(Q-FD,difference)
 side={};bindings=[]
 for s in ['plus','minus']:
  label=arm+'_'+s;solver=json.loads((A/(label+'_solver.json')).read_text());assert len(solver['accepted'])==1 and solver['accepted'][0]['alpha']==1.0
  key=mapping[kind][s];event=json.loads((A/('linear_'+key+'_start.json')).read_text());assert event['role']=='head_vector_solve'
  H=load(arm+'/'+s+'_H');L=load(arm+'/'+s+'_factor');rhs=load('linear/'+key+'_rhs');x=load('linear/'+key+'_solution');z=load(arm+'/'+s+'_z');q=load(arm+'/'+s+'_q');end=load(arm+'/'+s+'_defect')
  assert np.array_equal(H,load('linear/'+key+'_H')) and np.array_equal(L,load('linear/'+key+'_factor'))
  assert np.array_equal(z,z0-x), 'stored accepted update does not identify initial Newton RHS'
  w=z-z0;a=-rhs;e=H@w-a;eta=e-end;field=q[free]-(r[s][free]+apply(s,z))
  side[s]=dict(H=H,z=z,w=w,a=a,e=e,end=end,eta=eta,field=field)
  bindings.append(dict(side=s,initial_defect_source='linear/'+key+'_rhs.npy',Newton_alpha=1.,accepted_steps=1,update_exact=True,head_e_norm=norm(e),end_defect_norm=norm(end),affine_consistency_norm=norm(eta),field_assembly_norm=norm(field),original_rhs_global_b_saved=False))
 assert np.array_equal((load(arm+'/plus_q')[free]-load(arm+'/minus_q')[free])/D,FD)
 P,M=side['plus'],side['minus'];dw=(P['w']-M['w'])/D;wb=(P['w']+M['w'])/2
 da=(P['a']-M['a'])/D;de=(P['e']-M['e'])/D;dd=(P['end']-M['end'])/D
 cH=((P['H']+M['H'])/2-H0)@dw+((P['H']-M['H'])/D)@wb
 Jsec=(r['plus'][free]-r['minus'][free])/D+(apply('plus',z0)-apply('minus',z0))/D
 finiteB=(apply('plus',dw)+apply('minus',dw))/2-apply('source',dw)+(apply('plus',wb)-apply('minus',wb))/D
 def solve(label,rhs):
  global SOLVES
  SOLVES+=1;assert SOLVES<=12
  x=cho_solve((L0,True),rhs,check_finite=True);res=H0@x-rhs
  LIN.append(dict(arm=arm,label=label,rhs_norm=norm(rhs),residual_norm=norm(res),relative=norm(res)/max(norm(rhs),np.finfo(float).tiny)))
  save(arm+'/head_'+label+'_rhs',rhs);save(arm+'/head_'+label+'_solution',x)
  return x
 xU=solve('U',U);xa=solve('secant_a',da);xc=solve('coefficient_H',cH);xe=solve('endpoint_total_residual',de);xd=solve('endpoint_defect',dd)
 Qrecon=J-apply('source',xU);Qsec=Jsec+apply('source',xa)
 components={
 'AD_reconstruction':Q-Qrecon,
 'AD_vs_secant_J':J-Jsec,
 'AD_vs_secant_head':-apply('source',xU)-apply('source',xa),
 'finite_B':-finiteB,
 'finite_H':apply('source',xc),
 'endpoint_defect':-apply('source',xd),
 'affine_consistency':-apply('source',xe-xd),
 'offline_field_reconstruction':-(P['field']-M['field'])/D}
 total=np.zeros_like(Q)
 for name,value in components.items():total=total+value
 closure=difference-total;den=float(difference@difference)
 for name,value in {**components,'sum':total,'closure':closure,'mismatch':difference,'Qsec':Qsec,'Jsec':Jsec}.items():
  save(arm+'/'+name,value);METRICS.append(dict(arm=arm,component=name,L2=norm(value),relative_to_total_norm=norm(value)/norm(difference),signed_projection_on_mismatch=float(value@difference)/den))
 # Separate exact head identity closure. No b is manufactured from a solved endpoint.
 head_identity=H0@dw-(da+de-cH)
 SUMMARY.append(dict(arm=arm,source_z_norm=norm(z0),Q_norm=norm(Q),FD_norm=norm(FD),mismatch_norm=norm(difference),Q_reconstruction_error=norm(Q-Qrecon),coefficient_secant_vs_FD=norm(Qsec-FD),closure_norm=norm(closure),head_identity_closure=norm(head_identity),bindings=bindings,nominal_parameter_direction_only=True,actual_parameter_endpoint_arrays_saved=False,global_b_directly_saved=False,coefficient_equation_used='a_s=-original_initial_defect_s(z0), H_s w_s=a_s+e_s; no Hz_end fabricated RHS',bounds_are_not_forward_certificates=True))
assert SOLVES==10
save('free_dofs',free)
result=dict(status='SAVED_COEFFICIENT_ATTRIBUTION_COMPLETE',analysis_id=CONFIG['analysis_id'],source_run=CONFIG['source_run'],source_manifest_sha256=CONFIG['manifest_sha256'],science_state='c20s4/FEMdamage/sourcePIDLhistory/B0/UV/Phi/T0/seed173/scales/h1e-6 fixed',arms=SUMMARY,metrics=METRICS,linear_solves=LIN,vector_solves=SOLVES,triangular_solves=2*SOLVES,new_factors=0,new_NN_AD_physics_FEM_SVD_GPU=0,parameter_endpoint_direction_check='Unavailable: actual parameter endpoint arrays not saved; no checkpoint loaded',original_dtype='binary64 checked saved arrays; E011Bridge.parameter_state contract float64, endpoints unavailable',input_hash_bytes=HASHREAD,logical_array_read_bytes=READ,OS_ru_inblock_raw=resource.getrusage(resource.RUSAGE_SELF).ru_inblock,actual_physical_disk_read_bytes='UNKNOWN',CPU_seconds=time.process_time()-CPU0,wall_seconds=time.monotonic()-START,mechanical_seconds=MECHANICAL,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,RLIMIT_CPU=list(resource.getrlimit(resource.RLIMIT_CPU)),RLIMIT_AS=list(resource.getrlimit(resource.RLIMIT_AS)),numpy=np.__version__,all_input_hashes_verified=True,no_unique_cause_or_capacity_claim=True)
(OUT/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
entries=[dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()]
assert sum(x['bytes'] for x in entries)<100*1024**2
(OUT/'output_manifest.json').write_text(json.dumps(dict(files=entries,inputs=INPUTS,source_script_sha256=CONFIG['source_script_sha256']),indent=2)+'\n')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for p in sorted(OUT.rglob('*')):
  if p.is_file():tar.add(p,arcname=str(p.relative_to(OUT)),recursive=False)

print(json.dumps(dict(final_CPU_seconds=time.process_time()-CPU0,final_wall_seconds=time.monotonic()-START,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,OS_ru_inblock_raw=resource.getrusage(resource.RUSAGE_SELF).ru_inblock,actual_physical_disk_read_bytes='UNKNOWN',total_process_CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,output_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),phase='through_completed_tar_stream')),file=sys.stderr,flush=True)
