"""Deterministic reporting reductions of stored fields; no solver/training imports."""
from pathlib import Path
import base64,csv,json,hashlib
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import TwoSlopeNorm,LogNorm
from matplotlib.collections import PolyCollection

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=ROOT/'local_archive/report_ch4_revision_20261015'
OLD=ROOT/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z'
RAW=OUT/'raw'; ANA=OUT/'analysis'; FIG=OUT/'figures'
for p in [ANA,FIG]:p.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.titlesize':10,'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':200})

def writecsv(name,rows):
    with (ANA/name).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def quantile(x,w,q):
    order=np.argsort(x);xx=x[order];ww=w[order]
    return float(xx[np.searchsorted(np.cumsum(ww)/ww.sum(),q)])

def stats(d,w):
    return {'weighted_nodal_mean':float(np.sum(w*d,dtype=np.float64)/w.sum()),'weighted_nodal_p99':quantile(d,w,.99),'minimum':float(d.min()),'maximum':float(d.max()),'negative_node_fraction':float(np.mean(d<0)),'above_one_node_fraction':float(np.mean(d>1))}

def diffstats(a,b,w):
    d=b-a;norm=float(np.sqrt(np.sum(w*a*a)));sq=float(np.sum(w*d*d));return {'weighted_MAE':float(np.sum(w*np.abs(d))/w.sum()),'weighted_RMSE':float(np.sqrt(sq/w.sum())),'weighted_relative_L2':float(np.sqrt(sq)/norm),'weighted_abs_p99':quantile(np.abs(d),w,.99),'max_abs_difference':float(np.abs(d).max())}

text=(RAW/'fem_read.stdout').read_text()
fem={}; meta={};eventrows=[]
for arm in ['Q4','T3']:
    for line in text.splitlines():
        if line.startswith('INITIAL_DAMAGE_'+arm+'='):d=np.frombuffer(base64.b64decode(line.split('=',1)[1]),dtype='<f8').copy()
        if line.startswith('INITIAL_COORDS_'+arm+'='):xy=np.frombuffer(base64.b64decode(line.split('=',1)[1]),dtype='<f8').reshape((86756,-1),order='F').copy()
        if line.startswith('METADATA_'+arm+'='):meta[arm]=json.loads(line.split('=',1)[1])
        if line.startswith('EVENT,'+arm+','):
            r=line.split(',');eventrows.append({'arm':'FEM-'+arm,'cycle':int(r[2]),'global_step':5*int(r[2])-1,'substep':4,'qualifying_nodes':int(r[3]),'trigger':int(int(r[3])>=3),'damage_min':float(r[4]),'damage_max':float(r[5]),'source_bytes':int(r[6]),'source_mtime_matlab_datenum':float(r[7])})
    fem[arm]={'d':d,'xy':xy[:,:2]}
    assert np.isfinite(d).all() and len(d)==86756

z=np.load(RAW/'pidl_all_peaks.npz',allow_pickle=False)
receipt=json.loads(str(z['receipt_json']))
mesh=Path('/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/hard5_u012_q4_t3_unaligned_baseline_handoff_20261005_v1/mesh/canonical_mesh_geometry.mat')
with h5py.File(mesh) as h:
    xy=h['node_coords'][()].T;cells=h['connectivity_q4'][()].T.astype(int)-1
assert xy.shape==(86756,2) and cells.shape==(86408,4)
coordinate_checks={}
for a in ['Q4','T3']:
    coordinate_checks['FEM-'+a]=float(np.max(np.abs(fem[a]['xy']-xy)))
    coordinate_checks['PIDL-'+a]=float(np.max(np.abs(z['coords_'+a.lower()]-xy)))
    assert np.array_equal(fem[a]['xy'][:,0]>.48,xy[:,0]>.48)
    assert np.array_equal(z['coords_'+a.lower()][:,0]>.48,xy[:,0]>.48)
assert max(coordinate_checks.values())<1e-7,coordinate_checks

