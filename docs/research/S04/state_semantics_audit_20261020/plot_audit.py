"""Plot the exact saved-state index/commit audit, not a method-performance test."""
from pathlib import Path
import argparse,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    ap=argparse.ArgumentParser();ap.add_argument('audit',type=Path);args=ap.parse_args()
    with (args.audit/'state_map.csv').open() as f: rows=list(csv.DictReader(f))
    fig,(a,b)=plt.subplots(1,2,figsize=(13.5,4.7),gridspec_kw={'width_ratios':[1.35,1]},layout='constrained')
    cycles=[1,20,60,76,82,83,84,85,89]
    for y,pkg,label in [(1,'E011_pair_q4','Q4 pair'),(0,'E011_pair_t3','T3 pair')]:
        selected={int(r['cycle']):r for r in rows if r['package']==pkg}
        for x,c in enumerate(cycles):
            if c in selected:
                a.scatter(x,y,s=62,color='#0072B2',zorder=3)
                a.text(x,y+.16,str(int(float(selected[c]['pidl_raw_step']))),ha='center',fontsize=9)
            else:
                a.scatter(x,y,s=80,marker='x',color='#D55E00',zorder=3)
        a.text(-.6,y,label,ha='right',va='center',fontsize=10)
    a.set(xlim=(-.4,8.4),ylim=(-.5,1.7),xticks=range(len(cycles)),
          xticklabels=[str(c) for c in cycles],xlabel='Physical cycle (selected-state axis; unequal intervals)',yticks=[])
    a.set_title('Retained paired peaks: PIDL raw step shown above each dot',fontsize=11,pad=15)
    a.grid(axis='x',alpha=.16)
    a.text(.02,.96,'All listed pairs are s4. c84 is absent from the retained PIDL peak diagnostics.',
           transform=a.transAxes,fontsize=9,va='top',wrap=True)
    for y,arm in [(1,'original'),(0,'repaired')]:
        selected=sorted([r for r in rows if r['package']=='E011_c1_'+arm],key=lambda r:int(r['substep']))
        assert len(selected)==5
        for x,r in enumerate(selected):
            fresh=r['original_joint_pass']=='True'
            b.scatter(x,y,s=270,marker='s',facecolor='#009E73' if fresh else '#E69F00',edgecolor='white')
            b.text(x,y,str(r['accepted_version']),ha='center',va='center',color='white',weight='bold')
        b.text(-.55,y,arm,ha='right',va='center',fontsize=10)
    b.set(xlim=(-.4,4.4),ylim=(-.5,1.7),xticks=range(5),xticklabels=['1','2','3','4','5'],
          xlabel='Within-cycle substep; numbers inside = committed version',yticks=[])
    b.set_title('c1: one commit per substep, different acceptance rules',fontsize=11,pad=15)
    b.text(.02,.96,'Green: saved fresh joint check passed. Orange: native commit, fresh check missed.',
           transform=b.transAxes,fontsize=9,va='top',wrap=True)
    fig.suptitle('PIDL / FEM state audit — retained synthetic evidence, 20 October 2026',fontsize=13)
    for ax in [a,b]:
        ax.spines[['top','right','left']].set_visible(False)
    p=args.audit/'state_audit_decision.png';fig.savefig(p,dpi=180);plt.close(fig)
    print(p)

if __name__=='__main__':main()
