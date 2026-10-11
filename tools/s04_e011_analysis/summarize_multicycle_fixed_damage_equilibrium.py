#!/usr/bin/env python3
"""Combine bounded equilibrium, raw-unbounded sensitivity and field replay evidence."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_multicycle_fixed_damage_equilibrium as m

OUT=HERE/"multicycle_fixed_damage_equilibrium"

def main():
    global OUT
    ap=argparse.ArgumentParser()
    ap.add_argument("--analysis-root",type=Path,required=True)
    ap.add_argument("--handoff",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    analysis=args.analysis_root.resolve()
    OUT=(args.output or analysis/"multicycle_fixed_damage_equilibrium").resolve()
    m.RUN=analysis.parent; m.REPLAY=analysis/"multicycle_cross_replay"; m.OUT=OUT
    m.HANDOFF=args.handoff.resolve()
    eq=json.load(open(OUT/"summary.json")); raw=json.load(open(OUT/"raw_unbounded_pidl_eta0_replay.json")); field=json.load(open(analysis/"multicycle_cross_replay/summary.json"))
    retry=json.load(open(OUT/"q4_c60_pidl_eta0_max25_retry.json"))
    one_sided=json.load(open(OUT/"t3_one_sided_bound_eta0_replay.json"))
    original={(r['topology'],r['cycle']):r for r in field['rows']}
    attribution=[]
    for r in eq['damage_effect_comparisons']:
        if r['eta']!=1e-6: continue
        o=original[(r['topology'],r['cycle'])]
        attribution.append({**r,"original_active_relative_l2":o['active_relative_l2'],"original_active_correlation":o['active_correlation'],
                            "equilibrium_gap_fraction_of_original":r['equilibrium_active_rel_l2']/o['active_relative_l2']})
    zero=[]
    for top in ('q4','t3'):
        kin,cycles,fem,pidl=m.load(top)
        for c in m.CYCLES:
            i=int(np.flatnonzero(cycles==c)[0])
            for arm,data in (("FEM",fem),("PIDL",pidl)):
                d=np.clip(data[2][i],0,1); dgp=np.einsum('ei,gi->eg',d[kin.cells],kin.shape); g=(1-dgp)**2
                zero.append({'topology':top,'cycle':c,'arm':arm,'nodes_at_one':int(np.count_nonzero(d>=1-1e-14)),
                             'zero_gp':int(np.count_nonzero(g<1e-28)),'fully_zero_elements':int(np.count_nonzero(np.all(g<1e-28,axis=1)))})
    decision={"schema":"s04e011-multicycle-fixed-damage-decision-v1","bounded_equilibrium":eq,"raw_unbounded_pidl_eta0":raw,
              "q4_c60_pidl_eta0_max25_retry":retry,"t3_one_sided_bound_eta0":one_sided,"active_gap_attribution":attribution,"zero_stiffness_diagnostics":zero,
              "interpretation":[
                  "Using the same topology-native equilibrium solver, replacing original displacement fields does not remove the FEM-PIDL active gap: 88-103% of original active rel-L2 remains across selected Q4/T3 cycles.",
                  "Therefore damage location/event branch is the dominant carrier of the active discrepancy; original PIDL displacement residuals are larger than FEM but are secondary before the event.",
                  "Strictly bounded T3 PIDL damage is eta=0 singular at all selected cycles. Lower-bound-only clipping still passes, whereas upper-bound-only clipping remains singular: d>1 overshoot specifically supplies artificial residual stiffness through (1-d)^2.",
                  "eta=1e-6 results are sensitivity evidence, not replacements for the frozen eta=0 contract."
              ]}
    (OUT/"decision_summary.json").write_text(json.dumps(decision,indent=2,allow_nan=False)+'\n')

    rows=eq['arm_replays']; comp=attribution
    fig,ax=plt.subplots(2,2,figsize=(11,8),sharex=True)
    for top,color in (("q4","#0072B2"),("t3","#D55E00")):
        cr=[x for x in comp if x['topology']==top]; c=[x['cycle'] for x in cr]
        ax[0,0].plot(c,[x['equilibrium_displacement_rel_l2'] for x in cr],'-o',color=color,label=top.upper())
        ax[0,1].plot(c,[x['equilibrium_gap_fraction_of_original'] for x in cr],'-o',color=color,label=top.upper())
        ax[1,0].plot(c,[x['pidl_damage_reaction_delta_pct'] for x in cr],'-o',color=color,label=top.upper())
        for arm,ls in (("FEM","-"),("PIDL","--")):
            rr=[x for x in rows if x['topology']==top and x['damage_source']==arm and x['eta']==1e-6 and x['status']=='PASS']
            ax[1,1].plot([x['cycle'] for x in rr],[x['original_common_operator_residual'] for x in rr],ls+'o',color=color,label=f'{top.upper()} {arm}')
    ax[0,0].set_ylabel('equilibrium displacement rel-L2')
    ax[0,1].set_ylabel('active rel-L2 remaining / original')
    ax[1,0].set_ylabel('PIDL-damage reaction vs FEM-damage (%)'); ax[1,0].set_yscale('symlog',linthresh=10)
    ax[1,1].set_ylabel('original-field common-operator residual'); ax[1,1].set_yscale('log')
    for a in ax.ravel(): a.axvspan(83,85,color='0.9',zorder=-5); a.grid(alpha=.25); a.legend()
    ax[1,0].set_xlabel('cycle'); ax[1,1].set_xlabel('cycle')
    fig.suptitle('Fixed-damage common-equilibrium causal intervention (eta=1e-6 sensitivity)')
    fig.tight_layout(); fig.savefig(OUT/'multicycle_fixed_damage_equilibrium_v2.png',dpi=220); plt.close(fig)
    print(json.dumps({'attribution':attribution,'retry':retry,'raw':raw},allow_nan=False))

if __name__=='__main__': main()
