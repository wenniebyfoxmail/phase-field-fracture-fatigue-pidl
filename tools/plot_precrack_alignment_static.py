"""Visualize static construction checks; never a trained improvement claim."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main(a):
    z=np.load(a.static/'initial_profiles.npz');q=np.load(a.static/'initial_inputs.npz');f=np.load(a.static/'initial_fields.npz')
    fig,ax=plt.subplots(1,2,figsize=(10.5,3.6),layout='constrained')
    ax[0].plot(z['y'],z['FEM_U0'],color='#0072B2',label='FEM U0',lw=2.5)
    ax[0].plot(z['y'],z['A_legacy'],color='#D55E00',label='A: saved PIDL U0',lw=1.5)
    ax[0].plot(z['y'],z['C_FEM_initial'],color='#009E73',label='C: aligned construction',lw=1.5,ls='--')
    ax[0].set(xlabel='y',ylabel='damage d',title='Initial transverse field at x=0',xlim=(-.025,.025),ylim=(-.01,1.04));ax[0].legend(fontsize=8)
    mask=q['crack_mask'];x=q['node_coords'][mask,0];order=np.argsort(x)
    for arm,color,label,ls in [('A_legacy','#D55E00','A: saved PIDL U0','-'),('B_hard_line','#777777','B: hard line',':'),('C_FEM_initial','#009E73','C: aligned','--')]:
        ax[1].plot(x[order],f[arm][mask][order],label=label,color=color,ls=ls)
    ax[1].set(xlabel='x on y=0',ylabel='damage d',title='251 prescribed precrack nodes',ylim=(.985,1.002));ax[1].legend(fontsize=8)
    for p in ax:p.spines[['top','right']].set_visible(False)
    fig.suptitle('Static initial-field construction only | zero optimizer steps / zero new FEM')
    fig.savefig(a.static/'precrack_alignment_static.png',dpi=180);plt.close(fig)
    note='''# How to read precrack_alignment_static.png

## Figure question
Does the opt-in construction enforce the same precrack line and initial damage field as saved FEM U0? This is a construction check, not evidence of trained improvement.

## Data provenance
Existing S04-E011 post-U0 PIDL model/checkpoint and saved original FEM recovered initial field. prepare_precrack_alignment.py creates initial_profiles.npz, initial_inputs.npz and initial_fields.npz with no optimizer or FEM solve. common_initial matches original state0 to2.78e-16; float64 FEM cast tofloat32 differs by at most2.98e-8. All arms use the same original NN weights. C equals the float32 FEM nodal initial by construction.

## Visual grammar and panels
Left: native-Q4 damage at x=0,y[-.03,.03], shown y[-.025,.025]. Blue FEM U0, orange saved PIDL U0, dashed green C initial construction. Blue and green overlap. Right: actual251 original precrack-line nodes sorted by x; orange A old PIDL, gray dotted B line-only, green dashed C. B and C equal1; vertical range.985-1.002 magnifies the original small line deficit. Native Q4 interpolation is used for the profile; actual node values are used for the line plot. No mirror averaging or clipping.

## Key takeaway
Both B and C impose d=1 on251 nodes. C additionally has zero nodal initial-field discrepancy to the declared float32 FEM initial target. This is deterministic equality, not an accuracy gain after loading.

## Limitations
Zero training steps, zero new FEM, zero history commits. C changes the initial representation/history and its tangent; it is not pure optimizer initialization. Outside the line, damage can evolve or heal under the retained soft penalty. No claim about c1s1 convergence, FEM agreement after loading, complete fatigue evolution or physical truth. See static_receipt.json and ../preparation_card.json.
'''
    (a.static/'precrack_alignment_static.md').write_text(note)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--static',type=Path,required=True);main(p.parse_args())
