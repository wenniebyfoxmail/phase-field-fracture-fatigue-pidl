"""Diagnostics and plots from saved predictions; not extra fits or a physical-success gate."""
from pathlib import Path
import json
import contract

def diagnostic(pred_delta,true_delta,norm,center):
 import numpy as np
 from state import finite
 pred_delta,true_delta=finite(pred_delta),finite(true_delta);out={};lo=max(0,center-16);hi=min(128,center+17)
 for ch in range(2):
  p,t=pred_delta[ch],true_delta[ch];s=norm[ch];pm=float(np.abs(p).mean());tm=float(np.abs(t).mean())
  out.update({f'pred_mean_increment_{ch}':float(p.mean()/s),f'ref_mean_increment_{ch}':float(t.mean()/s),f'mean_increment_error_{ch}':float(abs(p.mean()-t.mean())/s),
    f'centered_increment_nmae_{ch}':float(np.abs((p-p.mean())-(t-t.mean())).mean()/s),
    f'pred_l1_normalized_{ch}':pm/s,f'ref_l1_normalized_{ch}':tm/s,
    f'l1_mass_ratio_{ch}':None if tm==0 else pm/tm,f'reference_exact_zero_{ch}':int(tm==0),
    f'pred_positive_mass_{ch}':float(np.maximum(p,0).mean()/s),f'pred_negative_mass_{ch}':float(np.maximum(-p,0).mean()/s),
    f'ref_positive_mass_{ch}':float(np.maximum(t,0).mean()/s),f'ref_negative_mass_{ch}':float(np.maximum(-t,0).mean()/s)})
  for label,x in (('pred_peak',p),('ref_peak',t),('max_error',p-t)):
   band=np.abs(x[lo:hi]);y,col=np.unravel_index(np.argmax(band),band.shape)
   out[f'{label}_row_{ch}']=int(y+lo);out[f'{label}_col_{ch}']=int(col);out[f'{label}_amplitude_{ch}']=float(band[y,col]/s)
 for v in out.values():
  if v is not None and not np.isfinite(v):raise ValueError('nonfinite diagnostic')
 return out

def analyse(out,rows,groups,cfg):
 import numpy as np
 from collections import defaultdict
 cells=defaultdict(list)
 for r in rows:cells[(r['arm'],r['group'],r['horizon_stages'])].append(r)
 means={k:float(np.mean([r['balanced_nmae'] for r in v])) for k,v in cells.items()}
 arms=sorted({r['arm'] for r in rows});primary={a:float(np.mean([means[(a,g,h)] for g in groups for h in (10,40)])) for a in arms}
 effect=np.asarray([np.mean([means[('B_STAR',g,h)]-means[('H_INNOV',g,h)] for h in (10,40)]) for g in groups]);byh={str(h):float(np.mean([means[('B_STAR',g,h)]-means[('H_INNOV',g,h)] for g in groups])) for h in (10,40)}
 loo=np.asarray([np.delete(effect,i).mean() for i in range(len(groups))]);rng=np.random.default_rng(20261019);draws=effect[rng.integers(len(groups),size=(10000,len(groups)))].mean(1)
 np.savez_compressed(Path(out)/'group_reweighting_draws.npz',draws=draws,paired_group_effect=effect,leave_one_group_out=loo)
 result={'primary_loss':primary,'primary_delta_Bstar_minus_Hinnov':float(effect.mean()),'paired_group_effect':dict(zip(groups,map(float,effect))),
  'per_horizon_delta':byh,'group_effect_range':[float(effect.min()),float(effect.max())],
  'leave_one_group_out_delta':dict(zip(groups,map(float,loo))),'leave_one_group_out_range':[float(loo.min()),float(loo.max())],
  'donor_minus_innov':primary['H_DONOR']-primary['H_INNOV'],
  'reweighting':{'unit':'released_group','draws':10000,'seed':20261019,'full_range':[float(draws.min()),float(draws.max())],'percentiles_2_5_97_5':list(map(float,np.percentile(draws,[2.5,97.5]))),'interpretation':'empirical benchmark reweighting sensitivity; NOT a population confidence interval'},
  'numeric_direction_flags':{'positive_primary_mean':bool(effect.mean()>1e-11),'both_horizons_positive':all(x>1e-11 for x in byh.values()),'all_leave_one_group_out_positive':bool((loo>1e-11).all()),'donor_mean_above_true_history':bool(primary['H_DONOR']-primary['H_INNOV']>1e-11)},
  'reference_R002_nominal_gap':.006723233424717502,'scope':'19 exposed release groups; common native current-field anchor; no fatigue-memory, physical-state-sufficiency, independent-specimen or road claim'}
 contract.write(Path(out)/'analysis.json',result)
 from worker import rows_write
 grouped=[dict(arm=k[0],group=k[1],horizon_stages=k[2],balanced_nmae=v,full_nmae=float(np.mean([r['full_nmae'] for r in cells[k]])),local_nmae=float(np.mean([r['local_nmae'] for r in cells[k]]))) for k,v in means.items()]
 rows_write(Path(out)/'group_horizon_scores.csv',grouped)