# One common nodal measure for all four arms: Q4 consistent row-sum mass.
g=1/np.sqrt(3);gp=[(g,g),(-g,g),(g,-g),(-g,-g)]
mass=np.zeros(len(xy));areas=np.zeros(len(cells));e=xy[cells]
for xi,eta in gp:
    N=.25*np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])
    D=.25*np.array([[-(1-eta),(1-eta),(1+eta),-(1+eta)],[-(1-xi),-(1+xi),(1+xi),(1-xi)]])
    jac=np.einsum('ij,ejk->eik',D,e);w=np.linalg.det(jac);assert np.all(w>0)
    areas+=w
    for j in range(4): np.add.at(mass,cells[:,j],N[j]*w)
assert abs(mass.sum()-1)<1e-10

initial={};statrows=[];historyrows=[]
for a in ['Q4','T3']:
    initial['FEM-'+a]=fem[a]['d'];initial['PIDL-'+a]=z['damage_'+a.lower()][0].astype(float)
    for solver in ['FEM','PIDL']:
        arm=solver+'-'+a;statrows.append({'arm':arm,**stats(initial[arm],mass)})
    historyrows.append({'arm':'FEM-'+a,'fatigue_history_min':meta[a]['alpha_bar_initial'],'fatigue_history_max':meta[a]['alpha_bar_initial'],'previous_active_min':meta[a]['driver_degraded_initial'],'previous_active_max':meta[a]['driver_degraded_initial'],'fatigue_factor_min':meta[a]['f_alpha_initial'],'fatigue_factor_max':meta[a]['f_alpha_initial'],'evidence':'saved initial-state metadata plus producer reset code; state0 field file stores damage only'})
    hist=z['initial_hist_fat_'+a.lower()];prev=z['initial_previous_active_'+a.lower()]
    assert np.max(np.abs(hist))==0 and np.max(np.abs(prev))==0
    historyrows.append({'arm':'PIDL-'+a,'fatigue_history_min':float(hist.min()),'fatigue_history_max':float(hist.max()),'previous_active_min':float(prev.min()),'previous_active_max':float(prev.max()),'fatigue_factor_min':1.,'fatigue_factor_max':1.,'evidence':'history and previous driver read from checkpoint; factor recomputed from stored zero history and the declared law'})
    d=z['damage_'+a.lower()];mask=z['coords_'+a.lower()][:,0]>.48
    assert d.shape==(121,86756)
    records=receipt[a.lower()]['sources']
    for c in range(1,121):
        n=int((d[c,mask]>.95).sum());r=records[c]
        eventrows.append({'arm':'PIDL-'+a,'cycle':c,'global_step':5*c-1,'substep':4,'qualifying_nodes':n,'trigger':int(n>=3),'damage_min':float(d[c].min()),'damage_max':float(d[c].max()),'source_bytes':r['bytes'],'source_mtime_matlab_datenum':None})

comparisons=[]
for reference,candidate in [('FEM-Q4','PIDL-Q4'),('FEM-T3','PIDL-T3'),('FEM-Q4','FEM-T3'),('PIDL-Q4','PIDL-T3')]:
    comparisons.append({'reference':reference,'candidate':candidate,**diffstats(initial[reference],initial[candidate],mass)})

# Independent event reconstruction: no previous labels used in this calculation.
events=[]
for arm in ['FEM-Q4','FEM-T3','PIDL-Q4','PIDL-T3']:
    rows=sorted([r for r in eventrows if r['arm']==arm],key=lambda r:r['cycle'])
    assert [r['cycle'] for r in rows]==list(range(1,121))
    hits=[r for r in rows if r['trigger']]
    first=hits[0]['cycle'] if hits else None;confirm=first+3 if first is not None and first+3<=120 else None
    events.append({'arm':arm,'peak_states_checked':120,'first_detection_cycle':first,'first_detection_global_step':5*first-1 if first else None,'confirmation_cycle':confirm,'confirmation_global_step':5*confirm-1 if confirm else None,'qualifying_nodes_at_first':hits[0]['qualifying_nodes'] if hits else None,'post_first_predicate_false_cycles':';'.join(str(r['cycle']) for r in rows if first and r['cycle']>first and not r['trigger'])})

# Cross-check independent checkpoint extraction against previously exported network outputs.
crosschecks=[]
for a in ['q4','t3']:
    old=np.load(OLD/f'analysis/multicycle_cross_replay/pidl_nodal/pidl_{a}_nodal_trajectory.npz')
    diffs=[float(np.max(np.abs(z['damage_'+a][int(c)]-d))) for c,d in zip(old['cycles'],old['d_node'])]
    assert max(diffs)==0,(a,diffs)
    crosschecks.append({'arm':'PIDL-'+a.upper(),'old_nodal_export_states_checked':len(diffs),'maximum_absolute_difference':max(diffs),'saved_alpha_snapshot_exact_matches':len(receipt[a]['snapshot_exact_match_steps'])})

