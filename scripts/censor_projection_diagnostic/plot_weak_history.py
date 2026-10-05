"""Visualization only: archived same-field UV vectors and history controls."""
import argparse,json,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('audit',type=Path);a=p.parse_args()
z=np.load(a.audit/'fields.npz');s=json.loads((a.audit/'summary.json').read_text());r=list(csv.DictReader((a.audit/'history_controls.csv').open()))
f=z['free_uv'];x=z['matlab_ru'].T.ravel()[f];y=z['pidl_grad_uv'].T.ravel()[f]
fig,ax=plt.subplots(1,2,figsize=(10,4),layout='constrained')
ax[0].scatter(x,y,s=2,alpha=.3,rasterized=True);v=max(abs(x).max(),abs(y).max());ax[0].plot([-v,v],[-v,v],color='black',lw=.8)
ax[0].set_xlabel('Archived MATLAB free UV residual');ax[0].set_ylabel('PIDL nodal energy gradient');ax[0].set_title('Same FEM c83 s4 field / raw vectors')
i=np.arange(len(r));ax[1].bar(i-.18,[float(v['box_rho_d_all']) for v in r],.36,label='All PIDL damage nodes');ax[1].bar(i+.18,[float(v['box_rho_d_common_free']) for v in r],.36,label='Common FEM free nodes')
ax[1].set_xticks(i,['P/P','F/P','P/Fprev','F/Fprev','F/Ftrial'],rotation=25);ax[1].set_xlabel('Damage history / fatigue coefficient');ax[1].set_ylabel('Box-projected damage residual');ax[1].legend(fontsize=8);ax[1].set_title('Fixed field / PIDL penalty coefficient')
out=a.audit/'figures';out.mkdir(exist_ok=True);fig.savefig(out/'weak_history_audit.png',dpi=180);fig.savefig(out/'weak_history_audit.pdf');plt.close(fig)
(out/'README_analysis.md').write_text('''# Same-field operator/history audit\n\nQuestion: does the original archived FEM weak UV residual equal the PIDL energy derivative, and how do qualified histories alter the fixed-field damage residual? Sources: S04-E003-R001 fields.npz, summary.json, history_controls.csv. Read left to right: all free raw UV components against the equality line; five frozen-history box-residual diagnostics. P=projected PIDL413 history (fatigue values retain original float32 mapping); F=qualified FEM prior accepted state; Ftrial is evaluated at the target then frozen, not differentiated. Both nodal sets use original total-area mass fractions, no re-normalization.\n\nAllowed: same-state discrete UV consistency and descriptive fixed-field history substitution. Numerical gate uses the mass-dual norm of the difference vector; scatter overlap is not the gate. Bar heights/norm reductions are nonadditive, not causal contribution percentages. FEM has251 fixed initial-crack nodes and different original penalty coefficient; bars all keep PIDL penalty16875. Damage-oracle comparison must be interpreted separately. No new solve, training, trajectory, or generalization claim. Storyline:S04; destination:censor research note.\n''')
