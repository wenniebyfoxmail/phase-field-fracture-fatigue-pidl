"""Matched post-refresh history/factor review from existing GP outputs."""
from pathlib import Path
import ast,base64,csv,gzip,json,hashlib
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm,Normalize,TwoSlopeNorm

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=ROOT/'local_archive/report_ch4_fatigue_fields_20261015'
RAW=OUT/'raw';ANA=OUT/'analysis';FIG=OUT/'figures'
for p in [ANA,FIG]:p.mkdir(parents=True,exist_ok=True)
OLD=ROOT/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z'
CYCLES=(20,60,83);ARMS=('q4','t3')
plt.rcParams.update({'font.size':11,'axes.titlesize':12,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'savefig.dpi':220})

def writecsv(name,rows):
 with (ANA/name).open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def f_law(h):return np.minimum(1.,(1./(np.asarray(h,float)+.5))**2)
def average(x,w):return float(np.sum(x*w)/np.sum(w))
def corr(a,b,w):
 aa=a-average(a,w);bb=b-average(b,w);den=np.sqrt(np.sum(w*aa*aa)*np.sum(w*bb*bb))
 return float(np.sum(w*aa*bb)/den) if den else None
def qtile(a,w,q):
 a=a.ravel();w=w.ravel();i=np.argsort(a);return float(a[i[np.searchsorted(np.cumsum(w[i])/w.sum(),q)]])
def metrics(a,b,w):
 d=b-a;return {'reference_mean':average(a,w),'candidate_mean':average(b,w),'reference_max':float(a.max()),'candidate_max':float(b.max()),'reference_min':float(a.min()),'candidate_min':float(b.min()),'MAE':average(np.abs(d),w),'relative_L2':float(np.sqrt(np.sum(w*d*d)/np.sum(w*a*a))),'correlation':corr(a,b,w),'max_abs_difference':float(np.abs(d).max())}

def geometry(points,cells):
 xy=points[cells];n=cells.shape[1]
 if n==4:
  g=1/np.sqrt(3);N=[];D=[]
  for x,y in [(g,g),(-g,g),(g,-g),(-g,-g)]:
   N.append(.25*np.array([(1-x)*(1-y),(1+x)*(1-y),(1+x)*(1+y),(1-x)*(1+y)]))
   D.append(.25*np.array([[-(1-y),(1-y),(1+y),-(1+y)],[-(1-x),-(1+x),(1+x),(1-x)]]))
  N=np.array(N);J=np.einsum('gij,ejk->egik',np.array(D),xy);weights=np.linalg.det(J)
 else:
  N=np.array([[2/3,1/6,1/6],[1/6,2/3,1/6],[1/6,1/6,2/3]])
  v=xy[:,1]-xy[:,0];u=xy[:,2]-xy[:,0];area=.5*(v[:,0]*u[:,1]-v[:,1]*u[:,0]);weights=np.repeat((area/3)[:,None],3,axis=1)
 assert np.all(weights>0) and abs(weights.sum()-1)<1e-10
 return {'vertices':xy,'weights':weights,'gp_xy':np.einsum('gn,enx->egx',N,xy),'area':weights.sum(1),'centers':xy.mean(1)}

payload={};fem_receipts=[]
for line in (RAW/'fem_history.stdout').read_text().splitlines():
 if line.startswith('META|'):fem_receipts.append(json.loads(line.split('|',1)[1]))
 if line.startswith('PACK|'):
  _,arm,c,s,name,rows,cols,b=line.split('|',7)
  a=np.frombuffer(gzip.decompress(base64.b64decode(b)),dtype='<f8').reshape((int(rows),int(cols)),order='F').copy()
  assert np.isfinite(a).all();payload[f'{arm.lower()}_c{c}_s{s}_{name}']=a
assert len(fem_receipts)==12
pidl=np.load(RAW/'pidl_history.npz',allow_pickle=False);pidl_receipts=json.loads(str(pidl['receipts_json']))
assert len(pidl_receipts)==12
expected_order={'q4':'(+,+),(-,+),(+,-),(-,-)','t3':'(2/3,1/6,1/6),(1/6,2/3,1/6),(1/6,1/6,2/3)'}
assert all(r['gauss_order']==expected_order[r['arm']] for r in pidl_receipts)
schedule={}
for arm in ARMS:
 settings=str(pidl['settings_'+arm])
 schedule[arm]=ast.literal_eval(next(l.split(': ',1)[1] for l in settings.splitlines() if l.startswith('derived_explicit_cycle_factors_for_internal_oracles: ')))
