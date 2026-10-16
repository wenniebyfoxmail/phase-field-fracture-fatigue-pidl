#!/usr/bin/env python3
"""E027 saved-output-only figures; never recalculate width or match pixels."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

from d01_nearfield_correspondence import candidates
from d01_t1_local_audit import read_csv
from d01_conditional_interface import dump_new

BLUE='#0072B2';ORANGE='#D55E00';GREEN='#009E73'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--qa-directory',type=Path,required=True)
    p.add_argument('--run-id',default='S03-E027-D01-R002')
    a=p.parse_args();repo=Path(__file__).resolve().parents[1]
    git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean committed renderer required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E027-D01',run_id=a.run_id,role='render_only',code_commit=git('rev-parse','HEAD'),git_dirty=False,
                 hostname=socket.gethostname(),pid=os.getpid(),python=sys.executable,command=sys.argv,gpu=None,
                 source=str(a.source.resolve()),started_utc=datetime.now(timezone.utc).isoformat(),execution='running',retrieval='pending')
    try:
        r=json.loads((a.source/'runtime_receipt.json').read_text())
        if r['execution']!='succeeded' or r['protocol']!='near-background-v1':raise ValueError('source not qualified')
        summary=json.loads((a.source/'summary.json').read_text());rows=read_csv(a.source/'correspondences.csv')
        selection=json.loads(a.selection.read_text());decisions={r['anchor_id']:r['decision'] for r in selection['decisions']}
        cache=np.load(a.source/'display_arrays.npz',allow_pickle=False)
        spec=importlib.util.spec_from_file_location('figureqa',a.qa_directory/'visual_qa.py')
        qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
        audits={}
        def footer(fig):fig.text(.5,.014,'E027-R001 | Beam4 T1 | background proxies, not crack-edge truth | native first-frame px',ha='center',fontsize=9)
        def save(fig,name):
            fig.canvas.draw();audits[name]=qa.audit_layout(fig)
            if any(x=='FAIL' for x,_ in audits[name]):raise RuntimeError('glyph audit')
            fig.savefig(a.output/f'{name}.png',dpi=300);fig.savefig(a.output/f'{name}.pdf')
            with Image.open(a.output/f'{name}.png') as im:im.convert('L').save(a.output/f'{name}_grayscale.png')
            plt.close(fig)
        def subset(j):return [r for r in rows if int(r['stage_index'])==j]
        def available(j):return [r for r in subset(j) if r['available']=='True']
        def field(j,support):return next(r for r in summary['center_fields'] if r['stage_index']==j and r['support_name']==support)
        # Fixed context: vectors enlarged for legibility, anchor centres unchanged.
        fig,axes=plt.subplots(1,4,figsize=(15,5))
        fig.subplots_adjust(left=.05,right=.99,bottom=.18,top=.78,wspace=.15)
        fig.suptitle('New near-background anchors: first-frame screen and three target stages',y=.98,fontsize=15)
        fig.text(.5,.90,'Photo-derived registered contexts, gray 0..255 | arrows show measured displacement x6, NOT actual display locations',ha='center',fontsize=10)
        for j,ax in enumerate(axes):
            ax.imshow(cache[f'context_st{j}'],origin='lower',extent=(-85.5,85.5,-60.5,60.5),cmap='gray',vmin=0,vmax=255,interpolation='nearest')
            ax.set_title('10 kN reference' if j==0 else f'{(10,30,40,50)[j]} kN target')
            ax.set_xlabel('n (px)');ax.set_ylabel('t (px)' if j==0 else '')
            ax.plot(0,0,'+',color='white',ms=8)
            for c in candidates():
                if decisions[c['anchor_id']]!='accept':ax.plot(c['n'],c['t'],'x',color=ORANGE,ms=6);continue
                ax.plot(c['n'],c['t'],'o',mfc='none',mec=BLUE,ms=4)
                ax.text(c['n']+2,c['t']+1,c['anchor_id'][1:],fontsize=6,color=BLUE)
            if j:
                rr=available(j)
                ax.quiver([float(r['n']) for r in rr],[float(r['t']) for r in rr],
                          [float(r['dn'])*6 for r in rr],[float(r['dt'])*6 for r in rr],
                          angles='xy',scale_units='xy',scale=1,color=BLUE,width=.007)
            ax.set_xlim(-85,85);ax.set_ylim(-60,60)
        fig.legend(handles=[Line2D([],[],marker='o',mfc='none',color=BLUE,ls='',label='17 accepted background templates'),
                            Line2D([],[],marker='x',color=ORANGE,ls='',label='3 first-frame exclusions'),
                            Line2D([],[],marker='+',color='.4',ls='',label='T1 centre (not a width boundary)')],
                   loc='lower center',bbox_to_anchor=(.5,.07),ncol=3,frameon=False,fontsize=9)
        footer(fig);save(fig,'F01_anchor_contexts')
        # Compare displacement vectors and residuals in n/t displacement space.
        fig,axes=plt.subplots(2,3,figsize=(13,8),sharex='row',sharey='row')
        fig.subplots_adjust(left=.07,right=.98,bottom=.18,top=.84,hspace=.25,wspace=.14)
        fig.suptitle('New measured background shifts versus the old FIT correction',y=.98,fontsize=14)
        fig.text(.5,.91,'Filled = flags clear; open = review flag; centre interpolation is a background model, not physical truth',ha='center',fontsize=10)
        allpoints=[r for r in rows if r['available']=='True']
        for col,j in enumerate((1,2,3)):
            f=field(j,'all_available');ax=axes[0,col]
            for row in available(j):
                clear=row['flags_clear']=='True'
                ax.scatter(float(row['dn']),float(row['dt']),s=30,facecolors=BLUE if clear else 'none',edgecolors=BLUE)
                axes[1,col].scatter(float(row['residual_dn']),float(row['residual_dt']),s=30,facecolors=BLUE if clear else 'none',edgecolors=BLUE)
            ax.scatter(f['old_dn'],f['old_dt'],marker='x',s=100,color=ORANGE,linewidths=2)
            if f['center_interpolation_available']:ax.scatter(f['center_dn'],f['center_dt'],marker='D',s=50,facecolors='none',edgecolors=GREEN)
            ax.set_title(f'{(10,30,40,50)[j]} kN | 17/20 candidate matches')
            for axis in axes[:,col]:axis.axhline(0,color='.65',lw=.6);axis.axvline(0,color='.65',lw=.6);axis.grid(color='.93',lw=.5)
            axes[1,col].set_xlabel('Normal component (px)')
        axes[0,0].set_ylabel('Measured tangent displacement (px)');axes[1,0].set_ylabel('After old correction: tangent residual (px)')
        for ax in axes[0]:ax.set_xlim(min(float(r['dn']) for r in allpoints)-.15,max(float(r['dn']) for r in allpoints)+.15);ax.set_ylim(min(float(r['dt']) for r in allpoints)-.15,max(float(r['dt']) for r in allpoints)+.15)
        lim=max(max(abs(float(r[k])) for r in allpoints) for k in ('residual_dn','residual_dt'))*1.15
        for ax in axes[1]:ax.set_xlim(-lim,lim);ax.set_ylim(-lim,lim)
        fig.legend(handles=[Line2D([],[],marker='o',color=BLUE,ls='',label='New-anchor candidate displacement'),
                            Line2D([],[],marker='x',color=ORANGE,ls='',label='Old FIT shift'),
                            Line2D([],[],marker='D',mfc='none',color=GREEN,ls='',label='Near-background affine centre')],
                   loc='lower center',bbox_to_anchor=(.5,.06),ncol=3,frameon=False,fontsize=9)
        footer(fig);save(fig,'F02_displacement_and_residuals')
        fig,axes=plt.subplots(1,3,figsize=(13,8),sharex=True,sharey=True)
        fig.subplots_adjust(left=.08,right=.98,bottom=.15,top=.82,wspace=.12)
        fig.suptitle('Every candidate: residual norm before and after the old correction',y=.98,fontsize=14)
        fig.text(.5,.91,'Same anchors paired; exclusions and quality flags remain visible. Lower is better on these background proxies.',ha='center',fontsize=10)
        for col,j in enumerate((1,2,3)):
            ax=axes[col];rr=subset(j);stat=summary['by_stage'][col]
            clear=sum(r['flags_clear']=='True' for r in rr)
            for i,row in enumerate(rr):
                if row['available']!='True':ax.text(.03,i,'origin excluded',fontsize=8,color='.5');continue
                before=float(row['before_norm_px']);after=float(row['after_norm_px'])
                ax.plot([before,after],[i,i],color='.75',lw=.8)
                ax.scatter(before,i,color='.6',marker='s',s=20)
                ax.scatter(after,i,facecolors=BLUE if row['flags_clear']=='True' else 'none',edgecolors=BLUE,marker='^',s=30)
            ax.set_title(f"{stat['load_kN']} kN | flags clear {clear}/17\nmedian {stat['median_before_norm_px']:.3f} -> {stat['median_after_norm_px']:.3f}px",fontsize=11)
            ax.set_yticks(range(20),[c['anchor_id'] for c in candidates()]);ax.set_ylim(19.7,-.7)
            ax.grid(axis='x',color='.92',lw=.5);ax.set_xlabel('Background displacement / residual norm (px)')
        axes[0].set_xlim(0,max(float(r['before_norm_px']) for r in allpoints)*1.1)
        fig.legend(handles=[Line2D([],[],marker='s',color='.6',ls='',label='No extra correction'),Line2D([],[],marker='^',color=BLUE,ls='',label='After old FIT correction (open = flagged)')],
                   loc='lower center',bbox_to_anchor=(.5,.06),ncol=2,frameon=False,fontsize=9)
        footer(fig);save(fig,'F03_paired_residual_norms')
        fig,axes=plt.subplots(2,3,figsize=(13,8))
        fig.subplots_adjust(left=.07,right=.98,bottom=.10,top=.83,hspace=.30,wspace=.20)
        fig.suptitle('Correspondence self-consistency and limits of centre interpolation',y=.98,fontsize=14)
        fig.text(.5,.91,'Dotted 0.5px lines are review flags, not certified accuracy. LOO interior/exterior support reported separately.',ha='center',fontsize=10)
        def fmt(x):return 'n/a' if x is None else f'{x:.3f}'
        for col,j in enumerate((1,2,3)):
            ax=axes[0,col]
            for row in available(j):
                if row['roundtrip_px'] and row['template_difference_px']:
                    ax.scatter(float(row['roundtrip_px']),float(row['template_difference_px']),s=35,
                               facecolors=BLUE if row['flags_clear']=='True' else 'none',edgecolors=BLUE)
            ax.axhline(.5,color='.5',ls=':',lw=.8);ax.axvline(.5,color='.5',ls=':',lw=.8)
            ax.set_xlim(0,.85);ax.set_ylim(0,.85);ax.set_xlabel('Reverse loop residual (px)');ax.set_ylabel('Template-size difference (px)')
            ax.set_title(f'{(10,30,40,50)[j]} kN');ax.grid(color='.94')
            ax=axes[1,col];ax.axis('off');full=field(j,'all_available');clear=field(j,'flags_clear')
            text=[]
            for label,f in (('All candidates',full),('Flags-clear subset',clear)):
                text.extend([f"{label}: n={f['support']}",f"Centre inside hull: {f['origin_inside_hull']}",
                             f"Centre - old FIT: {fmt(f['center_difference_from_old_px'])} px",
                             f"LOO inside: {fmt(f['loo_inside_RMS_px'])} px / n={f['loo_inside_count']}",
                             f"LOO outside: {fmt(f['loo_outside_RMS_px'])} px / n={f['loo_outside_count']}",''])
            ax.text(0,1,'\n'.join(text),transform=ax.transAxes,va='top',fontsize=9,family='monospace')
        footer(fig);save(fig,'F04_consistency_and_transfer_limits')
        # Full accepted-template gallery at the named 40kN diagnostic stage, not ranked by outcome.
        accepted=[c for c in candidates() if decisions[c['anchor_id']]=='accept']
        for page,start_index in enumerate(range(0,len(accepted),6),1):
            group=accepted[start_index:start_index+6]
            fig,axes=plt.subplots(len(group),4,figsize=(9,1.5*len(group)+1),squeeze=False)
            fig.subplots_adjust(left=.08,right=.98,bottom=.08,top=.90,hspace=.28,wspace=.05)
            fig.suptitle(f'All accepted anchors, ID order | fixed40kN comparison | page{page}',y=.98,fontsize=12)
            for i,c in enumerate(group):
                keys=[f"{c['anchor_id']}_reference",f"st2_{c['anchor_id']}_uncorrected",f"st2_{c['anchor_id']}_old",f"st2_{c['anchor_id']}_matched"]
                for col,key in enumerate(keys):
                    ax=axes[i,col]
                    if key in cache:ax.imshow(cache[key],cmap='gray',vmin=0,vmax=255,interpolation='nearest')
                    else:ax.text(.5,.5,'unavailable',ha='center',va='center')
                    ax.set_xticks([]);ax.set_yticks([])
                    if i==0:ax.set_title(('Reference10kN','40kN no extra shift','40kN old FIT shift','40kN NCC candidate')[col],fontsize=9)
                    if col==0:ax.set_ylabel(c['anchor_id'],rotation=0,labelpad=20)
            footer(fig);save(fig,f'F05_gallery_page{page}')
        dump_new(a.output/'layout_audit.json',audits)
        lines=['# Analysis: S03-E027-D01','', '## Scientific question',
               'Does the old correction transfer to independent near-background proxies around T1? No widths/scores are changed.',
               '', '## Evidence identity',f'- Numeric source: {a.source.resolve()} (R001).',f'- Renderer: {a.run_id}.',
               '- First-frame origin screen by context-isolated agent:17accepted /20; N05/N09/N10 excluded before matching.',
               '- Context/gallery are existing-photo-derived resampled pixels, fixed gray0..255; not native unwarped crops.',
               '- New anchors do not overlap old FIT/CHECK footprints. Shared H/sampler and correlated templates limit independence.',
               '', '## Reading order',
               '1. F03: every candidate, paired before/after residual norm. Open symbols retain predeclared review flags.',
               '2. F01: all4 contexts; arrows x6 for visibility, not actual displayed material-point positions.',
               '3. F02: n/t displacement space, old correction versus new candidates; residuals share axes.',
               '4. F04: reverse/size self-consistency and LOO hull support; dotted .5px is NOT a physical accuracy line.',
               '5. F05 pages: every accepted anchor, ID order, at named40kN stage with fixed primary15x15 pixels. Other stages remain in F01-F04/tables.',
               '', '## Main numerical takeaways']
        for stat in summary['by_stage']:
            lines.append(f"- {stat['load_kN']}kN:17/20candidate matches; median norm {stat['median_before_norm_px']:.6f} -> {stat['median_after_norm_px']:.6f}px; median paired change {stat['median_paired_norm_change_px']:.6f}px.")
        lines.extend([f"- Flags clear {summary['flags_clear']}/{summary['primary_available']}available, out of{summary['combined_opportunities']}nominal opportunities. Empty flag strings mean no flags, NOT missing data.",
                      '- Counts and all flag reasons remain in correspondences.csv/matches.csv. No correlation-based causal claim or significance test.',
                      '', '## Cross-figure interpretation',
                      'Old translation reduces near-background residuals at all three stages; centre agreement is a spatial-model diagnostic, not direct crack-edge validation.',
                      'Affine field spans a crack-like band, may cross displacement discontinuity, and shares image geometry with old method. Subpixel agreement is NOT certified accuracy.',
                      'The flags-clear subset is small; LOO interior support can be zero. Retain those unavailable checks, do not substitute fit residuals as validation.',
                      '', '## Allowed and blocked conclusions',
                      'Allowed: background-level corroboration of direction/magnitude and remaining position residuals; no application of the new affine field.',
                      'Blocked: reliable physical crack-edge transfer, true material displacement, physical width, improved old score or unseen validation.',
                      '', '## Storyline impact and next action',
                      'Consult experiment.md and independent review for final decision. Propagation of residual position uncertainty into the fixed width remains future work, not performed here.',
                      'Four main figure sets plus all-accepted gallery pages; PNG/PDF/grayscale and layout audits. Agent visual inspection recorded after opening outputs.'])
        (a.output/'README_analysis.md').write_text('\n'.join(lines)+'\n')
        receipt.update(execution='succeeded',retrieval='verified_local',main_figure_sets=4,gallery_pages=int(np.ceil(len(accepted)/6)),numerical_rerun=False,output=str(a.output.resolve()))
    except Exception as error:
        receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
