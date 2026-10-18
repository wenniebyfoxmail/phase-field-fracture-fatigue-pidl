"""Plot all parameter-tensor maxima and all actual guard violations."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    s=json.loads(a.summary.read_text());ts=s['tensors'];fails=s['failures'];m=s['metadata']
    labels=[t['parameter'].replace('hidden_layers.','H').replace('.weight','.W').replace('.bias','.b') for t in ts]
    fig,axs=plt.subplots(1,2,figsize=(13.4,8.2),layout='constrained',gridspec_kw={'width_ratios':[1,1.2]})
    yy=np.arange(len(ts));values=[t['max_ratio_to_tolerance'] for t in ts]
    axs[0].barh(yy,values,color=['#D55E00' if t['failing_components'] else '#0072B2' for t in ts],height=.67)
    axs[0].set(yticks=yy,yticklabels=labels,xlabel='Maximum |difference| / original pointwise tolerance',
        title='A  All parameter tensors (maxima, not samples)')
    axs[0].invert_yaxis();axs[0].axvline(1,color='#444444',ls='--',lw=1.2,label='Original limit = 1')
    axs[0].set_xscale('symlog',linthresh=.1);axs[0].set_xlim(0,max(values)*1.15);axs[0].legend(loc='lower right',fontsize=8)
    pos=np.arange(len(fails));names=[]
    for f in fails:
        short=f['parameter'].replace('hidden_layers.','H').replace('.weight','.W')
        names.append(short+'['+','.join(map(str,f['indices_zero_based']))+']')
    axs[1].barh(pos-.17,[f['absolute_difference']*1e6 for f in fails],height=.31,color='#D55E00',label='Observed absolute difference')
    axs[1].barh(pos+.17,[f['original_allowed_difference']*1e6 for f in fails],height=.31,color='#999999',label='Original allowed difference')
    axs[1].set(yticks=pos,yticklabels=names,xlabel='Parameter-gradient difference (x 1e-6)',
        title='B  All nine actual violations, ranked by ratio')
    axs[1].invert_yaxis();axs[1].legend(loc='lower right',fontsize=8)
    for ax in axs:
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',color='#dddddd',lw=.5);ax.set_axisbelow(True)
        ax.tick_params(labelsize=8)
    fig.suptitle(f'Saved full-NN gradient audit | zero optimizer updates\n'
        f"9 / {s['parameters']:,} components violate atol=1e-6, rtol=1e-4; relative L2 difference={m['relative_L2']:.3g}",fontsize=12)
    maxabs=s['maximum_absolute_difference']
    footer=(f"Hk = hidden_layers.k.weight; indices start at 0. Largest absolute difference: {maxabs['absolute_difference']:.6g} at H1.W[112,95]; "
            f"its allowed difference is {maxabs['original_allowed_difference']:.6g}, so this point is NOT a violation.\n"
            'Run pf_s04e011_wpair_grad_audit_20261018_v1 | C origin, beta=1, c1s1 U=.02999988 | synthetic numerical diagnostic; no root-cause or training-benefit claim')
    fig.supxlabel(footer,fontsize=8)
    fig.savefig(a.out/'gradient_discrepancy.png',dpi=180);plt.close(fig)
    readme=f'''# Gradient discrepancy reading guide

Question: what magnitude and parameter locations caused the original fullNN decomposition guard to stop?

Data provenance: `{a.summary}`; saved producer raw vectors remain under `{s['run']}`. GPU diagnostic source99cad0b3; CPU vector analysis26c0da65. Actual original allclose criterion is retained. The plot uses every parameter tensor and all9 violating scalar components. No NN forward, optimization or target FEM was used by the analysis.

How to read: read A first: each bar is a named tensor's maximum ratio abs(expected-direct)/(1e-6+1e-4 abs(direct)); the original boundary is1, with symlog x scale including zeros. This is a descriptive tensor maximum, not a statistical mean or independent-case result. Read B next: all9 failures ranked by their ratio, showing observed absolute difference versus the component-specific original allowed difference, in1e-6 units. Hk abbreviates hidden_layers.k.weight; indices are zero based.

Result: relative full-gradient L2 difference {m['relative_L2']:.12g}; {s['failing_components']} of{s['parameters']} scalar components fail. All failures lie in H0/H1/H2/H3 weights, counts1/2/2/4. Worst ratio{s['max_ratio_to_original_tolerance']:.9g}. The largest absolute difference{maxabs['absolute_difference']:.12g} occurs at H1[112,95] and does not fail its own tolerance; it is deliberately separated from the actual violation set.

Limitations and claim boundary: the vectors are close in aggregate but fail the unchanged pointwise criterion. This quantifies the numerical admission discrepancy; it does not qualify a reference gradient, identify a unique root cause, justify widening tolerances, or support either training arm. The penalty and its saved raw gradient are zero at this origin. A double arithmetic recombination of saved float32 parameter gradients still has9 violations; this is not double-precision model/energy replay and cannot prove that accumulation order is the only cause. Optimizer updates/history commits/FEM solves all0; two-arm training remains closed.

Next: preserve the original failure and these vectors for a separately scoped arithmetic-path diagnosis if requested. No automatic GPU replay or training follows this audit.
'''
    (a.out/'README_analysis.md').write_text(readme)
    (a.out/'gradient_discrepancy.md').write_text('# Gradient discrepancy\n\n'+readme)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--summary',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