assert all(abs(r['load_factor']-schedule[r['arm'].lower()][r['substep']-1])<1e-12 for r in fem_receipts)


m=loadmat(OLD/'analysis/trajectory_error/raw/mesh_for_fem_trajectory.mat');points=np.asarray(m['points'],float)
cells={a:np.asarray(m[a+'cells'],int)-1 for a in ARMS}
assert np.array_equal(cells['t3'][::2],cells['q4'][:,[0,1,2]])
assert np.array_equal(cells['t3'][1::2],cells['q4'][:,[0,2,3]])
geo={a:geometry(points,cells[a]) for a in ARMS}
fields={};checks={};law_checks=[];statistics=[];gaps=[];updates=[];support=[]
for arm in ARMS:
 checks[arm+'_fem_coordinates_exact']=bool(np.array_equal(payload[f'{arm}_c20_s4_coords'],points))
 checks[arm+'_fem_connectivity_exact']=bool(np.array_equal(payload[f'{arm}_c20_s4_cells'].astype(int)-1,cells[arm]))
 assert checks[arm+'_fem_coordinates_exact'] and checks[arm+'_fem_connectivity_exact']
 W=geo[arm]['weights'];ROI=np.abs(geo[arm]['gp_xy'][...,1])<=.03
 for c in CYCLES:
  for solver,src in [('FEM',payload),('PIDL',pidl)]:
   for sub in [3,4]:
    H=np.asarray(src[f'{arm}_c{c}_s{sub}_H'],float);F=np.asarray(src[f'{arm}_c{c}_s{sub}_F'],float)
    assert H.shape==W.shape and F.shape==W.shape and np.isfinite(H).all() and np.isfinite(F).all()
    assert H.min()>=0 and F.min()>=0 and F.max()<=1
    err=float(np.abs(F-f_law(H)).max());assert err<3e-7,(solver,arm,c,sub,err)
    law_checks.append({'solver':solver,'topology':arm,'cycle':c,'substep':sub,'f_vs_f_of_GP_history_maxabs':err})
    fields[(solver,arm,c,sub,'H')]=H;fields[(solver,arm,c,sub,'F')]=F
   H=fields[(solver,arm,c,4,'H')];F=fields[(solver,arm,c,4,'F')]
   H0=fields[(solver,arm,c,3,'H')];F0=fields[(solver,arm,c,3,'F')]
   assert (H-H0).min()>-1e-9 and (F-F0).max()<3e-7
   statistics.append({'solver':solver,'topology':arm,'cycle':c,'global_peak_step':5*c-1,'history_mean':average(H,W),'history_p99':qtile(H,W,.99),'history_max_GP':float(H.max()),'factor_mean':average(F,W),'factor_min_GP':float(F.min()),'history_corridor_mean':average(H[ROI],W[ROI]),'factor_corridor_mean':average(F[ROI],W[ROI]),'corridor_GP_area':float(W[ROI].sum())})
   updates.append({'solver':solver,'topology':arm,'cycle':c,'previous_substep':3,'current_substep':4,'history_increment_mean':average(H-H0,W),'history_increment_max':float((H-H0).max()),'factor_pre_min':float(F0.min()),'factor_post_min':float(F.min()),'factor_change_MAE':average(np.abs(F-F0),W),'factor_change_max':float(np.abs(F-F0).max())})
  for field in ['H','F']:
   a=fields[('FEM',arm,c,4,field)];b=fields[('PIDL',arm,c,4,field)]
   gaps.append({'topology':arm,'cycle':c,'field':field,'domain':'full',**metrics(a,b,W)})
   gaps.append({'topology':arm,'cycle':c,'field':field,'domain':'corridor_abs_y_le_0.03',**metrics(a[ROI],b[ROI],W[ROI])})
  ce=pidl[f'{arm}_c{c}_centers'];ar=pidl[f'{arm}_c{c}_areas']
  cerr=float(np.max(np.abs(ce-geo[arm]['centers'])));aerr=float(np.max(np.abs(ar-geo[arm]['area'])/geo[arm]['area']))
  assert cerr<2e-7 and aerr<3e-6,(arm,c,cerr,aerr)
  support.append({'topology':arm,'cycle':c,'elements':len(cells[arm]),'gauss_points_per_element':W.shape[1],'cell_center_max_abs_difference':cerr,'cell_area_max_relative_difference':aerr,'common_physical_area':float(W.sum()),'corridor_GP_area':float(W[ROI].sum()),'evaluation':'within topology, matched element and GP order; common double-precision geometric weights'})
 for solver in ['FEM','PIDL']:
  hs=np.stack([fields[(solver,arm,c,4,'H')] for c in CYCLES]);fs=np.stack([fields[(solver,arm,c,4,'F')] for c in CYCLES])
  checks[solver+'_'+arm+'_history_monotone']=bool(np.min(np.diff(hs,axis=0))>=-1e-9)
  checks[solver+'_'+arm+'_factor_monotone']=bool(np.max(np.diff(fs,axis=0))<3e-7)
