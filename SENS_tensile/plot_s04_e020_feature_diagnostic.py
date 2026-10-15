"""Render already-computed read-only endpoint diagnostics; no model fitting."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    x=json.loads((a.case/'results/summary.json').read_text());a.out.mkdir(exist_ok=False)
    rows=[]
    for r in x['results']:
        act=next(v for v in r['activations'] if v['layer']==7 and v['region']=='damage')
        spec=next(v for v in r['spectrum'] if v['region']=='damage')
        inp=next(v for v in r['gradients'] if v['group']=='input_layer')
        rows.append(dict(state=r['state'],arm=r['arm'],full=r['regions']['full'],last_damage_ever_positive=283-act['dead_units'],
            last_damage_active_fraction=act['mean_active_fraction'],damage_feature_rank_relative_1e_8=spec['rank_relative_1e_8'],
            damage_feature_entropy_rank=spec['entropy_rank'],gradient_cosine=r['gradients'][0]['cosine'],
            damage_gradient_input_norm=inp['damage_norm'],damage_gradient_total_norm=r['gradients'][0]['damage_norm']))
    with (a.out/'diagnostic_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    states=['c20s4','c60s4','c83s4'];colors={'initial_reconstruction':'#888888','E019':'#2878b5','E020':'#df651b'}
    fig,axes=plt.subplots(3,3,figsize=(14,10),layout='constrained')
    for i,s in enumerate(states):
        for arm,c in colors.items():
            r=next(v for v in x['results'] if v['state']==s and v['arm']==arm)
            acts=[v for v in r['activations'] if v['region']=='damage']
            axes[i,0].plot(range(1,9),[v['mean_active_fraction'] for v in acts],'o-',color=c,label=arm)
            if arm!='initial_reconstruction':
                groups=['input_layer']+[f'hidden_layers.{k}' for k in range(7)]+['output_layer'];g={v['group']:v for v in r['gradients']}
                axes[i,1].plot(range(1,10),[g[v]['damage_norm'] for v in groups],'o-',color=c,label=arm)
            eig=np.array(next(v for v in r['spectrum'] if v['region']=='damage')['eigenvalues'])
            axes[i,2].plot(np.arange(1,len(eig)+1),np.maximum(eig/eig[0],1e-16),color=c,label=arm)
        axes[i,0].set(title=f'{s}: damage activation',yscale='log',xlabel='Hidden layer',ylabel='Mass-weighted positive fraction',xticks=range(1,9))
        axes[i,1].set(title=f'{s}: damage-contribution gradients',yscale='log',xlabel='Linear layer (9 = output)',ylabel='Parameter-group L2 norm',xticks=range(1,10))
        axes[i,2].set(title=f'{s}: output-feature Gram spectrum',yscale='log',xlabel='Eigenvalue index',ylabel='Eigenvalue / maximum',ylim=(1e-16,2))
        axes[i,2].axhline(1e-8,color='black',ls=':',lw=.8)
        for ax in axes[i]:ax.grid(alpha=.2)
    for ax in axes[0]:ax.legend(fontsize=7)
    fig.suptitle('E020 endpoint diagnosis | all nodes | no fitting or parameter updates')
    for ext in ['png','pdf']:fig.savefig(a.out/f'feature_diagnostic_overview.{ext}',dpi=170)
    plt.close(fig)
    maps=json.loads((a.case/'e021_map_admission.json').read_text())
    moments=[dict(residual_energy_center=v['mapping']['local_center'],original_center=v['physical_geometry']['center'],
        original_scale=v['physical_geometry']['scale'],std_over_original_scale=(np.array(v['mapping']['residual_std'])/v['physical_geometry']['scale']).tolist()) for v in maps]
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for j,k in enumerate(['x','y']):
        axes[0].plot(range(3),[(v['residual_energy_center'][j]-v['original_center'][j])/v['original_scale'][j] for v in moments],'o-',label=k)
        axes[1].plot(range(3),[v['std_over_original_scale'][j] for v in moments],'o-',label=k)
    axes[0].set(title='Core residual-energy centre vs window centre',ylabel='Offset / original local-coordinate scale')
    axes[1].set(title='Core residual-energy spread in original coordinates',ylabel='Weighted std / original scale',yscale='log')
    for ax in axes:ax.set(xticks=range(3),xticklabels=['c20','c60','c83']);ax.grid(alpha=.2);ax.legend()
    fig.savefig(a.out/'residual_coordinate_moments.png',dpi=180);plt.close(fig)
    text='''Exact diagnostic source6a3b154, all86756nodes, c20/c60/c83 × reconstructed initial/E019/E020final. No optimizer/update. Overview rows=states; columns=damage activation, damage-contribution gradient norms, BC/window-weighted last-hidden+bias Gram eigenvalues. Initial hidden gradients omitted because initial output weights are zero. Relative eigenvalues plotted with1e-16floor;1e-8line is descriptive. This is not a full Jacobian/NTK. c60E020last ever-positive3/283 vsE01977/283; input damage gradient4.73e-10vs1.15e-5. c83 retains active features/nonzero gradients; successfulc20also has sparse activations. Coordinate plot uses inherited residual squared × mass on damage, post-hoc not predictive localization. Gram includes output bias; entropy rank is not a capacity ceiling. Endpoint findings are exploratory, not a causal training-path proof. See diagnostic_summary.csv and README_analysis.md.\n'''
    for stem in ['feature_diagnostic_overview','residual_coordinate_moments']:(a.out/f'{stem}.md').write_text(f'# {stem}\n\n'+text)
    with (a.out/'residual_coordinate_moments.md').open('a') as f:
        f.write('\nCoordinate figure uses core-only damage moments from e021_map_admission.json. Earlier all-damage raw moments remain archived: c60 y-variance is sensitive to the tiny exterior contribution; these raw moments do not define the repair. Proposed zoom<=4 is a hypothesis, not an observed fit improvement.\n')


if __name__=='__main__':main()