writecsv('initial_damage_statistics.csv',statrows);writecsv('initial_field_differences.csv',comparisons);writecsv('initial_history_checks.csv',historyrows)
writecsv('all_peak_event_counts.csv',eventrows);writecsv('unified_events.csv',events);writecsv('checkpoint_validation.csv',crosschecks)
np.savez_compressed(ANA/'initial_fields.npz',coords=xy,cells=cells,common_nodal_mass=mass,**{k.replace('-','_'):v for k,v in initial.items()})

# Same-node area-aware comparison; raw damage extrema are retained in the tables.
triangles=np.vstack((cells[:,[0,1,2]],cells[:,[0,2,3]]));tri=mtri.Triangulation(xy[:,0],xy[:,1],triangles)
fig,ax=plt.subplots(2,2,figsize=(9,3.8),constrained_layout=True)
for axis,arm in zip(ax.flat,['FEM-Q4','PIDL-Q4','FEM-T3','PIDL-T3']):
    p=axis.tripcolor(tri,initial[arm],shading='gouraud',vmin=0,vmax=1,cmap='viridis',rasterized=True)
    axis.set(title=arm,xlabel='x',ylabel='y',xlim=(-.5,.5),ylim=(-.12,.12));axis.set_aspect('equal')
fig.colorbar(p,ax=ax,label='Recovered damage d; displayed range [0, 1]',shrink=.8)
fig.savefig(FIG/'initial_damage_four_arms.png');fig.savefig(FIG/'initial_damage_four_arms.pdf');plt.close(fig)

fig,ax=plt.subplots(1,2,figsize=(9,2.3),constrained_layout=True)
limit=max(float(np.max(np.abs(initial['PIDL-'+a]-initial['FEM-'+a]))) for a in ['Q4','T3'])
for axis,a in zip(ax,['Q4','T3']):
    p=axis.tripcolor(tri,initial['PIDL-'+a]-initial['FEM-'+a],shading='gouraud',cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),rasterized=True)
    axis.set(title=a+': PIDL minus FEM',xlabel='x',ylabel='y',xlim=(-.5,.5),ylim=(-.12,.12));axis.set_aspect('equal')
fig.colorbar(p,ax=ax,label='Initial damage difference',shrink=.8)
fig.savefig(FIG/'initial_damage_differences.png');fig.savefig(FIG/'initial_damage_differences.pdf');plt.close(fig)

fig,ax=plt.subplots(2,1,figsize=(8,5.8),sharex=True,constrained_layout=True)
colors=['#0072B2','#009E73','#D55E00','#CC79A7']
for row,color in zip(events,colors):
    arm=row['arm'];rr=sorted([r for r in eventrows if r['arm']==arm],key=lambda r:r['cycle']);cs=[r['cycle'] for r in rr];ns=[r['qualifying_nodes'] for r in rr]
    ax[0].step(cs,ns,where='post',label=arm,color=color,lw=1.5)
    ax[1].plot([row['first_detection_cycle'],row['confirmation_cycle']],[arm,arm],color=color,lw=1.5)
    ax[1].scatter(row['first_detection_cycle'],arm,color=color,marker='o',s=35)
    ax[1].scatter(row['confirmation_cycle'],arm,color=color,marker='s',facecolors='none',s=35)
ax[0].axhline(3,color='.3',ls='--',lw=1,label='Detection threshold: 3 nodes');ax[0].set(ylabel='Nodes with x > 0.48 and d > 0.95',title='All 120 peak states checked in each arm');ax[0].legend(ncol=2,fontsize=8)
ax[1].set(xlabel='Physical cycle',title='First detection (circle) and three-cycle confirmation label (square)',xlim=(1,120));ax[1].grid(axis='x',alpha=.2)
fig.savefig(FIG/'unified_event_timeline.png');fig.savefig(FIG/'unified_event_timeline.pdf');plt.close(fig)

