"""Orthogonal parity decomposition of saved disagreement, not a model repair."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def components(error, parity):
    compatible=.5*(error+parity*error[::-1])
    violating=.5*(error-parity*error[::-1])
    total=float(np.sum(error**2));a=float(np.sum(compatible**2));b=float(np.sum(violating**2))
    assert abs(total-a-b)<1e-12*max(total,1e-30)
    return dict(error_RMS=float(np.sqrt(np.mean(error**2))),
                parity_compatible_squared_fraction=a/total if total else None,
                parity_violating_squared_fraction=b/total if total else None)


def main(args):
    out=args.analysis;rows=[]
    early=out/'front_fields.npz'
    with np.load(early) as z:
        for s in [2,4]:
            for name in ['u','v_correction','d','eps_xx','eps_yy','gamma_xy','raw','active']:
                error=z[f'PIDL-Q4-c1s{s}__{name}']-z[f'FEM-Q4-c1s{s}__{name}']
                rows.append(dict(state=f'c1s{s}',topology='Q4',field=name,support='302x160 native Q4 probes; x[0,.5],y[-.04,.04]',
                                 source=str(early),**components(error,-1 if name in ['v_correction','gamma_xy'] else 1)))
    late=args.root/'local_archive/ppt7_bc_audit_20261017/c83_display_fields.npz'
    with np.load(late) as z:
        for top in ['Q4','T3']:
            error=z['PIDL_'+top]-z['FEM_'+top]
            rows.append(dict(state='c83s4',topology=top,field='d',support='301x161 existing common T3 display interpolation; same bounds',
                             source=str(late),**components(error,1)))
    with (out/'error_parity_components.csv').open('w') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained',gridspec_kw={'width_ratios':[2,1]})
    fields=['u','v_correction','d','gamma_xy','raw','active']
    for s,offset,color in [(2,-.18,'#386a8f'),(4,.18,'#d67c45')]:
        vals=[100*next(r['parity_violating_squared_fraction'] for r in rows if r['state']==f'c1s{s}' and r['field']==n) for n in fields]
        bars=axs[0].bar(np.arange(len(fields))+offset,vals,.34,label=f'Q4 c1s{s}',color=color)
        axs[0].bar_label(bars,labels=[f'{v:.2f}' if v<.1 else f'{v:.1f}' for v in vals],fontsize=8,padding=2)
    axs[0].set_xticks(np.arange(len(fields)),['u','v - lifting','damage','shear','raw energy','active energy'],rotation=20)
    axs[0].legend();axs[0].set_title('Early same-state disagreement | native Q4 reconstruction')
    vals=[100*r['parity_violating_squared_fraction'] for r in rows if r['state']=='c83s4']
    bars=axs[1].bar(['Q4','T3'],vals,color=['#386a8f','#d67c45']);axs[1].bar_label(bars,fmt='%.1f',padding=3)
    axs[1].set_title('c83 damage\nExisting display interpolation')
    for ax in axs:
        ax.set_ylim(0,100);ax.set_ylabel('Parity-violating part of squared disagreement (%)')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Saved FEM/PIDL differences include substantial parity-compatible mismatch\nOrthogonal decomposition only; percentages are not causal repair gains',fontsize=11)
    fig.savefig(out/'error_parity_decomposition.png',dpi=180);plt.close(fig)
    (out/'decomposition_receipt.json').write_text(json.dumps(dict(sources=[str(early),str(late)],
        metric='E_viol=(E-s*R(E))/2; compatible and violating parts orthogonal on declared symmetric uniform probes',
        warning='No modified model, mirrored damage output, or counterfactual improvement is claimed',
        rows=len(rows)),indent=2)+'\n')
    print(f'Saved {len(rows)} deterministic decomposition rows and figure')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True)
    main(p.parse_args())
