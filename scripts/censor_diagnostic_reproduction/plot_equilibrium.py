"""Two separate metrics for the fixed-clipped-damage counterfactual."""
import argparse,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('csv',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rows=list(csv.DictReader(a.csv.open()))
fig,axes=plt.subplots(1,2,figsize=(9,3.8),layout='constrained')
colors=['#0072B2','#D55E00']
for r,col in zip(rows,colors):
 label=r['state'].replace('_',' ')
 axes[0].plot([0,1],[float(r['original_normalized_free_residual']),float(r['solved_normalized_free_residual'])],'-o',color=col,label=label,lw=1.5)
 y=[float(r['original_active_rel_l2_vs_fem']),float(r['solved_active_rel_l2_vs_fem'])]
 axes[1].plot([0,1],y,'-o',color=col,label=label,lw=1.5)
 axes[1].annotate(f'{y[1]:.4f}',(1,y[1]),xytext=(6,0),textcoords='offset points',fontsize=9,color=col)
for ax in axes:
 ax.set_xticks([0,1],['Original displacement','Re-equilibrated']);ax.set_xlim(-.15,1.4);ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
axes[0].set_yscale('log');axes[0].set_ylabel('Normalized free-DOF residual');axes[0].set_title('(a) Equilibrium residual');axes[0].legend(frameon=False,fontsize=9)
axes[1].set_ylim(0,.5);axes[1].set_ylabel('Area-weighted active-driver relative L2');axes[1].set_title('(b) Field error against FEM')
fig.suptitle('Hard-5: fixed clipped PIDL damage, displacement-only solve',fontsize=11)
for ext in ('png','pdf'):fig.savefig(a.out/f'fixed_damage_equilibrium.{ext}',dpi=200)
