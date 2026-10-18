#!/usr/bin/env python3
"""Render the stored readout audit summary; no force, model, basis or solve."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--analysis',type=Path,required=True)
    args=ap.parse_args();root=args.analysis;source=root/'summary.json'
    data=json.loads(source.read_text());assert data['status']=='verified_frozen_numerical_diagnosis'
    bases=['source','fresh0','fresh1','fresh2'];target=1e-10
    groups=[('gpu','Saved GPU projection','#0072B2','o'),
            ('numpy_same_force','NumPy: identical saved force','#D55E00','s'),
            ('numpy_q4_force','NumPy: independent Q4 force','#009E73','^')]
    fig,ax=plt.subplots(figsize=(11.5,6.1),layout='constrained')
    for index,(kind,label,color,marker) in enumerate(groups):
        values=[next(r['gradient_inf'] for r in data['cross_gradients']
                     if r['basis']==b and r['force']=='network_0' and r['calculation']==kind) for b in bases]
        ax.plot(np.arange(4)+(index-1)*.12,values,ls='none',marker=marker,ms=8,color=color,label=label)
    auxiliary=[next(r['rawhead_T_gradient_inf'] for r in data['projection_order']
                    if r['basis']==b and r['force']=='network_0') for b in bases]
    ax.plot(np.arange(4)+.24,auxiliary,ls='none',marker='x',ms=9,color='#555555',
            label='Auxiliary: T transpose times raw head gradient')
    for j,b in enumerate(bases):
        g=next(r['gradient_inf'] for r in data['cross_gradients']
               if r['basis']==b and r['force']=='network_0' and r['calculation']=='gpu')
        ax.annotate(f'{g:.4e}\n'+('PASS' if g<=target else 'MISS'),(j,g),xytext=(0,13),
                    textcoords='offset points',ha='center',fontsize=11,color='black')
    ax.axhline(target,color='#B2182B',ls='--',lw=1.5)
    ax.text(3.45,target,'  unchanged target 1e-10',ha='right',va='top',fontsize=10,color='#B2182B')
    ax.text(1.5,2.15e-10,'Auxiliary readout: about 2.054e-10 in every basis',ha='center',fontsize=11,color='#555555')
    ax.set_xticks(range(4),['Saved-T Phi\n(reconstructed this run)','Fresh build 0','Fresh build 1','Fresh build 2'])
    ax.set_xlim(-.55,3.5);ax.set_ylim(0,2.4e-10)
    ax.set_ylabel('Head-gradient infinity norm (basis-specific coordinates)')
    ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.grid(axis='y',alpha=.2)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.14),ncol=2,fontsize=9,frameon=False)
    fig.suptitle('Frozen PIDL c20s4: same fields and forces, different numerical readouts',fontsize=14)
    ax.set_title('8 force arrays identical; 3 fresh bases identical; zero parameter/history updates',fontsize=10,pad=12)
    path=root/'readout_decision.png';assert not path.exists();fig.savefig(path,dpi=170);plt.close(fig)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    caption=('Same frozen PIDL c20s4 endpoint, fixed conditional FEM damage, native Q4/2x2 GP, original UV boundary and retained Smooth B0 damage parameterization. '
             'Dots use network_0; all eight force readouts are identical. Source means cached design times the older saved T, '
             'not an archived complete Phi from the older run. The three primary calculations agree on PASS/MISS at the unchanged 1e-10 target. '
             'The gray cross is auxiliary T-transformed raw parameter gradient and does not replace actual-Phi stationarity. '
             'Across-basis infinity norms are coordinate dependent; fixed-force physical basis-images are reported separately in the CSV. '
             'No field, network parameter or history changes. This reproduces a possible numerical admission mechanism, not the uniquely established cause of the earlier failed run.')
    path.with_suffix('.md').write_text('# Frozen c20 readout decision\n\n'+caption+
        '\n\n## Data provenance\n\nSource: '+str(source.resolve())+'; SHA256 '+digest+
        '. Exact source fields, Phi, forces and cross vectors are bound by summary.json and raw_capture_manifest.json at the Run root. '
        'Producer commit a698ec7b; this posthoc rendering performs no numerical replay.\n\n## How to read\n\n'
        'Linear y axis from zero, no display clipping or transformed metric. Dashed line is exactly 1e-10. '
        'Black labels refer to the primary saved-GPU actual-Phi readout. The gray auxiliary crosses use a distinct computational path. '
        'All three fresh columns are repetitions on one cached input and one mass0, not independent initializations.\n\n## Limitation\n\n'+caption+'\n')


if __name__=='__main__':main()