assert all(checks.values()),checks
writecsv('native_GP_statistics.csv',statistics);writecsv('same_state_GP_differences.csv',gaps);writecsv('history_update_s3_to_s4.csv',updates);writecsv('spatial_support_checks.csv',support);writecsv('degradation_law_checks.csv',law_checks)

# Independent, physically weighted native-cell reductions for display only.
display={}
for (solver,arm,c,sub,field),v in fields.items():
 if sub==4:display[(solver,arm,c,field)]=np.sum(v*geo[arm]['weights'],axis=1)/geo[arm]['area']
HMIN=1e-4;HMAX=max(v.max() for k,v in display.items() if k[-1]=='H')
HDIFF=max(np.max(np.abs(display[('PIDL',a,c,'H')]-display[('FEM',a,c,'H')])) for a in ARMS for c in CYCLES)
def panel(axis,arm,v,field,difference=False):
 verts=geo[arm]['vertices'];mask=(verts[...,1].min(1)<=.12)&(verts[...,1].max(1)>=-.12)
 if field=='H':norm=TwoSlopeNorm(vmin=-HDIFF,vcenter=0,vmax=HDIFF) if difference else LogNorm(vmin=HMIN,vmax=HMAX)
 else:norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=1) if difference else Normalize(0,1)
 shown=v if difference or field=='F' else np.maximum(v,HMIN)
 p=PolyCollection(verts[mask],array=shown[mask],norm=norm,cmap='RdBu_r' if difference else ('magma' if field=='H' else 'viridis'),edgecolors='none',antialiaseds=False,rasterized=True)
 axis.add_collection(p);axis.set(xlim=(-.5,.5),ylim=(-.12,.12),xlabel='x',ylabel='y');axis.set_aspect('equal')
 return p
def save(fig,name):
 fig.savefig(FIG/(name+'.png'));plt.close(fig)
def field_grid(rows):
 fig=plt.figure(figsize=(13,2.0*rows),layout='constrained')
 gs=fig.add_gridspec(rows,5,width_ratios=[1,1,.045,1,.045])
 ax=np.array([[fig.add_subplot(gs[i,j]) for j in [0,1,3]] for i in range(rows)])
 return fig,ax,fig.add_subplot(gs[:,2]),fig.add_subplot(gs[:,4])
