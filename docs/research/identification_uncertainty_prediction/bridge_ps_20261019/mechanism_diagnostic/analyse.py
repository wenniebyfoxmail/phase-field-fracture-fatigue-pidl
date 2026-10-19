"""One bounded arithmetic pass on R003 saved derivatives. No fits or coefficient forwards."""
from pathlib import Path
import argparse,csv,json,re,math,time,warnings,collections
warnings.simplefilter('error')
import numpy as np
np.seterr(all='raise')
SOURCE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-BRIDGE-PS-20261019-R003/retrieved/outputs')
ARMS=('C_RAW','B_STAR','H_INNOV','H_DONOR');HS=(10,40);C30={'C_30Deg_20%_#1','C_30Deg_20%_#2','C_30Deg_20%_#3'}
read_log=[]
def source(name):
 if name not in ('per_case_scores.csv','selectors.json') and not re.fullmatch(r'fold(?:[0-9]|1[0-8])_(?:10|40)_(?:C_RAW|C_REL|H_INNOV|H_DONOR|input_evidence)\.npz',name):raise ValueError('not an authorised derived source')
 p=SOURCE/name;read_log.append({'name':name,'bytes':p.stat().st_size});return p

def save(p,x):
 with Path(p).open('w') as f:json.dump(x,f,indent=2,allow_nan=False)
def avg(x):
 x=list(x);return float(sum(x)/len(x)) if x else None
def ranks(x):
 x=np.asarray(x);order=np.argsort(x,kind='stable');out=np.empty(len(x),float);i=0
 while i<len(x):
  j=i+1
  while j<len(x) and x[order[j]]==x[order[i]]:j+=1
  out[order[i:j]]=(i+j-1)/2.;i=j
 return out

def rho(x,y):
 a,b=ranks(x),ranks(y);a-=a.mean();b-=b.mean();d=float(np.sqrt(np.sum(a*a)*np.sum(b*b)))
 return None if d==0 else float(np.sum(a*b)/d)