# Replace the old eight-step damage residual panels with October Hard-5 outputs.
fig,ax=plt.subplots(2,3,figsize=(10.5,3.6),constrained_layout=True)
resmax=0.;fields={}
for a in ['Q4','T3']:
    with h5py.File(OLD/f'analysis/multicycle_cross_replay/fem_nodal/fem_{a.lower()}_nodal_trajectory.mat') as h:
        cs=h['cycles'][()].reshape(-1).astype(int);f=h['d_node'][()][np.flatnonzero(cs==83)[0]]
    p=z['damage_'+a.lower()][83];fields[a]=(f,p,p-f);resmax=max(resmax,float(np.max(np.abs(p-f))))
for i,a in enumerate(['Q4','T3']):
    for j,(title,d) in enumerate(zip(['FEM','PIDL','PIDL minus FEM'],fields[a])):
        kwargs=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-resmax,vcenter=0,vmax=resmax)) if j==2 else dict(cmap='viridis',vmin=0,vmax=1)
        pp=ax[i,j].tripcolor(tri,d,shading='gouraud',rasterized=True,**kwargs);ax[i,j].set(title=a+' '+title,xlabel='x',ylabel='y',ylim=(-.12,.12),xlim=(-.5,.5));ax[i,j].set_aspect('equal')
        if i==0 and j==0:dam=pp
        if j==2:res=pp
fig.colorbar(dam,ax=ax[:,:2],label='Damage d; displayed [0, 1]',shrink=.75);fig.colorbar(res,ax=ax[:,2],label='Damage difference',shrink=.75)
fig.savefig(FIG/'hard5_c83_damage_comparison.png');fig.savefig(FIG/'hard5_c83_damage_comparison.pdf');plt.close(fig)

# The corrected Q4 active field: multiply at GP level before cell reduction.
zz=np.load(OLD/'analysis/c83_q4_mechanism/fields.npz')
fig,ax=plt.subplots(1,3,figsize=(10.5,2.6),constrained_layout=True)
ff=zz['fem_active_elem'];pp=zz['pidl_active_elem'];dd=pp-ff
mx=max(float(ff.max()),float(pp.max()));dm=float(np.abs(dd).max())
for axis,name,data in zip(ax,['FEM-Q4','PIDL-Q4','PIDL minus FEM'],[ff,pp,dd]):
    norm=TwoSlopeNorm(vmin=-dm,vcenter=0,vmax=dm) if name=='PIDL minus FEM' else LogNorm(vmin=1e-12,vmax=mx)
    display=data if name=='PIDL minus FEM' else np.maximum(data,1e-12)
    col=PolyCollection(xy[cells],array=display,cmap='RdBu_r' if name=='PIDL minus FEM' else 'magma',norm=norm,edgecolors='none',rasterized=True)
    axis.add_collection(col);axis.set(xlim=(-.5,.5),ylim=(-.12,.12),xlabel='x',ylabel='y',title=name);axis.set_aspect('equal')
    if name=='FEM-Q4':active=col
    if name=='PIDL minus FEM':diff=col
fig.colorbar(active,ax=ax[:2],label='Active energy density (log scale)',shrink=.8)
fig.colorbar(diff,ax=ax[2],label='Active energy density difference',shrink=.8)
fig.savefig(FIG/'hard5_c83_active_q4.png');fig.savefig(FIG/'hard5_c83_active_q4.pdf');plt.close(fig)

result={'schema':'fyr-ch4-existing-output-review-v1','event_rule':{'x_strictly_greater_than':.48,'damage_strictly_greater_than':.95,'minimum_nodes':3,'phase':'peak s4','confirmation_delay_physical_cycles':3},'events':events,'initial_statistics':statrows,'initial_differences':comparisons,'coordinate_max_abs':coordinate_checks,'common_nodal_mass_sum':float(mass.sum()),'initial_history':historyrows,'checkpoint_validation':crosschecks,'fem_initial_metadata':meta,'coverage':'4 arms x 120 peaks; stored damage only, no network evaluation or solver execution','weights':'One common Q4 row-sum mass; reported statistics are nodal weighted statistics, not native-GP field norms','figure_crop':'damage panels show y in [-0.12,0.12]; statistics use the full domain','producer_files_changed':False}
(ANA/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
(ANA/'pidl_source_receipts.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'events':events,'initial_statistics':statrows,'initial_differences':comparisons,'checkpoint_validation':crosschecks},indent=2))