def render(out,rows,cases,groups,selectors,loader,frames,cfg):
 import numpy as np
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from state import ARMS
 out=Path(out);figs=out/'figures';figs.mkdir()
 lookup={(r['arm'],r['group'],r['horizon_stages'],r['case_index']):r for r in rows}
 choices={(s['held_group'],s['horizon_stages']):s['chosen'] for s in selectors};selected=[]
 def field(i,arm,h,fold):
  c=cases[i];g,n=c['group'],c['origin_stage'];current=loader.get(frames[(g,n)])
  if arm=='P':return current
  if arm=='S':return current+(current-loader.get(frames[(g,n-10)]))*h/10.
  with np.load(out/f'fold{fold}_{h}_{arm}.npz',allow_pickle=False) as z:
   k=list(z['case_indices']).index(i);d=z['coarse_delta'][k].reshape(2,16,16)
  return current+np.repeat(np.repeat(d,8,1),8,2)
 summary=contract.read(out/'analysis.json');effect=summary['paired_group_effect']
 fig,ax=plt.subplots(figsize=(11,5));ax.bar(range(19),[effect[g] for g in groups]);ax.axhline(0,color='black',lw=.8);ax.set(xlabel='Released group index (physical independence unknown)',ylabel='L(B*) - L(H_INNOV); positive favors history',title='Primary paired group effect, mean over H10/H40');fig.tight_layout();fig.savefig(figs/'primary_group_effect.png',dpi=150);plt.close(fig)
 for fold,g in enumerate(groups):
  ids=[i for i,c in enumerate(cases) if c['group']==g]
  for h in (10,40):
   for tag,i in [('midpoint',ids[len(ids)//2]),('worst_H_INNOV',max(ids,key=lambda j:(lookup[('H_INNOV',g,h,j)]['balanced_nmae'],-j)))]:
    c=cases[i];n=c['origin_stage'];current=loader.get(frames[(g,n)]);future=loader.get(frames[(g,n+h)]);bstar=field(i,choices[(g,h)],h,fold);innov=field(i,'H_INNOV',h,fold)
    selected.append({'group':g,'horizon_stages':h,'case_index':i,'origin_stage':n,'rule':tag,'Bstar_method':choices[(g,h)]})
    fig,ax=plt.subplots(4,3,figsize=(11,13),constrained_layout=True)
    for ch in (0,1):
     arr=[future[ch]-current[ch],bstar[ch]-current[ch],innov[ch]-current[ch],np.abs(bstar[ch]-future[ch]),np.abs(innov[ch]-future[ch]),np.abs(future[ch]-current[ch])]
     lim=max(float(np.abs(x).max()) for x in arr[:3]) or 1e-9;el=max(float(x.max()) for x in arr[3:]) or 1e-9
     titles=['True released increment','B* increment','H_INNOV increment','B* absolute error','H_INNOV absolute error','Persistence absolute error']
     for j,(x,title) in enumerate(zip(arr,titles)):
      q=ax[ch*2+j//3,j%3];im=q.imshow(x,cmap='RdBu_r' if j<3 else 'magma',vmin=-lim if j<3 else 0,vmax=lim if j<3 else el)
      for y in (max(0,c['center_row']-16),min(127,c['center_row']+16)):q.axhline(y,color='lime',lw=.7)
      q.set_title(f'channel {ch}: {title}',fontsize=9);q.set_xlabel('published column');q.set_ylabel('published row');fig.colorbar(im,ax=q,fraction=.046)
    fig.suptitle(f'{g}; n={n}; H={h} release steps; {tag}; no physical crack truth',fontsize=10);fig.savefig(figs/f'field_g{fold}_H{h}_{tag}.png',dpi=120);plt.close(fig)
   fig,axs=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
   # Every origin-to-horizon forecast is an independent observed-prefix conditional forecast, not an autonomous rollout.
   for ch,q in enumerate(axs):
    for arm,label,col in [('B_STAR','B*','#777777'),('H_INNOV','H_INNOV','#0072B2')]:
     vals=[lookup[(arm,g,h,i)][f'pred_mean_increment_{ch}'] for i in ids];q.plot([cases[i]['origin_stage']+h for i in ids],vals,label=label,color=col,lw=1.3)
    q.plot([cases[i]['origin_stage']+h for i in ids],[lookup[('H_INNOV',g,h,i)][f'ref_mean_increment_{ch}'] for i in ids],label='True released increment',color='black',lw=1.3)
    q.set(xlabel=f'Forecast target release stage (origin + {h})',ylabel='Channel mean increment / train scale',title=f'channel {ch}: origin-to-H readout');q.legend()
   fig.suptitle(f'{g}; H{h}; repeated observed-prefix forecasts, NOT autonomous rollout');fig.savefig(figs/f'origin_to_H_g{fold}_H{h}.png',dpi=130);plt.close(fig)
 contract.write(out/'figure_selection.json',{'rule':'Every group and both horizons; fixed median retained origin plus worst H_INNOV case (post-hoc failure diagnosis, ties lower index)','cases':selected})