for field in ['H','F']:
 fig,ax,cb1,cb2=field_grid(2)
 for i,arm in enumerate(ARMS):
  a=display[('FEM',arm,83,field)];b=display[('PIDL',arm,83,field)]
  for j,(name,v) in enumerate(zip(['FEM','PIDL','PIDL minus FEM'],[a,b,b-a])):
   p=panel(ax[i,j],arm,v,field,j==2);ax[i,j].set_title(arm.upper()+' '+name)
   if j==0:pa=p
   if j==2:pd=p
 fig.colorbar(pa,cax=cb1,label='Fatigue history (log scale)' if field=='H' else 'Fatigue factor f')
 fig.colorbar(pd,cax=cb2,label='History difference' if field=='H' else 'Factor difference')
 save(fig,'c83_history_post_commit' if field=='H' else 'c83_factor_post_commit')
 for arm in ARMS:
  fig,ax,cb1,cb2=field_grid(3)
  for i,c in enumerate(CYCLES):
   a=display[('FEM',arm,c,field)];b=display[('PIDL',arm,c,field)]
   for j,(name,v) in enumerate(zip(['FEM','PIDL','PIDL minus FEM'],[a,b,b-a])):
    p=panel(ax[i,j],arm,v,field,j==2);ax[i,j].set_title(f'c{c} '+name)
    if j==0:pa=p
    if j==2:pd=p
  fig.colorbar(pa,cax=cb1,label='Fatigue history (shared log scale)' if field=='H' else 'Fatigue factor f (shared scale)')
  fig.colorbar(pd,cax=cb2,label='History difference' if field=='H' else 'Factor difference')
  save(fig,arm+('_history_evolution' if field=='H' else '_factor_evolution'))

fig,ax=plt.subplots(2,2,figsize=(10.2,6.5),constrained_layout=True)
colors={'FEM-q4':'#0072B2','PIDL-q4':'#D55E00','FEM-t3':'#009E73','PIDL-t3':'#CC79A7'}
for solver in ['FEM','PIDL']:
 for arm in ARMS:
  rr=[next(r for r in statistics if r['solver']==solver and r['topology']==arm and r['cycle']==c) for c in CYCLES]
  for a,key in [(ax[0,0],'history_mean'),(ax[0,1],'factor_mean')]:a.plot(CYCLES,[r[key] for r in rr],'-o',lw=1.5,label=solver+'-'+arm.upper(),color=colors[solver+'-'+arm])
for arm,color in [('q4','#0072B2'),('t3','#CC79A7')]:
 for field,a,key in [('H',ax[1,0],'relative_L2'),('F',ax[1,1],'MAE')]:
  for domain,style in [('full','-'),('corridor_abs_y_le_0.03','--')]:
   rr=[next(r for r in gaps if r['topology']==arm and r['cycle']==c and r['field']==field and r['domain']==domain) for c in CYCLES]
   a.plot(CYCLES,[r[key] for r in rr],style+'o',lw=1.4,color=color,label=arm.upper()+(' full' if domain=='full' else ' crack corridor'))
for a,title in zip(ax.flat,['Mean fatigue history','Mean fatigue factor','History relative L2 difference','Factor mean absolute difference']):
 a.set(title=title,xlabel='Physical cycle',xticks=CYCLES);a.grid(alpha=.2);a.legend(fontsize=8)
save(fig,'early_middle_late_metrics')

manifest={'study':'S04-E011 paired Hard-5 existing production','checkpoints':list(CYCLES),'phase':'s4 peak','actual_load_factors':schedule,'FEM_vs_PIDL_load_factor_maxabs':max(abs(r['load_factor']-schedule[r['arm'].lower()][r['substep']-1]) for r in fem_receipts),'main_fields':'after accepted damage and fatigue-history updates','pre_state':'previous accepted s3, not necessarily the coefficient inside FEM trial assembly','history_display_floor':HMIN,'history_display_max':float(HMAX),'history_difference_limits':[-float(HDIFF),float(HDIFF)],'factor_display_limits':[0,1],'factor_difference_limits':[-1,1],'display_reduction':'native GP physical-weighted cell means; f reduced separately from history','metrics':'within-topology native GP values with fixed common physical weights','display_crop_y':[-.12,.12],'descriptive_corridor_abs_y':.03,'fem_receipts':fem_receipts,'pidl_receipts':pidl_receipts,'checks':checks,'source_containers':[],'new_solver_or_training':False,'overleaf_changed':False}
for name in ['fem_history.stdout','pidl_history.npz']:
 p=RAW/name;manifest['source_containers'].append({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ANA/'source_and_timing_audit.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'checks':checks,'statistics':statistics,'gaps':[r for r in gaps if r['domain']=='full'],'history_display_max':HMAX,'history_difference_absmax':HDIFF},indent=2))
