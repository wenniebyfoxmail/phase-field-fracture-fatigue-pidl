"""Render fixed six endpoint diagnostic outputs; never load/update model weights."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

STATES=('c20s4','c60s4','c83s4')
COLORS={'E021':'#d76b22','E022':'#27825c'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);a=p.parse_args()
    data=json.loads((a.case/'results/summary.json').read_text());rr=data['results'];assert len(rr)==6
    out=a.case/'analysis';out.mkdir(exist_ok=True)
    rows=[];heads=[];gradients=[];activations=[]
    for r in rr:
        h={x['region']:x for x in r['head']};g={x['group']:x for x in r['gradients']}
        act=next(x for x in r['activations'] if x['layer']==7 and x['region']=='damage')
        rows.append(dict(state=r['state'],arm=r['arm'],full_rms=r['full_rms'],damage_rms=r['regional_rms']['damage'],inside_background_rms=r['regional_rms']['background_inside'],
            damage_effective_ever_units=act['effective_ever_units'],damage_active_fraction=act['active_fraction'],damage_gram_rank_1e_8=h['damage']['rank_relative_1e_8'],damage_gram_entropy=h['damage']['entropy_rank'],
            head_scaled_normal_full=h['full']['scaled_normal_residual'],head_scaled_normal_damage=h['damage']['scaled_normal_residual'],head_scaled_normal_inside=h['background_inside']['scaled_normal_residual'],head_max_feature_correlation=h['full']['max_feature_residual_correlation'],
            all_damage_inside_cos=g['all']['damage_inside_cosine'],hidden_damage_inside_cos=g['hidden']['damage_inside_cosine'],head_damage_inside_cos=g['head']['damage_inside_cosine'],
            all_damage_norm=g['all']['damage_norm'],all_inside_norm=g['all']['inside_background_norm'],head_full_norm=g['head']['full_norm'],hidden_full_norm=g['hidden']['full_norm'],
            all_damage_dot_full=g['all']['damage_dot_full_gradient'],all_inside_dot_full=g['all']['inside_background_dot_full_gradient'],damage_outside_nodes=r['damage_outside_nodes'],damage_outside_loss=r['damage_outside_loss_contribution'],peak_rss_bytes=r['peak_rss_bytes']))
        for x in r['head']:heads.append(dict(state=r['state'],arm=r['arm'],**{k:v for k,v in x.items() if k!='eigenvalues'}))
        gradients.extend(dict(state=r['state'],arm=r['arm'],**x) for x in r['gradients'])
        activations.extend(dict(state=r['state'],arm=r['arm'],**x) for x in r['activations'])
    for name,table in [('diagnostic_summary',rows),('head_stationarity',heads),('regional_gradients',gradients),('activations',activations)]:
        with (out/f'{name}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
    fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
    for i,state in enumerate(STATES):
        for arm,col in COLORS.items():
            r=next(x for x in rr if x['state']==state and x['arm']==arm)
            head={x['region']:x for x in r['head']};grad={x['group']:x for x in r['gradients']}
            axes[0,i].plot(range(3),[head[k]['scaled_normal_residual'] for k in ('damage','background_inside','full')],'o-',color=col,label=arm)
            axes[1,i].plot(range(3),[grad[k]['damage_inside_cosine'] for k in ('all','hidden','head')],'o-',color=col,label=arm)
        axes[0,i].set(title=state+': output-head residual',xticks=range(3),xticklabels=['damage','inside bg','full'],yscale='log',ylabel='||R|| / sqrt(trace(H) L)')
        axes[1,i].set(title=state+': regional gradient alignment',xticks=range(3),xticklabels=['all','hidden','head'],ylim=(-1.05,1.05),ylabel='cos(g_damage, g_inside-bg)')
        axes[1,i].axhline(0,color='black',ls=':',lw=.8)
        if state=='c60s4':axes[1,i].text(.03,.06,'E021 hidden cosine undefined: bg gradient = 0',transform=axes[1,i].transAxes,fontsize=8)
        for ax in axes[:,i]:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('E021/E022 six saved endpoints | original mass objective | no fitting or updates')
    for ext in ('png','pdf'):fig.savefig(out/f'head_and_regional_gradients.{ext}',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(11,10),layout='constrained')
    for i,state in enumerate(STATES):
        for arm,col in COLORS.items():
            r=next(x for x in rr if x['state']==state and x['arm']==arm)
            for reg,style in [('damage','-'),('background_inside','--')]:
                act=[x for x in r['activations'] if x['region']==reg]
                axes[i,0].plot(range(1,9),[x['active_fraction'] for x in act],style,color=col,label=arm+' '+reg)
                h=next(x for x in r['head'] if x['region']==reg);ev=np.maximum(np.array(h['eigenvalues']),0)
                axes[i,1].plot(range(1,len(ev)+1),np.maximum(ev/ev[0],1e-16),style,color=col,label=arm+' '+reg)
        axes[i,0].set(title=state+': actual positive activation',xlabel='Hidden layer',ylabel='Conditional mass-weighted fraction',yscale='log',xticks=range(1,9))
        axes[i,1].set(title=state+': effective head feature Gram',xlabel='Eigenvalue index',ylabel='Eigenvalue / maximum (floor 1e-16)',yscale='log',ylim=(1e-16,2))
        if state=='c60s4':axes[i,0].text(.28,.05,'E021 inside-bg L8 = 0 (off log scale)',transform=axes[i,0].transAxes,fontsize=7)
        for ax in axes[i]:ax.grid(alpha=.2);ax.legend(fontsize=6)
    for ext in ('png','pdf'):fig.savefig(out/f'activation_and_feature_spectrum.{ext}',dpi=170)
    plt.close(fig)
    for stem in ('head_and_regional_gradients','activation_and_feature_spectrum'):
        takeaway='; '.join(f"{r['state']} {r['arm']} full={r['full_rms']:.9g}, scaled head residual={r['head'][-1]['scaled_normal_residual']:.6g}, damage-bg cos={r['gradients'][0]['damage_inside_cosine']:.6g}" for r in rr)
        (out/f'{stem}.md').write_text(f'''# Six endpoint read-only diagnostic

## Data provenance

S04-E022-D001 results/summary.json from reviewed diagnose_s04_e022_endpoints.py, unchanged E021 measure; all six c20s4/c60s4/c83s4×E021/E022 final10000update checkpoints, fixed FEM UV-derived target and E017alpha.7seed7backbones. This is one exposed synthetic development trajectory, not prediction. Exact CSVs alongside; original E021/E022 producer primary FAIL and strict Mac portability exceptions unchanged.

## How to read

Head/gradient figure columns are c20,c60,c83. Top: head normal residual R=FᵀMerror scaled by sqrt(trace(H)L), lower means smaller first-order residual in this scaling, no stationarity cutoff. F includes BC×window×last-hidden plus bias, normalized by abs(Us). Bottom: damage vs inside-background gradient cosine for all trainable residual parameters, hidden and head separately. Zero line indicates orthogonality, not scientific success. Orange E021, green E022.

Activation/feature figure rows are the three states. Left: actual positive-activation fractions by hiddenlayer, conditional region mass; learned activation coefficient may have either sign. Right: effective feature Gram eigenvalues/max on log scale, plotted floor1e-16; solid damage,dashed inside-background. Compare features with physical BC/window factors. CSVs and rawJSON retain exact values. c60E021 inside-background layer8 activation is exactly zero (annotated off log scale), not a missing nonzero observation; its hidden gradient cosine is undefined because that regional gradient is zero and is not plotted as zero.

## Numerical takeaway

{takeaway}. Nonzero head residual is not a proven attainable UV improvement. Positive activations are not nonzero pathway coverage for LeakyReLU.


## Limitations

No optimizer, LS/ridge solve, parameter update, new producer run or holdout. No plotted quantity proves convergence, full-network capacity or Adam trajectory causality; a negative cosine alone does not explain historical regression. Conditional region measures are not full-objective mass contributions. Successful c20 is a counterexample control for generic explanations. Final recommendations and numerical takeaways are in README_analysis.md and the tracked E022/endpoint_diagnostic_decision.md. The diagnostic cannot revise the original .001 full-field criterion.
''')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
