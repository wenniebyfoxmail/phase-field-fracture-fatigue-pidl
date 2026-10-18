"""Saved-field 2x2 UV/d substitutions and native-Q4 error attribution."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import s04_e027 as old
import s04_e028 as scored


def main(case,out):
    torch.set_num_threads(1);raw=case/'retrieved/output';lock=json.loads((raw/'data_lock.json').read_text())
    arrays=old.load_reference(Path(lock['reference_lock']['root']),lock['reference_lock']);p=old.Problem(arrays)
    f=np.load(raw/'fields.npz');states={};parts={};scores={}
    for uv in ['own','FEM']:
        for d in ['zero','E030']:
            key=f'{uv}UV_{d}d';q=np.column_stack((f['fixedUV0' if uv=='own' else 'reference'][:,:2],f['fixedUV0' if d=='zero' else 'R'][:,2]))
            states[key]=q;t=torch.as_tensor(q);parts[key]=p.parts(*t.unbind(1));scores[key]=scored.component_scores(p,t)
    ref=p.parts(*p.ref.unbind(1));gp=torch.einsum('gn,enx->egx',p.N,p.xy[p.conn]);regions={
        'Z':p.gp_zone,'left_band':(gp[:,:,0]<0)&(gp[:,:,1].abs()<=.03),'outside_band':gp[:,:,1].abs()>.03}
    if not torch.equal(sum(mask.int() for mask in regions.values()),torch.ones_like(p.gp_zone,dtype=torch.int32)):raise ValueError('regions must partition global GP4')
    rows=[];actual={};total_weight=float(p.w.sum())
    for key,part in parts.items():
        err=part[4]-ref[4];total=float((p.w*err.square()).sum())
        for name,mask in dict(global_support=torch.ones_like(p.gp_zone),**regions).items():
            w=p.w[mask];e=err[mask];se=float((w*e.square()).sum())
            rows.append(dict(state=key,region=name,GP_count=int(mask.sum()),weight=float(w.sum()),weighted_SE=se,conditional_RMSE=float(torch.sqrt((w*e.square()).sum()/w.sum())),share_of_global_SE=se/total if total>0 else 0))
    a,b=parts['ownUV_zerod'],parts['ownUV_E030d']
    if not torch.equal(a[3],b[3]):raise ValueError('own UV raw must be identical')
    d0=old.q4_interpolate(torch.as_tensor(f['fixedUV0'][:,2]),p.conn,p.N);d1=old.q4_interpolate(torch.as_tensor(f['R'][:,2]),p.conn,p.N)
    delta_g=(1-d1).square()-(1-d0).square();delta_A=a[3]*delta_g;e0=a[4]-ref[4]
    if not torch.allclose(delta_A,b[4]-a[4],atol=1e-12,rtol=1e-12):raise ValueError('active product identity')
    delta_rows=[]
    for name,mask in regions.items():
        w=p.w[mask];cross=float((w*2*e0[mask]*delta_A[mask]).sum());positive=float((w*delta_A[mask].square()).sum())
        observed=float((w*((b[4][mask]-ref[4][mask]).square()-e0[mask].square())).sum())
        if not np.isclose(cross+positive,observed,atol=1e-12,rtol=1e-10):raise ValueError('SE decomposition')
        delta_rows.append(dict(region=name,cross_2e0_deltaA=cross,deltaA_squared=positive,delta_SE=observed))
    result=dict(status='NATIVE_Q4_ALGEBRAIC_SUBSTITUTIONS_VERIFIED',source_case=str(case),source_runtime='6f3d9abe024f17ba64e401aea9d71163c7207e68',scores=scores,regional_active_errors=rows,actual_E030_minus_zero=delta_rows,
        identity='Delta active = raw_own * Delta((1-d)^2); Delta weightedSE = integral(2e0 DeltaA + DeltaA^2)',
        regions='Exact disjoint GP4 partition: original Z x>=0 and |y|<=.03; left band x<0 and |y|<=.03; outside |y|>.03. Native mesh x in[-.5,.5].',
        scope='ownUV_zerod and ownUV_E030d are actual saved fields; FEMUV combinations are algebraic diagnostics, not equilibrated solutions, trainable NN oracles, or accepted physical states. Same target/lower/fatigue; no PT/model, optimizer, FEM solve or new data.')
    out.mkdir(parents=True,exist_ok=True);(out/'substitution.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(out/'substituted_fields.npz',**states)
    for filename,items in [('region_errors.csv',rows),('delta_SE.csv',delta_rows)]:
        with (out/filename).open('w') as file:
            writer=csv.DictWriter(file,fieldnames=list(items[0]),lineterminator='\n');writer.writeheader();writer.writerows(items)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,3.8),layout='constrained');keys=list(scores);x=np.arange(4)
    for ax,metric,label in [(axes[0],'active_error','Z active relative L2 error'),(axes[1],'global_active_RMSE','Global active absolute RMSE')]:
        ax.bar(x,[scores[k][metric] for k in keys],color=['#777777','#009E73','#999999','#56B4E9']);ax.set(xticks=x,xticklabels=['ownUV+d0','ownUV+d30','FEMUV+d0*','FEMUV+d30*'],ylabel=label);ax.tick_params(axis='x',labelrotation=25)
    axes[2].bar(range(3),[r['delta_SE'] for r in delta_rows],color=['#009E73' if r['delta_SE']<=0 else '#D55E00' for r in delta_rows]);axes[2].axhline(0,c='#999999',lw=.8);axes[2].set(xticks=range(3),xticklabels=[r['region'] for r in delta_rows],ylabel='Change in integrated squared active error',title='Actual E030 d change at fixed own UV')
    fig.suptitle('E030 attribution | * FEM-UV substitutions are algebraic, not solved states | exposed c20s4 / horizon0 / seed1')
    fig.savefig(out/'substitution.png',dpi=170);plt.close(fig)
    (out/'substitution.md').write_text(f'''# How to read substitution.png
\n## Figure question
Which UV/d combination and region produces the global active cost of actual E030?
\n## Data provenance
Exact {raw}/fields.npz and data_lock.json, native Q4/GP4/Jacobian weights. Source tools/analyze_s04_e030_uv_damage.py, original runtime6f3d9abe024f17ba64e401aea9d71163c7207e68. Same exposed synthetic c20s4 / horizon0 / seed1, no fresh reference or history commit. Numeric substitution.json, region_errors.csv and delta_SE.csv accompany this plot.
\n## Visual grammar and panel guide
Left Z relative error; center global absolute RMSE, distinct scales/units. First two bars actual ownUV+d0/d30, last two use exact FEM UV only as algebraic counterfactual. Right exact change in integrated squared active error from zero d to d30 at fixed ownUV, partitioned into original Z, x<0 near-crack band |y|<=.03, and outside band |y|>.03. Negative green means reduction; positive orange means increase. Full signed values, no clipping, selected error region or smoothing.
\n## Key numerical takeaway
Actual local/global scores {json.dumps({k:{n:v[n] for n in ['active_error','global_active_RMSE']} for k,v in scores.items()})}. Regional changes {json.dumps(delta_rows)}. Product identity and squared-error cross term are exactly checked; do not add RMS norms or call regional SE contributions causal percentages.
\n## Limitations and claim boundary
FEM-UV substitutions are not physically solved or trainable head outputs. They only motivate checking current UV-head reachability. Global and Z errors use their native supports and do not override the frozen E030 primary. One exposed synthetic state, no physical evolution, teacher truth or transfer claim.
''')
    print(json.dumps(dict(scores={k:{n:v[n] for n in ['active_error','global_active_RMSE','free_force']} for k,v in scores.items()},delta_SE=delta_rows),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();main(args.case,args.out)