def finite(x,label):
 if not np.isfinite(x).all():raise ValueError('nonfinite '+label)
 return x

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);out=p.parse_args().output;start=time.monotonic()
 rec={};meta={};total=0
 fields=['balanced_nmae','full_nmae','local_nmae']+[f'{k}_{ch}' for ch in (0,1) for k in ('pred_mean_increment','ref_mean_increment','mean_increment_error','centered_increment_nmae','pred_l1_normalized','ref_l1_normalized','reference_exact_zero','pred_peak_row','pred_peak_col','ref_peak_row','ref_peak_col')]
 with source('per_case_scores.csv').open(newline='') as f:
  for row in csv.DictReader(f):
   total+=1
   if row['arm'] not in ARMS:continue
   i,h=int(row['case_index']),int(row['horizon_stages']);ident=(row['group'],int(row['origin_stage']))
   if i in meta and meta[i]!=ident:raise ValueError('case identity changed')
   meta[i]=ident;k=(i,h,row['arm'])
   if k in rec:raise ValueError('duplicate case')
   x={n:float(row[n]) for n in fields};finite(list(x.values()),'CSV')
   if any(x[n]<0 for n in fields if n not in [f'{s}_{ch}' for s in ('pred_mean_increment','ref_mean_increment') for ch in (0,1)]):raise ValueError('negative absolute metric')
   for ch in (0,1):
    if x[f'reference_exact_zero_{ch}'] not in (0,1):raise ValueError('zero support identity')
    if (x[f'ref_l1_normalized_{ch}']==0)!=bool(x[f'reference_exact_zero_{ch}']):raise ValueError('reference zero mismatch')
   gm=avg(x[f'mean_increment_error_{ch}'] for ch in (0,1));sc=avg(x[f'centered_increment_nmae_{ch}'] for ch in (0,1))
   if gm>x['full_nmae']+1e-11 or x['full_nmae']>gm+sc+1e-11:raise ValueError('normalised metric semantics')
   rec[k]=x
 groups=sorted({g for g,n in meta.values()});ids={g:sorted(i for i in meta if meta[i][0]==g) for g in groups}
 if total!=22880 or len(rec)!=9152 or len(meta)!=1144 or len(groups)!=19 or not C30<=set(groups):raise ValueError('frozen derived cohort mismatch')
 with source('selectors.json').open() as f:selectors=json.load(f)
 choice={(x['held_group'],int(x['horizon_stages'])):x['chosen'] for x in selectors}
 if len(choice)!=38 or any(v not in ('C_RAW','C_REL') for v in choice.values()):raise ValueError('saved current selector schema')
 print('CSV loaded:19groups,2288cases,4methods; no native targets',flush=True)
 support={};scales={};energy={}
 for fold,g in enumerate(groups):
  for h in HS:
   with np.load(source(f'fold{fold}_{h}_input_evidence.npz'),allow_pickle=False) as z:
    train=z['final_train_indices'].copy();query=z['final_query_indices'].copy();dt=z['final_train_donor_squared_distance'].copy();dq=z['final_query_donor_squared_distance'].copy()
   if list(map(int,query))!=ids[g] or len(dt)!=len(train) or len(dq)!=len(query):raise ValueError('distance/query support mismatch')
   finite(dt,'train distance');finite(dq,'query distance')
   if np.any(dt<0) or np.any(dq<0):raise ValueError('negative squared distance')
   tg=[meta[int(i)][0] for i in train];counts=collections.Counter(tg);w=np.asarray([1./counts[t] for t in tg]);w/=w.sum();order=np.argsort(dt,kind='stable');sd=dt[order];cw=np.cumsum(w[order]);ix=np.searchsorted(sd,dq,side='right')
   pct=np.asarray([0. if j==0 else float(cw[j-1]) for j in ix]);finite(pct,'support ranks')
   for j,i in enumerate(query):support[int(i),h]={'distance':float(dq[j]),'train_cdf':min(1.,float(pct[j]))}
   coarse={};norm=None
   for arm in set(('C_RAW','H_INNOV','H_DONOR',choice[g,h])):
    with np.load(source(f'fold{fold}_{h}_{arm}.npz'),allow_pickle=False) as z:
     ix=z['case_indices'].copy();a=z['coarse_delta'].copy().reshape(len(query),2,16,16);n=z['normalizer'].copy()
     if arm=='H_INNOV':
      tail=z['feature_scale'].copy()[20:]
      if len(tail)!=12 or np.any(tail<=0):raise ValueError('innovation scale schema')
      finite(tail,'innovation training scales')
      for ch in (0,1):scales[g,h,ch]={'training_tail_scale_rms':float(np.sqrt(np.mean(tail[ch::2]**2))),'scale_equal_one_count':int(np.sum(tail[ch::2]==1.))}
    if list(map(int,ix))!=ids[g] or n.shape!=(2,) or np.any(n<=0):raise ValueError('prediction units/cases')
    finite(a,'saved coarse');finite(n,'normalizer')
    if norm is not None and not np.array_equal(norm,n):raise ValueError('normalizer mismatch')
    norm=n;coarse[arm]=a
   coarse['B_STAR']=coarse[choice[g,h]]
   for j,i in enumerate(query):
    i=int(i)
    for arm in ARMS:
     for ch in (0,1):
      mu=float(coarse[arm][j,ch].mean()/norm[ch])
      if abs(mu-rec[i,h,arm][f'pred_mean_increment_{ch}'])>=1e-11:raise ValueError('saved mean/coarse unit mismatch')
    for ref in ('C_RAW','B_STAR'):
     delta=(coarse['H_INNOV'][j]-coarse[ref][j])/norm[:,None,None]
     for ch in (0,1):
      mu=float(delta[ch].mean());sp=float(np.mean((delta[ch]-mu)**2));en=mu*mu
      energy[i,h,ch,ref]={'mean2':en,'space2':sp}
  print(f'derived group {fold+1}/19',flush=True)
 cells={}
 for g in groups:
  for h in HS:
   for ch in (0,1):
    for arm in ARMS:
     xs=[rec[i,h,arm] for i in ids[g]];nonzero=[x for x in xs if x[f'pred_mean_increment_{ch}']!=0 and x[f'ref_mean_increment_{ch}']!=0];peak=[x for x in xs if x[f'pred_l1_normalized_{ch}']>0 and x[f'ref_l1_normalized_{ch}']>0]
     pm=avg(x[f'pred_l1_normalized_{ch}'] for x in xs);tm=avg(x[f'ref_l1_normalized_{ch}'] for x in xs)
     cells[g,h,ch,arm]={'n':len(xs),'balanced':avg(x['balanced_nmae'] for x in xs),'full':avg(x['full_nmae'] for x in xs),'band':avg(x['local_nmae'] for x in xs),'G':avg(x[f'mean_increment_error_{ch}'] for x in xs),'S':avg(x[f'centered_increment_nmae_{ch}'] for x in xs),'pred_mass':pm,'ref_mass':tm,'mass_ratio':None if tm==0 else pm/tm,'sign_error_rate':None if not nonzero else sum(x[f'pred_mean_increment_{ch}']*x[f'ref_mean_increment_{ch}']<0 for x in nonzero)/len(nonzero),'sign_valid_n':len(nonzero),'ref_mean_zero_n':sum(x[f'ref_mean_increment_{ch}']==0 for x in xs),'pred_mean_zero_n':sum(x[f'pred_mean_increment_{ch}']==0 for x in xs),'peak_distance':avg(math.hypot(x[f'pred_peak_row_{ch}']-x[f'ref_peak_row_{ch}'],x[f'pred_peak_col_{ch}']-x[f'ref_peak_col_{ch}']) for x in peak),'peak_valid_n':len(peak),'peak_undefined_n':len(xs)-len(peak)}
 def combine(gs,h,ch,arm):
  cs=[cells[g,h,ch,arm] for g in gs];v={k:avg(x[k] for x in cs if x[k] is not None) for k in ('balanced','full','band','G','S','pred_mass','ref_mass','sign_error_rate','peak_distance')}
  for k in ('n','sign_valid_n','ref_mean_zero_n','pred_mean_zero_n','peak_valid_n','peak_undefined_n'):v[k]=sum(x[k] for x in cs)
  v['mass_ratio']=None if v['ref_mass']==0 else v['pred_mass']/v['ref_mass'];v['groups']=len(gs);v['support_rank']=avg(avg(support[i,h]['train_cdf'] for i in ids[g]) for g in gs);v['support_squared_distance']=avg(avg(support[i,h]['distance'] for i in ids[g]) for g in gs);v['training_tail_scale_rms']=avg(scales[g,h,ch]['training_tail_scale_rms'] for g in gs)
  for ref in ('C_RAW','B_STAR'):
   em=avg(avg(energy[i,h,ch,ref]['mean2'] for i in ids[g]) for g in gs);es=avg(avg(energy[i,h,ch,ref]['space2'] for i in ids[g]) for g in gs);v['change_global_energy_fraction_vs_'+ref]=None if em+es==0 else em/(em+es)
   v['global_mean_error_worse_fraction_vs_'+ref]=avg(avg(float(rec[i,h,'H_INNOV'][f'mean_increment_error_{ch}']>rec[i,h,ref][f'mean_increment_error_{ch}']) for i in ids[g]) for g in gs)
  return v
 scopes=[(g,[g]) for g in groups]+[('ALL',groups),('C30_LABEL',sorted(C30)),('OTHER_LABELS',[g for g in groups if g not in C30])];table=[];summary={}
 for label,gs in scopes:
  for h in HS:
   for ch in (0,1):
    for arm in ARMS:
     v=combine(gs,h,ch,arm);row=dict(scope=label,H=h,channel=ch,method=arm,**v);table.append(row);summary[label,h,ch,arm]=v
 with (out/'decomposition_table.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 correlations={}
 for h in HS:
  xx=[combine([g],h,0,'C_RAW')['support_rank'] for g in groups];yy=[cells[g,h,0,'C_RAW']['balanced']-cells[g,h,0,'H_INNOV']['balanced'] for g in groups]
  correlations[str(h)]={'all19_group_rank_vs_gain_rho':rho(xx,yy),'within_group_case_rho':{g:rho([support[i,h]['train_cdf'] for i in ids[g]],[rec[i,h,'C_RAW']['balanced_nmae']-rec[i,h,'H_INNOV']['balanced_nmae'] for i in ids[g]]) for g in groups}}
 serial={label:{str(h):{str(ch):{arm:summary[label,h,ch,arm] for arm in ARMS} for ch in (0,1)} for h in HS} for label,gs in scopes}
 paired={}
 for label,gs in scopes:
  paired[label]={}
  for h in HS:
   pair={ref:avg(cells[g,h,0,ref]['balanced']-cells[g,h,0,'H_INNOV']['balanced'] for g in gs) for ref in ('C_RAW','B_STAR','H_DONOR')}
   E=avg(cells[g,h,0,'H_INNOV']['full'] for g in gs);G=avg(avg(cells[g,h,ch,'H_INNOV']['G'] for ch in (0,1)) for g in gs);pair['Gmean_over_full_Jensen_bound_ratio_Hinnov']=None if E==0 else G/E
   paired[label][str(h)]=pair
 result={'scope':'posthoc exposed19 groups; saved derivatives only; C30 labels have no inferred physical semantics','groups':groups,'subgroups':{'C30_LABEL':sorted(C30),'OTHER_LABELS':[g for g in groups if g not in C30]},'cells':serial,'paired_gain':paired,'support_correlations':correlations,'missing':['query c/h/innovation vectors not saved: cannot diagnose innovation-direction coverage, conditional collisions or identifiability','native targets forbidden/unavailable: cannot recompute spatial counterfactual MAE or global-mean-only intervention','feature scale==1 may reflect floor; no raw query innovation amplitude','no physical zero/sign/position tolerance established; strict zero/sign and published grid only'],'metrics_notes':['G,S are non-additive L1 diagnostics','Global L2 fraction refers to difference between saved model outputs, not target error','Support CDF is a descriptive training-side distance rank, not OOD probability','Mass ratio is ratio of equal-group normalized means, not mean of per-case ratios','Sign rate conditional on both strict nonzero means; peak undefined when either full-field L1 mass exactly zero','No independent units, CI/p-values, causal proof or new-model prediction'],'read_sources':read_log}
 save(out/'summary.json',result);save(out/'progress.json',{'status':'ARITHMETIC_COMPLETE_RENDERING','elapsed_seconds':time.monotonic()-start})
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(1,3,figsize=(15,9),layout='constrained',gridspec_kw={'width_ratios':[1,2,2]})
 specs=[('Balanced gain',[(h,None) for h in HS],'balanced'),('Mean-increment error gain G',[(h,ch) for h in HS for ch in (0,1)],'G'),('Centered-spatial error gain S',[(h,ch) for h in HS for ch in (0,1)],'S')]
 for ax,(title,columns,metric) in zip(axes,specs):
  arr=np.asarray([[cells[g,h,0 if ch is None else ch,'C_RAW'][metric]-cells[g,h,0 if ch is None else ch,'H_INNOV'][metric] for h,ch in columns] for g in groups]);lim=float(np.abs(arr).max()) or 1.;im=ax.imshow(arr,cmap='RdBu',vmin=-lim,vmax=lim,aspect='auto');ax.set_xticks(range(len(columns)),[f'H{h}'+('' if ch is None else f'/ch{ch}') for h,ch in columns],rotation=45,ha='right');ax.set_yticks(range(19),[f'{j}: {g}' for j,g in enumerate(groups)] if ax is axes[0] else []);ax.set_title(title+'\nC_RAW - H_INNOV; positive better')
  for j,g in enumerate(groups):
   if g in C30:ax.add_patch(Rectangle((-.5,j-.5),len(columns),1,fill=False,edgecolor='black',lw=1.2))
  fig.colorbar(im,ax=ax,shrink=.6,label='Normalized difference; own panel scale')
 fig.suptitle('All19 exposed groups: current versus history innovations; C30 labels outlined\nG and S are NOT additive error shares; original warning-stop breach retained');fig.savefig(out/'mechanism_error_components.png',dpi=160);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
 for ax,h in zip(axes,HS):
  for j,g in enumerate(groups):
   x=combine([g],h,0,'C_RAW')['support_rank'];y=paired[g][str(h)]['C_RAW'];ax.scatter(x,y,marker='^' if g in C30 else 'o',color='#D55E00' if g in C30 else '#0072B2',s=50);ax.annotate(str(j),(x,y),xytext=(3,3),textcoords='offset points',fontsize=7)
  ax.axhline(0,color='black',lw=.7);ax.set(xlim=(-.02,1.02),xlabel='Mean query distance rank in training distance CDF',ylabel='L(C_RAW)-L(H_INNOV)',title=f'H{h}: all19 group means; orange triangles=C30 labels')
 fig.suptitle('Input support proxy versus prediction gain: association only; no OOD threshold or fitted trend');fig.savefig(out/'mechanism_support_gain.png',dpi=160);plt.close(fig)
 fig,axes=plt.subplots(4,3,figsize=(15,12),sharey='row',layout='constrained')
 for col,g in enumerate(sorted(C30)):
  order=sorted(ids[g],key=lambda i:meta[i][1]);ns=[meta[i][1] for i in order]
  for rr,(h,ch) in enumerate([(10,0),(10,1),(40,0),(40,1)]):
   ax=axes[rr,col]
   for arm,key,label,color in [('C_RAW','ref','Saved reference','black'),('C_RAW','pred','C_RAW','#888888'),('H_INNOV','pred','H_INNOV','#0072B2')]:ax.plot(ns,[rec[i,h,arm][f'{key}_mean_increment_{ch}'] for i in order],label=label,color=color,lw=1.)
   ax.axhline(0,color='black',lw=.5,ls=':');ax.set_title(f'{g};H{h};channel{ch}');ax.set_xlabel('Origin release stage');ax.set_ylabel('Mean increment / saved train scale')
   if rr==0 and col==0:ax.legend(fontsize=8)
 fig.suptitle('Every origin in all3 preidentified C30-label groups: saved signed means\nConnected conditional readouts are NOT autonomous rollout; no selected example or physical angle claim');fig.savefig(out/'mechanism_C30_all_mean_curves.png',dpi=140);plt.close(fig)
 save(out/'arithmetic_receipt.json',{'status':'COMPLETE_SAVED_DERIVATIVE_DIAGNOSTIC','elapsed_seconds':time.monotonic()-start,'source_files':len(read_log),'table_rows':len(table),'figures':3,'scientific_fit_or_forward':False,'native_target_read':False,'coefficient_read_or_forward':False,'warning_contract_breach_of_R003_preserved':True})
 print('COMPLETE: bounded saved-output arithmetic and3 figures',flush=True)

if __name__=='__main__':main()
