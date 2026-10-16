#!/usr/bin/env python3
"""E030 saved-output-only comparison figures; no fitting or source JPEG access."""
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
import numpy as np
from PIL import Image
from d01_conditional_interface import dump_new
from d01_t1_local_audit import read_csv

ARMS=('original_H','oldFIT','fixed_background')
LABELS=('Original H','Old FIT','Fixed background')
COLORS=('.5','#0072B2','#D55E00')
STYLES=(':','--','-')
MARKERS=('x','s','o')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--qa-directory',type=Path,required=True)
    p.add_argument('--run-id',default='S03-E030-D01-R002');a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean renderer required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E030-D01',run_id=a.run_id,role='render_only',code_commit=git('rev-parse','HEAD'),
        git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),python=sys.executable,command=sys.argv,gpu=None,
        source=str(a.source.resolve()),started_utc=datetime.now(timezone.utc).isoformat(),execution='running',
        retrieval='pending',numerical_rerun=False)
    try:
        numeric=json.loads((a.source/'runtime_receipt.json').read_text())
        if numeric['execution']!='succeeded' or numeric['protocol']!='T1-fixed-background-sampling-v1':
            raise ValueError('source identity mismatch')
        summary=json.loads((a.source/'summary.json').read_text());rows=read_csv(a.source/'measurements.csv')
        with np.load(a.source/'profiles.npz',allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
        q={r['arm']:r for r in summary['by_arm']};change=summary['changes_vs_oldFIT']['fixed_background']
        def row(j,arm):return next(r for r in rows if int(r['stage_index'])==j and r['arm']==arm)
        spec=importlib.util.spec_from_file_location('qa',a.qa_directory/'visual_qa.py')
        qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
        audits={}
        handles=[Line2D([],[],color=c,ls=ls,marker=m,label=label) for label,c,ls,m in zip(LABELS,COLORS,STYLES,MARKERS)]
        findings='\n'.join(f"- {label}: coverage {q[arm]['valid_profiles']}/3; widths {q[arm]['w30']}, {q[arm]['w40']}, {q[arm]['w50']} px; signed secant error {q[arm]['secant_error']} px; persistence error {q[arm]['persistence_error']} px." for arm,label in zip(ARMS,LABELS))
        guides={
            'F01_halfdepth_profiles':('How does the fixed location change the measured profiles?',
                'Columns30/40/50kN, top fullmedian intensity and shoulder background, bottom central intensity deficit with half-depth crossing markers. Shared gray scales and normal coordinates. Each arm uses its own frozen location and identical five-line operator. Horizontal crossing segments are half-depth widths, not uncertainty intervals.'),
            'F02_width_and_query':('Does this single background position remove the remaining supplied-Q50 mismatch?',
                'Left: all3stage widths, native first-frame pixels, connected in nominal load order only as a visual guide. Right: each arm signed error at suppliedQ50 for secant triangles and persistence squares, unconnected categorical arms; zero line means equality with that arm\'s own same-operator reference. No pooled performance statistic or new validation score.'),
            'F03_context_and_contributions':('Where do the fixed bands lie, and which stage changes account for the error change?',
                'Top: existing-photo-derived strips resampled onto original frozen n/t coordinates, gray0..255 shared. Three arm centre lines n[-30,30] at shift_t; width segments plotted at shift_t with their own crossing+shift_n coordinates. Dotted band bounds t=shift_t±2 shown for fixed-background arm only. Bottom: exact additive contributions -dw30,2dw40,-dw50,clip change and total error change versus oldFIT, categorical unconnected points with stems. Strip interpolation is context, not a raw pixel crop or a new measurement arm.')}
        def save(fig,name):
            fig.text(.5,.012,'E030-R001 | Beam4 T1 | viewed development | fixed positions saved first | optical px, not physical width | old scores unchanged',ha='center',fontsize=8)
            fig.canvas.draw();audits[name]=qa.audit_layout(fig)
            if any(level=='FAIL' for level,_ in audits[name]):raise RuntimeError('glyph failure')
            fig.savefig(a.output/f'{name}.png',dpi=300);fig.savefig(a.output/f'{name}.pdf')
            with Image.open(a.output/f'{name}.png') as im:im.convert('L').save(a.output/f'{name}_grayscale.png',dpi=(300,300))
            question,guide=guides[name]
            for gray in (False,True):
                stem=name+('_grayscale' if gray else '')
                (a.output/f'{stem}.md').write_text(f'''# {question}

## Data provenance and purpose
E030-R001 numeric commit {numeric['code_commit']}; {a.run_id} renderer {receipt['code_commit']}.
Exact source: {a.source.resolve()}; measurements.csv, profiles.npz, summary.json,
positions_before_width_access.json and source_images.json. Fixed position lock commit8218e32,
E029 all17 background affine centre. No new fit, offset search, image read or numerical replay in renderer.

## How to read every panel
{guide}
{'Grayscale QA: line style and marker distinguish arms.' if gray else 'Gray x OriginalH; blue dashed square oldFIT; orange solid circle fixed-background.'}

## Exact numerical takeaway
{findings}
Fixed-background change versus oldFIT: {json.dumps(change,allow_nan=False)}.

## Limitations and claim boundary
One already-viewed beam/transect, three nominal stages. Position stability does not establish
material-coordinate accuracy. Same images/H/sampler and background transfer can share bias.
Both history-derived prediction and target reference can change between arms; show them separately.
No physical-width accuracy, causal attribution, held-out forecast, confidence interval, probability,
new eight-case score or position selection by error. Half-depth operator/QC and oldscore files unchanged.

## Related assets
README_analysis.md; source summary and fixed_positions.json; protocol {repo}/docs/research/S03/S03-E030-D01/experiment.md.
''')
            plt.close(fig)
        s=arrays['normal_offsets']
        fig,axes=plt.subplots(2,3,figsize=(13,8),sharex='row',sharey='row')
        fig.subplots_adjust(left=.07,right=.98,bottom=.16,top=.86,hspace=.26,wspace=.12)
        fig.suptitle('Same half-depth operator at three predeclared locations',y=.98,fontsize=15)
        fig.text(.5,.92,'All stages and all arms shown; no position selected from width or query error',ha='center')
        all_deficits=[]
        for col,(j,load) in enumerate(zip((1,2,3),(30,40,50))):
            widths=[]
            for arm,c,ls,m in zip(ARMS,COLORS,STYLES,MARKERS):
                r=row(j,arm);key=f'st{j}_{arm}';widths.append(f"{float(r['width_px']):.3f}" if r['valid']=='True' else 'NA')
                if key+'_profile' not in arrays:continue
                axes[0,col].plot(s,arrays[key+'_profile'],color=c,ls=ls,lw=1.3)
                axes[0,col].plot(s,arrays[key+'_background'],color=c,ls=':',lw=.7,alpha=.5)
                deficit=arrays[key+'_deficit'];all_deficits.extend(deficit[(s>=-25)&(s<=30)])
                axes[1,col].plot(s,deficit,color=c,ls=ls,lw=1.3)
                if r['valid']=='True':
                    h=float(r['depth'])/2;edges=[float(r['left_px']),float(r['right_px'])]
                    axes[1,col].plot(edges,[h,h],color=c,ls=ls,marker=m,lw=1)
            axes[0,col].set_title(f'{load} kN | O / FIT / fixed = '+ ' / '.join(widths)+' px',fontsize=9)
            axes[0,col].set_ylim(0,255);axes[0,col].set_xlim(-60,60)
            axes[1,col].set_xlim(-25,30)
            for ax in axes[:,col]:ax.set_xlabel('Normal coordinate s (px)');ax.grid(color='.92',lw=.5)
        if all_deficits:axes[1,0].set_ylim(min(-10,min(all_deficits)-5),max(all_deficits)+5)
        axes[0,0].set_ylabel('Median intensity / background (gray)');axes[1,0].set_ylabel('Intensity deficit (gray)')
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.055),ncol=3,frameon=False)
        save(fig,'F01_halfdepth_profiles')
        fig,axes=plt.subplots(1,2,figsize=(12,6));fig.subplots_adjust(left=.08,right=.98,bottom=.22,top=.8,wspace=.25)
        fig.suptitle('Width trajectory and remaining supplied-Q50 error',y=.98,fontsize=15)
        fig.text(.5,.90,'Each arm is evaluated against its OWN same-definition 50 kN reference; not a new forecast score',ha='center',fontsize=10)
        for index,(arm,c,ls,m) in enumerate(zip(ARMS,COLORS,STYLES,MARKERS)):
            r=q[arm]
            if not r['available']:
                axes[1].text(index,.05,f"NA {r['valid_profiles']}/3",transform=axes[1].get_xaxis_transform(),ha='center',fontsize=9)
                continue
            axes[0].plot((30,40,50),[r['w30'],r['w40'],r['w50']],color=c,ls=ls,marker=m,lw=1.5)
            axes[1].scatter(index-.08,r['secant_error'],color=c,marker='^',s=70)
            axes[1].scatter(index+.08,r['persistence_error'],color=c,marker='s',s=45,facecolors='none')
            axes[1].annotate(f"{r['secant_error']:+.3f}",(index-.08,r['secant_error']),xytext=(0,-18),textcoords='offset points',ha='center',fontsize=9)
        axes[0].set_xticks((30,40,50));axes[0].set_xlabel('Supplied nominal load (kN)');axes[0].set_ylabel('Half-depth width (native px)')
        axes[0].set_ylim(bottom=0);axes[0].grid(color='.92',lw=.5)
        axes[1].axhline(0,color='.3',lw=.8);axes[1].set_xticks(range(3),LABELS);axes[1].set_ylabel('Prediction minus own reference (px)')
        axes[1].margins(y=.25,x=.2);axes[1].grid(axis='y',color='.92',lw=.5)
        fig.legend(handles=handles+[Line2D([],[],color='black',marker='^',ls='',label='Secant'),Line2D([],[],color='black',marker='s',mfc='none',ls='',label='Persistence')],
            loc='lower center',bbox_to_anchor=(.5,.065),ncol=5,frameon=False,fontsize=9)
        save(fig,'F02_width_and_query')
        fig=plt.figure(figsize=(13,8));gs=fig.add_gridspec(2,3,left=.07,right=.92,bottom=.14,top=.86,hspace=.45,wspace=.18)
        fig.suptitle('Fixed sampling bands and exact error-change contributions',y=.98,fontsize=15)
        fig.text(.5,.92,'Top: original-H n/t strips, resampled from existing photographs | Bottom: fixed-background minus oldFIT',ha='center',fontsize=10)
        for col,(j,load) in enumerate(zip((1,2,3),(30,40,50))):
            ax=fig.add_subplot(gs[0,col]);strip=arrays[f'st{j}_strip']
            im=ax.imshow(strip,origin='lower',extent=(-35.125,35.125,-8.125,8.125),cmap='gray',vmin=0,vmax=255,aspect='auto',interpolation='nearest')
            for arm,c,ls,m in zip(ARMS,COLORS,STYLES,MARKERS):
                r=row(j,arm);dn=float(r['shift_n']);dt=float(r['shift_t'])
                ax.plot(np.array([-30,30])+dn,[dt,dt],color=c,ls=ls,lw=.9)
                if r['valid']=='True':ax.plot(np.array([float(r['left_px']),float(r['right_px'])])+dn,[dt,dt],color=c,ls=ls,marker=m,lw=2)
                if arm=='fixed_background':
                    for yy in (dt-2,dt+2):ax.hlines(yy,-30+dn,30+dn,color=c,lw=.7,ls=':')
            ax.set_title(f'{load} kN');ax.set_xlabel('Original normal coordinate n (px)');ax.set_ylabel('Original tangent t (px)')
            ax.set_xlim(-35,35);ax.set_ylim(-8,8)
        cax=fig.add_axes([.94,.58,.013,.28]);fig.colorbar(im,cax=cax,label='Gray intensity')
        ax=fig.add_subplot(gs[1,:]);keys=('contribution30','contribution40','contribution50','delta_clip','delta_error')
        if change['available']:
            values=[change[k] for k in keys]
            ax.vlines(range(5),0,values,color='#D55E00',lw=1.2);ax.scatter(range(5),values,color='#D55E00',s=40)
            for i,v in enumerate(values):ax.annotate(f'{v:+.6f}',(i,v),xytext=(0,8 if v>=0 else -16),textcoords='offset points',ha='center',fontsize=9)
        ax.axhline(0,color='.4',lw=.8);ax.set_xticks(range(5),('-delta w30','2 x delta w40','-delta w50','Clip change','Total error change'))
        ax.set_ylabel('Signed contribution (px)');ax.margins(x=.12,y=.3);ax.grid(axis='y',color='.92',lw=.5)
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.045),ncol=3,frameon=False)
        save(fig,'F03_context_and_contributions')
        dump_new(a.output/'layout_audit.json',audits)
        (a.output/'README_analysis.md').write_text(f'''# E030 fixed-background sampling comparison

## Question and provenance
Does the ONE background-only E029 centre alter T1 half-depth widths and remaining Q50 mismatch?
Numeric source: {a.source.resolve()}, commit {numeric['code_commit']}; renderer {a.run_id}, {receipt['code_commit']}.
Fixed positions committed8218e32 before E030 width access. Existing three CRC-verified E012 JPEGs,
E018 geometry/H and unchanged half-depth operator; E026 baseline reproduction. No search or new data.

## Reading order and panels
1. F02 width trajectory and secant/persistence signed errors against each arm's own reference.
2. F01 all3stage median gray/background and deficit/crossing profiles, shared scales.
3. F03 same-scale original-H strips and three fixed bands; exact stage contribution decomposition.
Strips are resampled photo context, not untouched raw crops. Shapes/line styles plus grayscale aid comparison.
Full CSV/JSON are authoritative. No statistical uncertainty bars or significance claimed.

## Main results
{findings}
Changes versus oldFIT: {json.dumps(change,allow_nan=False)}.

## Interpretation and limits
A residual difference can come from changed historical prediction AND changed target reference.
This does not identify correct material coordinates, causal physical opening or new held-out forecasting.
Background and crack may not share a displacement field; images/H/sampler can share bias.
All3arms shown, no best-error selection. Half-depth definition and prior scores untouched.
See experiment.md for independent review, final disposition and smallest next action.

## Storyline impact and QA
This bounded intervention tests whether the stable background estimate removes the local discrepancy,
not whether an arbitrary position could do so. layout_audit.json contains mechanical checks;
actual colour/grayscale review must be recorded separately before evidence closure.
''')
        receipt.update(execution='succeeded',retrieval='verified_local',figure_sets=3,output=str(a.output.resolve()))
    except Exception as e:
        receipt.update(execution='failed',error=repr(e));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
