"""Passive E018 saved-array verification and complete matched-region analysis."""
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
REPO=OUT.parents[3]
sys.path.insert(0,str(REPO/'SENS_tensile'))
from run_s04_e018_global_local_screen import validate_reference, US
PROJECT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
RAW=PROJECT/'local_archive/experiments/S04-E018/runs/S04-E018-R007-posthoc'
BUNDLE=RAW/'retrieved'
REFS=PROJECT/'local_archive/experiments/S04-E013/runs/S04-E013-stage1-matrix-769396f-20261008T230420Z/http_inputs'
STATES=('c20s4','c60s4','c83s4'); ARMS=('control','localized')
KEYS=('displacement_mass_rms_over_abs_Us','damage_conditional_rms_over_abs_Us','background_conditional_rms_over_abs_Us')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def csvwrite(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
s=json.loads((BUNDLE/'aggregate/summary.json').read_text()); assert s['valid_completed_runs']==6 and not s['missing'] and not s['integrity_errors']
refs={state:validate_reference(state,REFS/f'{state}.npz') for state in STATES}
traces={}; rows=[]; receipts=[]; audit=[]; support_rows=[]
for run in sorted((BUNDLE/'runs').iterdir()):
    receipt=json.loads((run/'RUN_RECEIPT.json').read_text()); state,arm=receipt['state'],receipt['arm']; key=(state,arm)
    assert key not in traces and receipt['dirty'] is False and receipt['code_commit']==s['code_commit']
    for name,hkey in [('metrics.json','metrics_sha256'),('prediction.npz','prediction_sha256'),('monitoring.json','monitoring_sha256')]: assert sha(run/name)==receipt[hkey]
    d=refs[state]; assert receipt['reference_sha256']==d['reference_sha256']
    with np.load(run/'prediction.npz') as p: uv=p['uv'].copy()
    w=d['mass']/d['mass'].sum(); mask=d['damage']>.1
    err=((uv-d['equilibrated_uv'])**2).sum(1)/abs(US)**2
    ca=float(np.sum(w[mask]*err[mask])); cb=float(np.sum(w[~mask]*err[~mask])); pa=w[mask].sum()
    values=[np.sqrt(ca+cb),np.sqrt(ca/pa),np.sqrt(cb/(1-pa))]
    trace=json.loads((run/'monitoring.json').read_text()); assert [t['step'] for t in trace]==list(range(0,10001,1000))
    for t in trace:
        np.testing.assert_allclose(t[KEYS[0]]**2,t['active_contribution']+t['background_contribution'],rtol=1e-12,atol=1e-15)
        for metric,contrib,prob in [(KEYS[1],'active_contribution','p_damage'),(KEYS[2],'background_contribution','p_background')]: np.testing.assert_allclose(t[metric]**2*t[prob],t[contrib],rtol=1e-12,atol=1e-15)
    np.testing.assert_allclose(values,[trace[-1][k] for k in KEYS],rtol=0,atol=1e-14)
    metrics=json.loads((run/'metrics.json').read_text())
    g=metrics['geometry']; lo=np.asarray(g['lower']); hi=np.asarray(g['upper']); pad=g['padding']
    support=np.all((d['xy']>lo-pad)&(d['xy']<hi+pad),axis=1)
    for label,region in [('background_inside_support',~mask&support),('background_outside_support',~mask&~support),('damage_outside_support',mask&~support)]:
        pr=float(w[region].sum()); contribution=float(np.sum(w[region]*err[region]))
        support_rows.append(dict(state=state,arm=arm,region=label,mass_fraction=pr,squared_contribution=contribution,conditional_rms=(contribution/pr)**.5 if pr else None,share_of_full_error=contribution/(ca+cb)))
    np.testing.assert_allclose(values[0],metrics['metrics'][KEYS[0]],rtol=0,atol=1e-14)
    traces[key]=trace; receipts.append(receipt)
    rows.append(dict(state=state,arm=arm,full=values[0],damage=values[1],background=values[2],damage_contribution=ca,background_contribution=cb,background_fraction=cb/(ca+cb),run_id=run.name))
    audit.append(dict(state=state,arm=arm,independent_final_rms=values,atol=1e-14,hashes_match=True,reference_sha256=d['reference_sha256']))
assert set(traces)=={(st,a) for st in STATES for a in ARMS}
comparison=[]; lookup={(r['state'],r['arm']):r for r in rows}
with (OUT.parent/'S04-E017/ratio_comparison.csv').open() as f: e17={r['state']:r for r in csv.DictReader(f) if r['alpha']=='0.7'}
for st in STATES:
    c,l=lookup[st,'control'],lookup[st,'localized']; old=e17[st]
    comparison.append(dict(state=st,control_full=c['full'],localized_full=l['full'],full_improvement_percent=100*(1-l['full']/c['full']),control_damage=c['damage'],localized_damage=l['damage'],damage_improvement_percent=100*(1-l['damage']/c['damage']),control_background=c['background'],localized_background=l['background'],background_ratio=l['background']/c['background'],control_background_fraction=c['background_fraction'],localized_background_fraction=l['background_fraction'],e017_alpha07_full=float(old['final_uv']),localized_over_e017=l['full']/float(old['final_uv']),damage_squared_contribution_saved=c['damage_contribution']-l['damage_contribution'],background_squared_contribution_added=l['background_contribution']-c['background_contribution']))
floor_rows=[]
E17=PROJECT/'local_archive/experiments/S04-E017/runs/S04-E017-R013-posthoc/retrieved/runs'
for st in STATES:
    run=next(p for p in E17.iterdir() if st in p.name and '-a07-' in p.name)
    receipt=json.loads((run/'RUN_RECEIPT.json').read_text()); assert sha(run/'prediction.npz')==receipt['prediction_sha256']
    with np.load(run/'prediction.npz') as p: uv=p['uv'].copy()
    d=refs[st]; w=d['mass']/d['mass'].sum(); err=np.sum((uv-d['equilibrated_uv'])**2,1)/abs(US)**2
    run18=next(p for p in (BUNDLE/'runs').iterdir() if st in p.name and '-localized-' in p.name)
    g=json.loads((run18/'metrics.json').read_text())['geometry']; lo=np.array(g['lower']);hi=np.array(g['upper']);pad=g['padding']
    support=np.all((d['xy']>lo-pad)&(d['xy']<hi+pad),axis=1)
    outside=float(np.sum(w[~support]*err[~support]))
    floor_rows.append(dict(state=st,base_run_id=run.name,base_prediction_sha256=receipt['prediction_sha256'],outside_support_squared_error=outside,ideal_compact_correction_full_rms_lower_bound=np.sqrt(outside),attainability_of_1e3_by_outside_lower_bound_only=bool(outside<=1e-6)))
csvwrite(OUT/'frozen_base_outside_floor.csv',floor_rows)
csvwrite(OUT/'support_decomposition.csv',support_rows); csvwrite(OUT/'region_comparison.csv',comparison); csvwrite(OUT/'final_regions.csv',rows)
merged=[dict(state=st,arm=a,**t) for (st,a),trace in traces.items() for t in trace]
csvwrite(OUT/'trajectories.csv',merged)
(OUT/'monitoring.json').write_text(json.dumps(merged,indent=2)+'\n'); (OUT/'receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
verification=dict(status='SAVED_ARRAY_RECOMPUTATION_PASS',compact_sha256=sha(RAW/'compact_bundle.tar.gz'),checkpoint_retrieval='NOT_LOCAL; REMOTE_AUDIT_SEPARATE',rows=audit)
(OUT/'retrieval_verification.json').write_text(json.dumps(verification,indent=2)+'\n')
for filename in ('metrics.csv','summary.json'): (OUT/filename).write_text((BUNDLE/'aggregate'/filename).read_text())
figdir=OUT/'figures'; figdir.mkdir(exist_ok=True)
fig,axes=plt.subplots(1,3,figsize=(13,4.5))
for ax,metric in zip(axes,('full','damage','background')):
    for arm,color in [('control','#0072B2'),('localized','#D55E00')]: ax.plot(range(3),[lookup[st,arm][metric] for st in STATES],'-o',label=arm,color=color)
    basemetric={'full':'final_uv','damage':'damage_conditional_rms','background':'background_conditional_rms'}[metric]
    ax.plot(range(3),[float(e17[st][basemetric]) for st in STATES],'--s',color='#009E73',label='E017 alpha=.7 context')
    if metric=='full': ax.axhline(.001,color='black',ls=':',label='frozen full-field gate')
    ax.set_xticks(range(3),STATES); ax.set_yscale('log'); ax.set_title(metric+' RMS / |Us|'); ax.grid(alpha=.2); ax.legend(fontsize=8)
fig.suptitle('E018 final step10000, seed7, alpha=.7 • all three states; E017 is a different architecture')
for ext in ('png','pdf'): fig.savefig(figdir/f'final_region_comparison.{ext}',dpi=180,bbox_inches='tight')
plt.close(fig)
fig,axes=plt.subplots(3,4,figsize=(16,10))
for i,st in enumerate(STATES):
    for j,(metric,title) in enumerate(zip(KEYS+('fraction',),('Full-field UV','Damage conditional','Background conditional','Background squared-error share'))):
        ax=axes[i,j]
        for arm,color in [('control','#0072B2'),('localized','#D55E00')]:
            ts=traces[st,arm]; vals=[t['background_contribution']/t['full_field_loss'] if metric=='fraction' else t[metric] for t in ts]
            ax.plot([t['step'] for t in ts],vals,'-o',ms=3,label=arm,color=color)
        if metric!='fraction': ax.set_yscale('log')
        else: ax.set_ylim(0,1)
        if j==0: ax.axhline(.001,color='black',ls=':')
        ax.set_title(st+' • '+title); ax.grid(alpha=.2)
        if i==0 and j==0: ax.legend()
        if i==2: ax.set_xlabel('Optimizer step (passive monitoring)')
fig.suptitle('E018 fixed full-field traces • step0 shown for initialization; final-only decisions')
fig.tight_layout()
for ext in ('png','pdf'): fig.savefig(figdir/f'fixed_region_trajectories.{ext}',dpi=180,bbox_inches='tight')
plt.close(fig)
print(json.dumps(comparison,indent=2))
