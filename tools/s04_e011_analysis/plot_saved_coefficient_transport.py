"""Only saved-vector figures; no NN, AD, mechanics operator or solves."""
import os,resource,signal,time
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
resource.setrlimit(resource.RLIMIT_CPU,(25,25))
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'s04_e011_execution'))
from local_owned_rss_guard import OwnedGuard
g=OwnedGuard(90).start()
import json,hashlib,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm
start=time.monotonic();c=Path(sys.argv[1]);a=c/'retrieved';out=c/'analysis';out.mkdir();z=json.loads((a/'result.json').read_text());terms=['AD_reconstruction','AD_vs_secant_J','AD_vs_secant_head','finite_B','finite_H','endpoint_defect','affine_consistency','offline_field_reconstruction','closure'];labels=['source Q reconstruction','AD − secant J','AD − secant head','finite B cross term','finite H cross term','endpoint head defect','affine consistency','offline field reconstruction','closure remainder']
rows=z['metrics'];fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained');ys=np.arange(len(terms))
for j,kind in enumerate(['constant','zero']):
 d={r['component']:r for r in rows if r['arm']=='frozen_'+kind};norms=[d[t]['relative_to_total_norm'] for t in terms];proj=[d[t]['signed_projection_on_mismatch'] for t in terms];color=['#0072B2','#D55E00'][j]
 axes[0].barh(ys+(j-.5)*.34,norms,height=.32,color=color,label=kind);axes[1].barh(ys+(j-.5)*.34,proj,height=.32,color=color,label=kind)
for ax in axes:ax.set_yticks(ys,labels);ax.invert_yaxis();ax.axvline(1,color='black',ls='--',lw=1);ax.legend()
axes[0].set_xscale('log');axes[0].set_xlabel('Component L2 / original mismatch L2');axes[1].set_xscale('symlog',linthresh=1e-3);axes[1].set_xlabel('Signed projection on original mismatch');fig.suptitle('Fixed c20 PIDL saved coefficient decomposition: vectors can cancel');fig.savefig(out/'coefficient_decomposition.png',dpi=160);plt.close(fig)
mesh=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_probe/retrieved/root/inputs/c20_peak.npz');assert hashlib.sha256(mesh.read_bytes()).hexdigest()=='c51bd3c121378d33c7d08aaf5f88f76b7decba4827c1e8d271bb8c6dec73ecd3';m=np.load(mesh,allow_pickle=False);free=np.load(a/'free_dofs.npy');assert np.array_equal(free,m['freeu']);nodes=m['nodes'];cells=m['cells'];n=len(nodes)
def v(name):return np.load(a/'frozen_constant'/(name+'.npy'),allow_pickle=False)
vec=[v('mismatch'),v('AD_vs_secant_J')+v('AD_vs_secant_head'),v('finite_B')+v('finite_H'),sum((v(t) for t in ['AD_reconstruction','endpoint_defect','affine_consistency','offline_field_reconstruction','closure']),np.zeros_like(v('mismatch')))];titles=['Original Q − FD','AD − coefficient-secant terms','Finite-step B/H cross terms','Remaining terms + closure']
vals=[]
for x in vec:
 f=np.zeros(2*n);f[free]=x;mag=np.sqrt(f[:n]**2+f[n:]**2);vals.append(np.sqrt(np.mean(mag[cells]**2,axis=1)))
fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained');vmax=max(float(x.max()) for x in vals)
for ax,val,title in zip(axes.flat,vals,titles):
 pc=PolyCollection(nodes[cells],array=val,cmap='viridis',edgecolors='none',norm=SymLogNorm(linthresh=max(vmax*1e-4,1e-16),vmin=0,vmax=vmax));ax.add_collection(pc);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('x (model units)');ax.set_ylabel('y (model units)')
fig.colorbar(pc,ax=axes,label='Cell RMS nodal UV derivative magnitude; shared symlog',shrink=.85);fig.savefig(out/'coefficient_fields.png',dpi=160);plt.close(fig)
provenance='Original immutable frozen R002/f5972efd c20s4, source/+h/-h Phi/r/z/H/L/J/U/Q/FD and authentic initial-gradient Newton RHS; new saved-only CPU attribution '+z['analysis_id']+'. No new NN/AD/force/tangent/FEM/SVD or physical solution. Free UV order/unweighted L2 unchanged, h1e-6; figures use exact retrieved decomposition vectors. Source RHS is initial defect, not a global b manufactured from solved z.'
for stem,reading in [('coefficient_decomposition','Left shows non-additive component norm ratios; right signed dot(component,mismatch)/||mismatch||². Signed projections can cancel. Neither is an independent causal percentage.'),('coefficient_fields','Constant-target arm selected in advance. Panels show magnitudes of original mismatch, two AD-secant terms summed as vectors, finite B/H terms summed as vectors, and remaining terms plus closure. Their vectors add to mismatch; displayed magnitudes do not add. Shared color scale, no clipping/smoothing.')]:
 (out/(stem+'.md')).write_text('# '+stem+'\n\n## How to read\n\n'+reading+'\n\n## Data provenance\n\n'+provenance+'\n\n## Limitations\n\nExact algebra closure is not independent causal proof or a complete arithmetic forward bound. Offline field reconstruction includes new CPU product arithmetic. Actual rounded parameter endpoints and direct global b were not saved. No optimization/architecture/physical validation claim.\n')
(out/'README_analysis.md').write_text('# Saved coefficient attribution\n\n'+provenance+'\n\nTwo figures: component norms/signed projections and constant-arm field decomposition. Result and original inputs remain immutable, no producer rerun.\n')
g.close()
(out/'plot_cost.json').write_text(json.dumps(dict(wall_seconds=time.monotonic()-start,total_process_CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,CPU_hard_seconds=25,Mac_AS_limit_required=False,monitor=g.report(),geometry_file_hash_bytes=mesh.stat().st_size,new_physics_NN_AD_SVD_solve=0),indent=2)+'\n')
print(json.dumps(z['arms'],indent=2))
