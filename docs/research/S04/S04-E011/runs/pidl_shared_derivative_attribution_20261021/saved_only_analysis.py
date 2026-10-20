import os
for n in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[n]='1'
import time,signal,resource,json,hashlib
from pathlib import Path
start=time.monotonic();cpu=time.process_time();signal.alarm(90)
import numpy as np
c=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profile_measure_c20_r1_hq_20261020')
a=c/'retrieved_partial/archive';audit=a/'measurement_audit';out=c/'shared_derivative_attribution';out.mkdir(exist_ok=True)
events=[json.loads(p.read_text()) for p in audit.glob('*.json')];heads={}
for e in events:
 if e['event']=='side_returned' and e['data']['arm']=='B':
  d=e['data'];vals={}
  for name in ['head_gradient','head_z']:
   ref=e['arrays'][name];p=audit/Path(ref['path']).name
   assert hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256']
   vals[name]=np.load(p,allow_pickle=False)
  heads[d['label']]=vals
rows=[]
for pair,h,plus,minus,err in [('h',1e-6,'plus_h','minus_h',.00944476041534808),('half',5e-7,'plus_half','minus_half',.006760963599658827)]:
 gp,gm=heads[plus]['head_gradient'],heads[minus]['head_gradient'];zp,zm=heads[plus]['head_z'],heads[minus]['head_z']
 n=lambda x:float(np.sqrt(np.sum(x*x)))
 den=n(gp)+n(gm)
 rows.append(dict(pair=pair,h=h,side_gradient_L2_plus=n(gp),side_gradient_L2_minus=n(gm),side_gradient_difference_over_2h_L2=n((gp-gm)/(2*h)),minimum_common_BHinv_gain_if_all_B_mismatch_were_side_solver_defects=2*h*err/den,head_z_signed_mean_L2=n((zp+zm)/2),head_z_central_derivative_L2=n((zp-zm)/(2*h)),interpretation='First-order triangle lower requirement on max ||B_side H_side^-1|| if this alone explained all field FD mismatch; NOT a measured gain or bound. Signed z mean mixes source correction and finite-h curvature; no unique attribution.'))
missing={'local_physical_point_npz':(a/'point_0/local_physical_point.npz').exists(),'H_or_factor_filenames':[]}
# bounded inventory only of this already-retrieved subset, no remote/fallback lookup
for p in (c/'retrieved_partial').rglob('*'):
 if p.is_file() and (p.suffix=='.npz' or any(t in p.name.lower() for t in ['factor','hessian'])):missing['H_or_factor_filenames'].append(str(p.relative_to(c)))
rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
assert rss<2*1024**3
result=dict(scope='saved-only small head arrays and local filenames; zero producer evaluation',rows=rows,local_H_factor_inventory=missing,source_chart_g_inf=json.loads((a/'point_0/local_chart_admission.json').read_text())['actual_Phi_gradient_inf'],fresh_A_zero_g_inf=8.272852997266711e-11,CPU_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start,peak_RSS_bytes_macos=rss,threads=1,NN_AD_JVP_VJP_physics_tangent_SVD_solve_SSH=0)
(out/'saved_head_defect_scales.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))
