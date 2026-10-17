"""Plot saved observations only; no predictions or smoothing."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--analysis',type=Path,required=True);a=ap.parse_args();data=json.loads((a.analysis/'state_space_inputs.json').read_text());fig,axs=plt.subplots(3,2,figsize=(12,12))
    for row,seq in enumerate(data['sequences']):
        obs=seq['observations'];load=np.array([o['metadata']['nominal_stage_load_kN'] for o in obs]);widths=np.array([o['model_widths_strip_px'] for o in obs],float);human=np.array([o['human_reference_widths_strip_px'] for o in obs],float)
        for j,cut in enumerate(seq['paired_visible_reference_transects']):
            line,=axs[row,0].plot(load,widths[:,j],'-o',label=f'Section {cut}: mask',lw=1.5,markersize=4);valid=np.isfinite(human[:,j]);axs[row,0].plot(load[valid],human[valid,j],linestyle='none',marker='D',mfc='none',mec=line.get_color(),markersize=7,label=f'Section {cut}: human endpoints')
        area=np.array([o['geometry']['candidate_area_reference_px2'] for o in obs]);clear=np.array([o['geometry']['eligible_area_reference_px2'] for o in obs]);axs[row,1].plot(load,area/1000,'-o',color='#47566b',label='All candidate pixels in common ROI');axs[row,1].plot(load,clear/1000,'-o',color='#0099b5',label='Eligible subset (screen varies)')
        axs[row,0].set(title=f'Beam{seq["beam_id"]}: fixed-section observations',xlabel='Nominal loading stage (kN)',ylabel='Width (saved strip-coordinate px)',ylim=(0,max(np.nanmax(widths),np.nanmax(human))*1.65));axs[row,1].set(title=f'Beam{seq["beam_id"]}: partial candidate geometry',xlabel='Nominal loading stage (kN)',ylabel='Area (1,000 reference px²)',ylim=(0,max(area)*1.2/1000))
        axs[row,0].legend(fontsize=7,loc='upper left',ncol=2);axs[row,1].legend(fontsize=7,loc='lower left')
        for ax in axs[row]:ax.grid(alpha=.2)
    fig.suptitle('D01: observed sequences prepared for state-space modelling — no fit or forecast\nMask widths retain boundary bias; area is partial candidate geometry. No monotonicity or confidence bands imposed.',fontsize=12);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(a.analysis/'F02_observation_sequences.png',dpi=150);plt.close(fig)


if __name__=='__main__':main()
