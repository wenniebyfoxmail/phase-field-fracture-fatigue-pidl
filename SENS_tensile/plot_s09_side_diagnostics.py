"""Render exact assessed outputs; no model inference, scoring changes or training."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from scipy.spatial import cKDTree

p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
paths=sorted(x for x in a.runs.iterdir() if (x/'output/best_windows.csv').exists())
colors=['#0072B2','#E69F00','#009E73','#CC79A7','#D55E00','#56B4E9']
summary=[];fig,ax=plt.subplots(1,2,figsize=(13,5),layout='constrained')
fields=[]
for i,r in enumerate(paths):
 receipt=json.loads((r/'output/receipt.json').read_text());arm=receipt['config']['diagnostic_arm']
 evaluations=[]
 for line in (r/'logs/train.log').read_text().splitlines():
  try:v=json.loads(line)
  except ValueError:continue
  if isinstance(v,dict) and 'step' in v:evaluations.append(v)
 steps=[v['step'] for v in evaluations];ratios=[v['metrics']['increment_mae_ratio'] for v in evaluations]
 rows=list(csv.DictReader((r/'output/best_windows.csv').open()));score=sum(float(x['error']) for x in rows)/sum(float(x['growth']) for x in rows)
 m=json.loads((r/'output/best_metrics.json').read_text());assert abs(score-m['increment_mae_ratio'])<1e-10
 f=np.load(r/'output/best_fixed_window.npz');assert int(f['origin_index'])==95
 assert str(f['trajectory_id'])=='hard5_u011'
 summary.append({'run_id':r.name,'arm':arm,'windows':len(rows),'updates':receipt['updates'],'best_step':int(f['checkpoint_step']),'ratio':score,'pass':score<=.8,'elapsed_seconds':receipt['elapsed_seconds']})
 ax[0].plot(steps,ratios,label=f"{arm} (n={len(rows)})",color=colors[i],lw=1.3)
 xs=[j for j in range(16)] if len(rows)==16 else [8]
 ax[1].scatter(np.array(xs)+.06*(i-2.5),[float(x['ratio']) for x in rows],label=arm,color=colors[i],s=20,alpha=.8)
 fields.append((r.name,arm,{k:f[k] for k in f.files}))
for z in ax:
 z.axhline(1,color='black',ls='--',lw=1,label='persistence = 1');z.axhline(.8,color='#777777',ls=':',lw=1.3,label='fit threshold = 0.8');z.set_yscale('log');z.grid(alpha=.15);z.set_ylabel('Area-weighted damage MAE / persistence (lower better)')
ax[0].set_xlabel('Optimizer updates');ax[0].set_title('Every assessed checkpoint; no smoothing');ax[0].legend(fontsize=8,ncol=2)
ax[1].set_xlabel('Original training-window list index (not independent units)');ax[1].set_xticks(range(16));ax[1].set_title('All evaluated windows at each arm best checkpoint')
fig.suptitle('S09 SIDE DIAG | synthetic, seen training windows | one-step peak transition | seed 1',fontsize=12)
for ext in ['png','pdf']:fig.savefig(a.out/f'decision.{ext}',dpi=170)
plt.close(fig)
with (a.out/'decision.csv').open('w') as h:
 w=csv.DictWriter(h,fieldnames=summary[0].keys());w.writeheader();w.writerows(summary)
vmax=max(float(max(np.max(f['true_increment']),np.max(f['pred_increment']))) for _,_,f in fields)
xy0=fields[0][2]['xy'];lo=xy0.min(0);hi=xy0.max(0)
gx,gy=np.meshgrid(np.linspace(lo[0],hi[0],600),np.linspace(lo[1],hi[1],600))
nearest=cKDTree(xy0).query(np.column_stack([gx.ravel(),gy.ravel()]))[1]
fig,ax=plt.subplots(len(fields),3,figsize=(10,3.1*len(fields)),layout='constrained',squeeze=False)
norm=PowerNorm(.3,vmin=0,vmax=vmax)
for i,(run,arm,f) in enumerate(fields):
 xy=f['xy'];true=f['true_increment'];pred=f['pred_increment']
 for j,(label,val) in enumerate([('Reference increment',true),('Predicted increment',pred),('Persistence increment',np.zeros_like(true))]):
  assert np.array_equal(xy,xy0)
  artist=ax[i,j].imshow(val[nearest].reshape(gx.shape),origin='lower',extent=[lo[0],hi[0],lo[1],hi[1]],cmap='magma',norm=norm,interpolation='nearest')
  ax[i,j].set_aspect('equal');ax[i,j].set_xlabel('x (native specimen coordinate)');ax[i,j].set_ylabel('y');ax[i,j].set_title(label,fontsize=9)
 ax[i,0].text(-.35,.5,f'{run}\n{arm}\nbest step {int(f["checkpoint_step"])}',transform=ax[i,0].transAxes,rotation=90,ha='center',va='center',fontsize=8)
fig.colorbar(artist,ax=ax.ravel().tolist(),label='Damage increment (dimensionless); shared power scale gamma=0.3',shrink=.75)
fig.suptitle('Fixed U011 origin index95 (stored peak96) -> next peak\nFull domain, nearest-centroid display; all arms; seen training example, not morphology validation',fontsize=11)
for ext in ['png','pdf']:fig.savefig(a.out/f'fixed_fields.{ext}',dpi=160)
plt.close(fig)
print(json.dumps(summary,indent=2))
