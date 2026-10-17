"""Decision-facing plots from saved exploratory measurements only."""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(base):
    old = pd.read_csv(base/'probe_v0_absolute/candidate_trajectories.csv')
    new = pd.read_csv(base/'probe_v1_concentration/candidate_trajectories.csv')
    groups = sorted(new.group.unique())
    fig, axes = plt.subplots(5,4,figsize=(14,14),layout='constrained')
    for ax, group in zip(axes.flat, groups):
        a = old[old.group==group].sort_values('stage')
        b = new[new.group==group].sort_values('stage')
        x = b.cycle_from_readme.to_numpy()/1000
        band = b[['span_px_threshold08','span_px','span_px_threshold125']].to_numpy()
        ax.plot(a.cycle_from_readme/1000,a.span_px,color='#a1a1aa',lw=.7,label='V0 absolute gradient')
        available = np.any(np.isfinite(band),axis=1)
        lower,upper = np.full(len(band),np.nan),np.full(len(band),np.nan)
        lower[available],upper[available] = np.nanmin(band[available],axis=1),np.nanmax(band[available],axis=1)
        ax.fill_between(x,lower,upper,color='#ef4444',alpha=.2)
        ax.plot(x,b.span_px,color='#b91c1c',lw=1,label='V1 concentration')
        ax.set_title(group,fontsize=9);ax.set_ylim(0,130);ax.tick_params(labelsize=7)
        ax.set_xlabel('Nominal cycles / 1000',fontsize=8);ax.set_ylabel('Projected span / px',fontsize=8)
    axes.flat[-1].axis('off')
    axes.flat[-1].text(0,.95,'Exploratory field measurement\n19 published specimen codes\nNo training or temporal smoothing\n\nBand = threshold-setting range,\nnot measurement uncertainty.\n\nCycles follow filename/README;\nphysical time/phase not certified.\n\nV0 retained; V1 is a candidate.\nNo qualified new ground truth.',va='top',fontsize=10)
    handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2)
    fig.suptitle('S02-E006 R009/R010 | Full Mendeley displacement exploration\nA bounded spatial-rule repair improves the proxy; no forecasting model was run',fontsize=13)
    fig.savefig(base/'candidate_trajectories_all19.png',dpi=160);plt.close(fig)

    z=np.load(base/'pt_selected_frames.npz')
    sample_rows=json.loads((base/'csv_sample_receipt.json').read_text())
    chosen=['E_0Deg_17.5%_#1','C_15Deg_20%_#1','E_0Deg_20%_#1']
    fig,axes=plt.subplots(3,3,figsize=(12,11),layout='constrained')
    for i,group in enumerate(chosen):
        for j,pos in enumerate(['early','middle','late']):
            ax=axes[i,j];a=z[group+'__'+pos][1]
            sample=next(r for r in sample_rows if r['group']==group and r['position']==pos)
            r=new[(new.group==group)&(new.stage==sample['stage'])].iloc[0]
            im=ax.imshow(a,origin='lower',cmap='viridis')
            if np.isfinite(r.left_px):
                ax.axvline(r.left_px,color='#ef4444',ls='--',lw=1)
                ax.axvline(r.right_px,color='#ef4444',ls='--',lw=1)
            ax.set_title(f"{group} | stage {sample['stage']}\nV1 support {r.span_px:.1f} px",fontsize=9)
            ax.set_xlabel('Grid column / px');ax.set_ylabel('Grid row / px')
            fig.colorbar(im,ax=ax,shrink=.65,label='Published channel 1')
    fig.suptitle('Current PT fields with exploratory projected support boundaries\nDashed lines are projected span limits, not certified physical crack tips; grid mapping unqualified',fontsize=12)
    fig.savefig(base/'candidate_field_overlays.png',dpi=160);plt.close(fig)

    lab=pd.read_csv(base/'probe_v1_concentration/published_label_probe.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for ax,(sheet,g) in zip(axes.flat,lab.groupby('sheet')):
        g=g.sort_values('published_cycle');ax.plot(g.published_cycle/1000,g.published_label,'o',ms=3,color='#111827',label='Published label')
        ax.plot(g.published_cycle/1000,g.nominal_mm_assuming_100_over_127,color='#b91c1c',label='V1, assumed scale')
        ax.set_title(sheet,fontsize=10);ax.set_xlabel('Nominal cycles / 1000');ax.set_ylabel('Published numeric value / nominal mm')
        ax.legend(fontsize=8)
    fig.suptitle('Existing-label development check, all 156 rows shown\n100/127 mm per pixel is provisional; label definition/unit and PT grid are not qualified\nShared DIC source: agreement is not independent physical accuracy',fontsize=12)
    fig.savefig(base/'published_label_comparison.png',dpi=160);plt.close(fig)
    print('Saved all-group trajectories, field overlays and all-label comparison')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);main(p.parse_args().base)
