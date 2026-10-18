"""Read-only CPU endpoint evaluation: exact penalty support vs native Q4 readout."""
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np,torch,h5py
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from run_physical_symmetry_pilot import make_field,probes
from audit_saved_physical_parity import Probe
from utils import hist_alpha_init
from material_properties import MaterialProperties
from pff_model import PFFModel
run=Path(sys.argv[1]);out=run/'diagnosis_20261018_v2';out.mkdir(exist_ok=False)
torch.set_num_threads(1)
man={r['path']:r for r in json.loads((run/'retrieved/output/readout_derivation.json').read_text())}
# Full networks' hashes are supplied by the original preserved manifest.
full={line.split()[1].removeprefix('output/'):line.split()[0] for line in (run/'retrieved/output/original_output.sha256').read_text().splitlines()}
for name in ['original','control','physical_uv']:
 p=run/'retrieved'/f'{name}_network.pt';assert hashlib.sha256(p.read_bytes()).hexdigest()==full[name+'/network.pt']
inputs=run.parent/'pf_s04e011_mcs_20261017_v1/retrieved/inputs'
with h5py.File(inputs/'c0001_s002_post_commit.mat') as h:
 s=h['request28_snapshot'];points=np.array(s['node_coords']).T;cells=np.array(s['connectivity']).T.astype(int)-1
 fem=np.array(s['d_node']).ravel()
with h5py.File(inputs/'common_common_initial.mat') as h:
 fem0=np.array(h['common/d']).ravel();femlower=np.array(h['common/lower']).ravel()
 free=np.array(h['free_dof_d']).ravel().astype(int)-1
seed,weights=probes(torch.device('cpu'));seed=seed.numpy();weights=weights.numpy().astype(float);weights/=weights.sum()
x=np.linspace(-.04,.08,241);y=np.linspace(0,.04,81);xx,yy=np.meshgrid(x,y);local=np.c_[xx.ravel(),yy.ravel()]
sets={'train_global':seed[:3240],'train_front':seed[3240:],'display':local}
for xp in [-.4,-.25,-.1,0,.01]:
 yy=np.linspace(-.04,.04,1601);sets[f'cross_{xp:g}']=np.c_[np.full_like(yy,xp),yy]
allq=np.concatenate(list(sets.values()));splits=np.cumsum([0]+[len(v) for v in sets.values()]);mirror=allq*np.array([1,-1])
probe=Probe(points,cells,np.r_[allq,mirror]);n=len(allq)
rows=[];profiles=[];node_rows=[];curve_data={}
for name in ['original','control','physical_uv']:
 net=make_field(torch.load(run/'retrieved'/f'{name}_network.pt',map_location='cpu',weights_only=True),torch.device('cpu'))
 with torch.inference_mode():
  parts=[]
  for q in np.array_split(np.r_[allq,mirror],max(1,len(allq)//512)):
   parts.append(torch.stack(net.fieldCalculation(torch.tensor(q,dtype=torch.float32)),1).numpy())
 direct=np.concatenate(parts)
 z=np.load(run/'retrieved/output'/name/'fields.npz');native=np.stack([probe.value(z[k]) for k in ['u','v','d']],1)
 for mode,values in [('direct_network',direct),('native_Q4',native)]:
  a,b=values[:n],values[n:];res=np.stack(((a[:,0]-b[:,0])/.12,(a[:,1]+b[:,1]-.05999988)/.12,a[:,2]-b[:,2]),1)
  for j,key in enumerate(sets):
   sl=slice(splits[j],splits[j+1]);rr=res[sl];rows.append(dict(arm=name,representation=mode,support=key,u_mse=float(np.mean(rr[:,0]**2)),v_mse=float(np.mean(rr[:,1]**2)),d_mse=float(np.mean(rr[:,2]**2)),uv_mse=float(np.mean(rr[:,:2]**2)*2)))
  rr=res[:len(seed)];rows.append(dict(arm=name,representation=mode,support='train_mixture',u_mse=float(np.sum(weights*rr[:,0]**2)),v_mse=float(np.sum(weights*rr[:,1]**2)),d_mse=float(np.sum(weights*rr[:,2]**2)),uv_mse=float(np.sum(weights*(rr[:,0]**2+rr[:,1]**2)))))
  for j,key in enumerate(sets):
   if not key.startswith('cross_'):continue
   q=sets[key];dd=a[splits[j]:splits[j+1],2];curve_data[name+'_'+mode+'_'+key]=dd
 # Actual centerline nodes, no interpolation.
 masks={'line_xnegative':(points[:,0]<=1e-12)&(abs(points[:,1])<1e-12),'strip_xnegative':(points[:,0]<-1e-8)&(abs(points[:,1])<.02)}
 for key,m in masks.items():
  dd=z['d'][m];node_rows.append(dict(arm=name,support=key,count=int(m.sum()),minimum=float(dd.min()),maximum=float(dd.max()),mean=float(dd.mean()),max_abs_to_FEM=float(abs(dd-fem[m]).max()),RMS_to_FEM=float(np.mean((dd-fem[m])**2)**.5)))
 del net
# Analytic original PIDL history profile, FEM recovered initial, actual FEM s2 and PIDL s1 lower.
analytic=hist_alpha_init(torch.tensor(points,dtype=torch.float32),MaterialProperties(1,.3,1,.01),PFFModel('AT1','volumetric',.005),{'x_init':[-.5],'y_init':[0.],'L_crack':[.5],'angle_crack':[0.]}).numpy()
hist=np.load(run/'retrieved/output/fixed_inputs.npz')['hist_alpha']
for name,dd in [('FEM_recovered_initial',fem0),('FEM_initial_lower',femlower),('FEM_s2',fem),('PIDL_analytic_initial_history',analytic),('PIDL_s1_history',hist)]:
 for key,m in masks.items():node_rows.append(dict(arm=name,support=key,count=int(m.sum()),minimum=float(dd[m].min()),maximum=float(dd[m].max()),mean=float(dd[m].mean()),max_abs_to_FEM=float(abs(dd[m]-fem[m]).max()),RMS_to_FEM=float(np.mean((dd[m]-fem[m])**2)**.5)))
 for j,key in enumerate(sets):
  if key.startswith('cross_'):curve_data[name+'_'+key]=probe.value(dd)[splits[j]:splits[j+1]]
for filename,data in [('parity_supports.csv',rows),('precrack_nodes.csv',node_rows)]:
 with (out/filename).open('w') as f:
  w=csv.DictWriter(f,list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
np.savez_compressed(out/'profiles.npz',**curve_data,y=np.linspace(-.04,.04,1601))
(out/'summary.json').write_text(json.dumps({'CPU_read_only':True,'training_updates':0,'new_FEM':0,'fixed_global_count':3240,'fixed_front_count':6040,'mixture_mass':[.5,.5],'line_nodes':int(masks['line_xnegative'].sum()),'FEM_free_dof_d':len(free),'FEM_total_nodes':len(points)},indent=2))
for r in rows:
 if r['support']=='train_mixture':print(r)
print('centerline');print(*[r for r in node_rows if r['support']=='line_xnegative'],sep='\n')
