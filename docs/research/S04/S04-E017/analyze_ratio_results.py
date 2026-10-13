#!/usr/bin/env python3
"""Exact-output posthoc for E017; passive analysis, no model/training calls."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

STATES = ('c20s4','c40s4','c60s4','c83s4')
ALPHAS = (.5,.7,.9)
US = .11999988
COLORS = { .5:'#0072B2', .7:'#009E73', .9:'#D55E00'}
UV = 'displacement_mass_rms_over_abs_Us'
BG = 'background_conditional_rms_over_abs_Us'
DM = 'damage_conditional_rms_over_abs_Us'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(path, rows):
    with path.open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def save(fig, figures, stem):
    fig.savefig(figures/(stem+'.png'), dpi=180, bbox_inches='tight')
    fig.savefig(figures/(stem+'.pdf'), bbox_inches='tight')
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--project-root',type=Path,required=True,help='Parent project containing local_archive')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent)
    args=parser.parse_args()
    output=args.output; figures=output/'figures'; figures.mkdir(parents=True,exist_ok=True)
    summary=json.loads((args.bundle/'aggregate/summary.json').read_text())
    if summary['valid_completed_runs']!=12 or summary['missing'] or summary['integrity_errors']:
        raise ValueError('Incomplete/inadmissible bundle; never analyze partial archive')
    with (args.bundle/'aggregate/metrics.csv').open() as f:
        rows=list(csv.DictReader(f))
    metrics={ (r['state'],float(r['alpha'])):r for r in rows}
    if len(rows)!=12 or set(metrics)!={(s,a) for s in STATES for a in ALPHAS}:
        raise ValueError('Expected exactly all12 unique states/arms')
    runs={}; traces={}
    for run in sorted((args.bundle/'runs').iterdir()):
        receipt=json.loads((run/'RUN_RECEIPT.json').read_text())
        key=(receipt['state'],float(receipt['alpha']))
        if receipt['status']!='COMPLETED' or key in runs or receipt['seed']!=7:
            raise ValueError('Invalid run receipt/duplicate')
        for filename, hashkey in [('monitoring.json','monitoring_sha256'),('prediction.npz','prediction_sha256')]:
            if sha(run/filename)!=receipt[hashkey]:
                raise ValueError(f'Payload identity mismatch {run}/{filename}')
        trace=json.loads((run/'monitoring.json').read_text())
        if [t['step'] for t in trace]!=list(range(0,10001,1000)):
            raise ValueError('Expected all11 frozen monitoring points')
        for t in trace:
            loss=t['active_contribution']+t['background_contribution']
            np.testing.assert_allclose(t[UV]**2,loss,rtol=1e-12,atol=1e-18)
            np.testing.assert_allclose(t[DM]**2*t['p_damage'],t['active_contribution'],rtol=1e-12,atol=1e-18)
            np.testing.assert_allclose(t[BG]**2*t['p_background'],t['background_contribution'],rtol=1e-12,atol=1e-18)
            t['background_fraction']=t['background_contribution']/loss
        np.testing.assert_allclose(trace[-1][UV],float(metrics[key][UV]),rtol=0,atol=1e-14)
        runs[key]=run; traces[key]=trace
    if set(runs)!=set(metrics): raise ValueError('Run/metric coverage mismatch')
    comparisons=[]; diagnostics=[]
    for state in STATES:
        base=float(metrics[state,.9][UV]); best=min(ALPHAS,key=lambda a:float(metrics[state,a][UV]))
        for alpha in ALPHAS:
            row=metrics[state,alpha]; trace=traces[state,alpha]; final=trace[-1]
            comparisons.append(dict(state=state,role='sentinel' if state=='c40s4' else 'primary',seed=7,alpha=alpha,
                final_uv=float(row[UV]),damage_conditional_rms=final[DM],background_conditional_rms=final[BG],
                damage_contribution=final['active_contribution'],background_contribution=final['background_contribution'],
                background_contribution_fraction=final['background_fraction'],ratio_to_fixed_alpha09=float(row[UV])/base,
                improvement_percent_vs_fixed_alpha09=100*(1-float(row[UV])/base),
                descriptive_state_best_alpha=best,gate_1e3=float(row[UV])<=.001,
                strain_relative_l2=float(row['strain_relative_l2']),rho_u=float(row['predicted_rho_u']),run_id=runs[state,alpha].name))
            d=dict(state=state,alpha=alpha,run_id=runs[state,alpha].name)
            for label, subset in [('post_init1000to10000',[t for t in trace if t['step']>=1000]),('late7000to10000',[t for t in trace if t['step']>=7000])]:
                peak=max(subset,key=lambda t:t['background_fraction'])
                largest_bg=max(subset,key=lambda t:t[BG])
                d.update({label+'_max_background_fraction':peak['background_fraction'],label+'_fraction_peak_step':peak['step'],
                          label+'_fraction_peak_uv':peak[UV],label+'_max_background_conditional_rms':largest_bg[BG],
                          label+'_background_rms_peak_step':largest_bg['step']})
            d.update(final_uv=final[UV],final_damage_conditional_rms=final[DM],final_background_conditional_rms=final[BG],
                     final_background_fraction=final['background_fraction'])
            diagnostics.append(d)
    csv_write(output/'ratio_comparison.csv',comparisons)
    csv_write(output/'trajectory_diagnostics.csv',diagnostics)
    with (output.parent/'S04-E014/r002_metrics.csv').open() as f:
        e014=list(csv.DictReader(f))
    for row in e014:
        if row['state'] in ('c20s4','c83s4'):
            for key in (UV,'strain_relative_l2','predicted_rho_u'):
                if float(row[key])!=float(metrics[row['state'],.9][key]):
                    raise ValueError('E014 repeated .9 metrics not exact')

    fig,axes=plt.subplots(1,4,figsize=(16,4))
    for ax,(key,label) in zip(axes,[(UV,'Full-field UV RMS / |Us|'),('final_damage_conditional_rms','Damage conditional RMS / |Us|'),
                                  ('final_background_conditional_rms','Background conditional RMS / |Us|'),('fraction','Background contribution fraction')]):
        for alpha in ALPHAS:
            values=[(traces[s,alpha][-1]['background_fraction'] if key=='fraction' else float(metrics[s,alpha][key])) for s in STATES]
            ax.plot(range(4),values,'o-',color=COLORS[alpha],label=f'α={alpha}')
        if key==UV: ax.axhline(.001,color='black',ls='--',lw=1,label='Primary 1e-3')
        ax.set_xticks(range(4),['c20','c40*','c60','c83']); ax.set_title(label,fontsize=10); ax.grid(alpha=.2)
        if key!='fraction': ax.set_yscale('log')
    axes[0].legend(fontsize=8)
    fig.suptitle('S04-E017 • synthetic same-state development • seed7 • step10000 only\nAll12 runs; * c40 sentinel; fixed α=.9 is the worst-state development choice, not independent validation',fontsize=11)
    fig.tight_layout(); save(fig,figures,'final_ratio_comparison')

    fig,axes=plt.subplots(4,4,figsize=(16,12),sharex=True)
    for i,state in enumerate(STATES):
        for j,(key,label) in enumerate([(UV,'Full-field UV RMS'),(DM,'Damage conditional RMS'),(BG,'Background conditional RMS'),('background_fraction','Weighted background fraction')]):
            ax=axes[i,j]
            for alpha in ALPHAS:
                ax.plot([t['step'] for t in traces[state,alpha]],[t[key] for t in traces[state,alpha]],'o-',ms=3,color=COLORS[alpha],label=f'α={alpha}')
            ax.set_title(f'{state} • {label}',fontsize=10); ax.grid(alpha=.2)
            if key!='background_fraction': ax.set_yscale('log'); ax.set_ylabel('RMS / |Us|')
            else: ax.set_ylim(-.01,1.01); ax.set_ylabel('C_B / (C_A + C_B)')
            if key==UV: ax.axhline(.001,color='black',ls='--',lw=.8)
            if i==3: ax.set_xlabel('Optimizer step (passive monitoring)')
            if i==0 and j==0: ax.legend(fontsize=8)
    fig.suptitle('S04-E017 fixed full-field traces • no checkpoint selection\nInitialization shown for context; spike statistics exclude only step0 (use1000–10000); late window7000–10000',fontsize=12)
    fig.tight_layout(); save(fig,figures,'fixed_trajectory_regions')

    # Fixed alpha .7 chosen by protocol for visualization, never best-state selection.
    references={s:args.project_root/'local_archive/experiments/S04-E013/runs/S04-E013-stage1-matrix-769396f-20261008T230420Z/http_inputs'/f'{s}.npz' for s in STATES}
    references['c40s4']=args.project_root/'local_archive/experiments/S04-E009/runs/S04-E009-R001/retrieved/output/c40/fields.npz'
    fields={}
    for state in STATES:
        ref=references[state]
        if sha(ref)!=metrics[state,.7]['reference_sha256']: raise ValueError('Reference identity mismatch')
        with np.load(ref) as data: xy=data['xy'].copy(); conn=data['conn'].copy(); target=data['equilibrated_uv'].copy()
        with np.load(runs[state,.7]/'prediction.npz') as data: pred=data['uv'].copy()
        if pred.shape!=target.shape or not np.isfinite(pred).all(): raise ValueError('Invalid prediction')
        fields[state]=(xy,target[:,1]/US,pred[:,1]/US,np.linalg.norm(pred-target,axis=1)/US,conn)
    vmin=min(np.min(values[1:3]) for values in fields.values()); vmax=max(np.max(values[1:3]) for values in fields.values())
    errmax=max(values[3].max() for values in fields.values())
    fig,axes=plt.subplots(4,3,figsize=(11,13),sharex=True,sharey=True)
    for i,state in enumerate(STATES):
        xy,target,pred,error,conn=fields[state]
        for j,(values,label,cmap,lo,hi) in enumerate([(target,'FEM target v / Us','viridis',vmin,vmax),(pred,'PIDL predicted v / Us','viridis',vmin,vmax),(np.log10(np.maximum(error,1e-8)),'log10 vector UV error / |Us|','magma',-8,np.log10(errmax))]):
            ax=axes[i,j]
            scatter=PolyCollection(xy[conn],array=values[conn].mean(axis=1),cmap=cmap,edgecolors='none',rasterized=True)
            scatter.set_clim(lo,hi); ax.add_collection(scatter)
            ax.set_aspect('equal'); ax.set_xlim(-.5,.5); ax.set_ylim(-.5,.5)
            ax.set_title(f'{state} • {label}',fontsize=9)
            if j==0: ax.set_ylabel('y')
            if i==3: ax.set_xlabel('x')
            if i==3: fig.colorbar(scatter,ax=ax,orientation='horizontal',pad=.13,fraction=.07)
    fig.suptitle('S04-E017 • all states at fixed α=.7 • final step10000\nQualified conditional FEM UV • Q4 nodal-colour averages for display only • common scales; log-error floor1e-8',fontsize=11)
    fig.tight_layout(); save(fig,figures,'fixed_alpha07_uv_fields')
    print(json.dumps({'all12_min_final_uv':min(float(r[UV]) for r in rows),'all12_max_final_uv':max(float(r[UV]) for r in rows),
        'fixed_alpha09_selected':summary['selected_development_alpha'],'E014_exact_reproduction':True,
        'field_v_range':[float(vmin),float(vmax)],'field_vector_error_max':float(errmax)},indent=2))


if __name__=='__main__': main()
