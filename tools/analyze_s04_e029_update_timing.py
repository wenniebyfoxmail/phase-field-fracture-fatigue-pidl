"""Align exact full-support pre-update LA with saved post-update milestones."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np


def main(case,out):
    raw=case/'retrieved/output';trace=json.loads((raw/'loss_trace.json').read_text())
    ms=json.loads((raw/'milestones.json').read_text());s=json.loads((raw/'scores.json').read_text())
    if [r['step'] for r in trace]!=list(range(1,201)):raise ValueError('200 contiguous updates required')
    pre=np.sqrt([r['L_active'] for r in trace]);post=np.r_[pre[1:],s['R']['active_error']]
    for r in ms:
        k=r['step'];v=pre[0] if k==0 else post[k-1]
        if not np.isclose(v,r['scores']['active_error'],atol=1e-10,rtol=1e-10):raise ValueError('milestone timing mismatch')
    start=s['smooth0']['active_error'];rows=[]
    for i in range(200):rows.append(dict(update=i+1,pre_active_error=float(pre[i]),post_active_error=float(post[i]),post_over_pre=float(post[i]/pre[i]),post_source='next row full-support pre-loss' if i<199 else 'saved post200 field score'))
    windows=[]
    for a,b in [(0,200),(0,50),(50,100),(100,150),(150,200)]:
        v=post[a:b];windows.append(dict(first=a+1,last=b,post_min=float(v.min()),post_median=float(np.median(v)),post_max=float(v.max()),worse_than_zero_count=int((v>start).sum()),count=len(v)))
    result=dict(status='EXACT_TIMING_ALIGNED',source_case=str(case),runtime_commit='7c72db1795e2982a25de68a37dceb0baffb18f8a',own_zero_active=start,windows=windows,largest_jumps=sorted(rows,key=lambda x:x['post_over_pre'],reverse=True)[:10],
        scope='Full-support active objective has no sampling; next pre-update q is prior post-update q, with no intervening parameter update. All scheduled milestones independently match.',
        observed='196/200 post-update states worse than own zero, plus repeated sharp changes. Stored10/50/100/200 UV errors all worse than zero; endpoint swaps implicate UV/raw while damage also imperfect.',
        unavailable='No per-step UV/d fields or parameter/Adam update norms. Cannot attribute every jump to UV, classify actual parameter step magnitude, or prove optimizer causality.',
        decision='One-factor fixed physical own-zero UV isolation; retain map/Adam/loss/seed/200steps. No simultaneous step clipping or optimizer change.')
    out.mkdir(parents=True,exist_ok=True);(out/'timing_alignment.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'timing_alignment.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,3.8),layout='constrained')
    axes[0].semilogy(np.arange(201),np.r_[pre[0],post],lw=1.2,label='all actual post-update states')
    axes[0].axhline(start,c='#E69F00',ls='--',label='own smooth0');axes[0].set(xlabel='completed optimizer updates',ylabel='Z active relative L2 error',title='Correctly aligned E029 trajectory');axes[0].legend()
    axes[1].semilogy(np.arange(1,201),post/pre,lw=1.2);axes[1].axhline(1,c='#999999',ls=':');axes[1].set(xlabel='update index',ylabel='active error after / before',title='Observable field changes, not parameter-step norms')
    fig.savefig(out/'timing_alignment.png',dpi=170);plt.close(fig)
    (out/'timing_alignment.md').write_text(f'''# How to read timing_alignment.png
\n## Figure question
Is E029 degradation persistent or just a final-update artifact?
\n## Data provenance
Exact {raw}/loss_trace.json, milestones.json, scores.json; original runtime7c72db1795e2982a25de68a37dceb0baffb18f8a. Plot source tools/analyze_s04_e029_update_timing.py. Same exposed synthetic c20s4 / horizon0 / seed1, native GP4 Z scoring. No PT/model, optimizer/FEM solve, fresh data or history update.
\n## Visual grammar and panel guide
Left every post-update active error, reconstructed from next row full-support pre-update LA except200 from saved final score; all saved milestones match1e-10. Horizontal line own zero. Right after/before active error for each update;1 means unchanged. Log scales, no clipping or smoothing. Updates are optimization, not physical time.
\n## Key numerical takeaway
196/200 post-update states worse than zero. First update multiplies error96.167; repeated later jumps occur, last3.1464. Last endpoint alone does not explain the persistent departure. Saved UV errors and endpoint swaps select physical-UV isolation as one intervention.
\n## Limitations and claim boundary
Per-step fields and parameter update norms are absent. Ratios are field-error changes, not Adam step sizes; no optimizer causality or all-jumps-UV claim. No selected lower trace state replaces the frozen200 endpoint, no old result revision. Proposed isolation is an independent future trial, not a result here.
''')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();main(args.case,args.out)
