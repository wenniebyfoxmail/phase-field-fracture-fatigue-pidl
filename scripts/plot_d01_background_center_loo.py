#!/usr/bin/env python3
"""E029 render-only background centre/LOO comparison, no width or pixel inputs."""
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
from d01_t1_local_audit import read_csv
from d01_conditional_interface import dump_new

BLUE='#0072B2';ORANGE='#D55E00'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--qa-directory',type=Path,required=True);p.add_argument('--run-id',default='S03-E029-D01-R002');a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean renderer required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E029-D01',run_id=a.run_id,role='render_only',code_commit=git('rev-parse','HEAD'),git_dirty=False,
        hostname=socket.gethostname(),pid=os.getpid(),python=sys.executable,command=sys.argv,gpu=None,source=str(a.source.resolve()),
        execution='running',retrieval='pending',started_utc=datetime.now(timezone.utc).isoformat(),numerical_rerun=False)
    try:
        numeric=json.loads((a.source/'runtime_receipt.json').read_text())
        if numeric['execution']!='succeeded' or numeric['protocol']!='T1-background-center-LOO-v1':raise ValueError('source mismatch')
        ff=read_csv(a.source/'full_centres.csv');ll=read_csv(a.source/'leave_one_out_centres.csv');pp=read_csv(a.source/'temporal_pairs.csv')
        summary=json.loads((a.source/'summary.json').read_text());audits={}
        spec=importlib.util.spec_from_file_location('qa',a.qa_directory/'visual_qa.py');qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
        def full(j,support):return next(r for r in ff if r['stage_index']==str(j) and r['support_name']==support)
        primary=[r for r in summary['by_stage'] if r['support_name']=='all_available']
        takeaways='\n'.join(f"- {load}kN full tangential shift {float(full(j,'all_available')['t']):.9f}px; max absolute centre LOOchange {r['max_abs_delta_t']:.9f}px ({r['valid']}/{r['opportunities']})." for j,load,r in zip((1,2,3),(30,40,50),primary))
        guides={
            'F01_fixed_centres':('What single background-only estimate was fixed, and how does it compare with old FIT?',
                'Left normal n, right tangent t displacement at T1 centre, native first-frame pixels relative to original-H reference. Each named load has oldFIT grayx, PRIMARY all17 affine centre bluecircle and secondary flags-clear orangetriangle. Small horizontal offsets separate categories, not modified loads. Right vertical segments are finite min/max across single deletions of each support, NOT CI or accuracy bounds. No width or forecast values plotted.'),
            'F02_primary_tangent_LOO':('How much does each single deletion move the primary T1 tangent centre?',
                'Columns30/40/50kN; y is every retained background ID in fixed order. x=leave-one-out centre_t minus full17 centre_t, pixels, shared symmetric axes. Filledblue removed point was flags-clear; openblue removed point had a review flag. Zero graydotted is no change. These are centre influences, not E027 held-out-anchor prediction errors. IDs are categorical and not connected.'),
            'F03_relative_tangent_LOO':('Does deleting the same background point alter cross-stage relative tangent correspondence?',
                'Columns30→40 and40→50kN. Top PRIMARY all17, bottom secondary flags-clear support intersection for each pair, different IDs/counts stated. x=(LOO centre_t difference between stages)−(full centre_t difference), px, same axes across all panels; zero graydotted. Every supported omitted ID shown, no Cartesian independent-stage combination. Available/nominal support in titles; no line across categorical IDs.')}
        def save(fig,name):
            fig.text(.5,.012,'E029-R001 | Beam4 T1 | background-only viewed development | deletion stability is NOT physical accuracy | widths/scores unchanged',ha='center',fontsize=9)
            fig.canvas.draw();audits[name]=qa.audit_layout(fig)
            if any(level=='FAIL' for level,_ in audits[name]):raise RuntimeError('glyph failure')
            fig.savefig(a.output/f'{name}.png',dpi=300);fig.savefig(a.output/f'{name}.pdf')
            with Image.open(a.output/f'{name}.png') as im:im.convert('L').save(a.output/f'{name}_grayscale.png',dpi=(300,300))
            question,guide=guides[name]
            for gray in (False,True):
                stem=name+('_grayscale' if gray else '')
                text=f'''# How to read `{stem}`

## Figure question
{question}

## Data provenance
Exact source: {a.source.resolve()}. E029-R001 numeric {numeric['code_commit']}; {a.run_id} renderer {receipt['code_commit']}.
Tables: full_centres.csv, leave_one_out_centres.csv, temporal_pairs.csv, summary.json; source background correspondence/field tables and receipt are E027-R00165e424d, with hashes in input_identity.json.
Plotting: scripts/plot_d01_background_center_loo.py, saved-output only. No JPEG, width, E028 numerical result, fitting, forecast or score reading during rendering.

## Visual grammar
{guide}
{'Grayscale QA copy: use shape, fill and labels rather than hue.' if gray else 'Colourblind-safe roles plus marker/fill redundancy; paired grayscale copy supplied.'}

## Panel guide
{guide}

## Key numerical takeaway
{takeaways}
Primary relative tangent LOO maxchange30→40: {summary['by_transition'][0]['max_abs_change']:.9f}px;40→50: {summary['by_transition'][1]['max_abs_change']:.9f}px. These describe finite deletion influence only; no physical pass threshold.

## Limitations and claim boundary
One viewed beam/location, correlated/flagged image-background correspondences and shared H/sampler. All fits can share bias or violate affine continuity across the crack-like band. Small LOO is not accuracy, certified uncertainty, probability, independent material tracking or reliable transfer to crack edges. Primary estimator remains all17 OLS, not selected from width/error; secondary supports never replace it. No new widths sampled or old scores changed.

## Related assets
README_analysis.md; exact centre_weights.csv and input_identity.json; {repo}/docs/research/S03/S03-E029-D01/experiment.md. Colour PNG/PDF and same-stem grayPNG preserve exact saved sources.
'''
                (a.output/f'{stem}.md').write_text(text)
            plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(12,6));fig.subplots_adjust(left=.08,right=.98,bottom=.23,top=.78,wspace=.23)
        fig.suptitle('Fixed background-only T1 estimate versus old FIT',y=.98,fontsize=15)
        fig.text(.5,.90,'Primary = all17 affine centre | secondary = predeclared flags-clear support | vertical spans = finite LOO range, NOT accuracy',ha='center',fontsize=10)
        for ax,key in zip(axes,('n','t')):
            for j in (1,2,3):
                old=full(j,'all_available');ax.scatter(j-.13,float(old['old_'+key]),color='.5',marker='x',s=60)
                for support,color,marker,offset in (('all_available',BLUE,'o',0),('flags_clear',ORANGE,'^',.13)):
                    r=full(j,support);ax.scatter(j+offset,float(r[key]),color=color,marker=marker,s=40)
                    if key=='t':
                        values=[float(x['t']) for x in ll if x['support_name']==support and x['stage_index']==str(j) and x['available']=='True']
                        if values:ax.plot([j+offset]*2,[min(values),max(values)],color=color,lw=1,marker='_')
            ax.set_xticks((1,2,3),('30 kN','40 kN','50 kN'));ax.set_xlim(.6,3.4);ax.set_ylabel(('Normal' if key=='n' else 'Tangent')+' centre shift (px)');ax.axhline(0,color='.7',lw=.6);ax.grid(axis='y',color='.93')
        fig.legend(handles=[Line2D([],[],ls='',marker=m,color=c,label=l) for m,c,l in (('x','.5','Old FIT'),('o',BLUE,'Fixed all17 centre'),('^',ORANGE,'Secondary flags-clear8/6/5'))],loc='lower center',bbox_to_anchor=(.5,.09),ncol=3,frameon=False)
        save(fig,'F01_fixed_centres')
        fig,axes=plt.subplots(1,3,figsize=(13,7),sharex=True,sharey=True);fig.subplots_adjust(left=.08,right=.98,bottom=.19,top=.79,wspace=.16)
        fig.suptitle('Primary all17 estimate: every single-point deletion at the T1 centre',y=.98,fontsize=14)
        fig.text(.5,.91,'Changes relative to the full centre; filled/open describes the REMOVED point, not physical truth',ha='center',fontsize=10)
        lim=max(abs(float(r['delta_t'])) for r in ll if r['support_name']=='all_available' and r['available']=='True')*1.2
        for ax,j,st in zip(axes,(1,2,3),primary):
            rr=[r for r in ll if r['stage_index']==str(j) and r['support_name']=='all_available']
            for i,r in enumerate(rr):
                if r['available']=='True':ax.scatter(float(r['delta_t']),i,s=36,facecolors=BLUE if r['removed_flags_clear']=='True' else 'none',edgecolors=BLUE)
                else:ax.text(0,i,'unavailable',fontsize=8)
            ax.set_yticks(range(len(rr)),[r['left_out'] for r in rr]);ax.set_ylim(len(rr)-.3,-.7);ax.set_xlim(-lim,lim);ax.axvline(0,color='.5',ls=':',lw=.8);ax.grid(axis='x',color='.93')
            ax.set_title(f"{(30,40,50)[j-1]}kN | {st['valid']}/{st['opportunities']}\nmax |change|={st['max_abs_delta_t']:.4f}px",fontsize=11);ax.set_xlabel('T1 tangent centre change (px)')
        axes[0].set_ylabel('Removed background point')
        fig.legend(handles=[Line2D([],[],ls='',marker='o',color=BLUE,label='Removed point: flags clear'),Line2D([],[],ls='',marker='o',mfc='none',color=BLUE,label='Removed point: flagged')],loc='lower center',bbox_to_anchor=(.5,.06),ncol=2,frameon=False)
        save(fig,'F02_primary_tangent_LOO')
        fig,axes=plt.subplots(2,2,figsize=(12,10),sharex=True);fig.subplots_adjust(left=.09,right=.98,bottom=.12,top=.84,hspace=.34,wspace=.20)
        fig.suptitle('Same-deletion cross-stage tangent changes: primary versus secondary support',y=.98,fontsize=14)
        fig.text(.5,.92,'Difference change = centre influence at later stage minus that at earlier stage | finite influence, not a position error bound',ha='center',fontsize=10)
        lim=max(abs(float(r['change_delta_t'])) for r in pp if r['available']=='True')*1.2
        for row,support in enumerate(('all_available','flags_clear')):
            for col,(a_stage,b_stage) in enumerate(((1,2),(2,3))):
                rr=[r for r in pp if r['support_name']==support and r['stage_a']==str(a_stage) and r['stage_b']==str(b_stage)];ax=axes[row,col];color=BLUE if row==0 else ORANGE
                for i,r in enumerate(rr):
                    if r['available']=='True':ax.scatter(float(r['change_delta_t']),i,s=34,marker='o' if row==0 else '^',color=color)
                    else:ax.text(0,i,'unavailable',fontsize=8)
                ax.set_yticks(range(len(rr)),[r['left_out'] for r in rr]);ax.set_ylim(max(len(rr)-.3,.7),-.7);ax.set_xlim(-lim,lim);ax.axvline(0,color='.5',ls=':',lw=.8);ax.grid(axis='x',color='.93')
                ax.set_title(f"{'Primary all17' if row==0 else 'Secondary pair-common clear'} | {(30,40,50)[a_stage-1]}→{(30,40,50)[b_stage-1]}kN | {sum(r['available']=='True' for r in rr)}/{len(rr)}",fontsize=10)
                ax.set_ylabel('Removed point');ax.set_xlabel('Change in relative tangent displacement (px)')
        save(fig,'F03_relative_tangent_LOO')
        dump_new(a.output/'layout_audit.json',audits)
        lines=['# E029 background-only T1 centre stability','',f"Numeric: {a.source.resolve()} / {numeric['code_commit']}",f"Renderer: {receipt['run_id']} / {receipt['code_commit']}",'',
            '## Question and fixed choice','Primary: all17 background points, exact E027 OLS affine centre. Secondary flags-clear8/6/5 is only a sensitivity diagnostic, never a replacement. No widths/images/forecast errors were inputs.',
            '', '## Main numbers',takeaways,'', '## Reading order','F01: fixed centre against oldFIT and secondary; tangent vertical spans are finite deletion extrema, NOT CI or certified errors. F02: all17 individual centre influences with common axes. F03: same omitted ID across two stages, primary versus secondary support.',
            '', '## Interpretation','The primary centre is insensitive to deleting one point within this model/sample, not independently accurate. Single-deletion stability cannot detect common bias, shared-H errors, correlated templates or invalid affine continuity across the dark band.',
            'E027 LOO errors were held-out ANCHOR predictions; these new LOO values are changes at the T1 CENTRE. They are different quantities. Do not claim that anchor residuals have become0.03px accuracy.',
            'Primary relative30→40/40→50maxchanges: '+str([r['max_abs_change'] for r in summary['by_transition'] if r['support_name']=='all_available'])+'px.',
            'Secondary stage maxchanges: '+str([r['max_abs_delta_t'] for r in summary['by_stage'] if r['support_name']=='flags_clear'])+'px. Fewer quality-selected points can yield greater deletion sensitivity; do not cherry-pick support.',
            '', '## Missingness / evidence scope','6fullfields,70single-deletion opportunities and45pair opportunities. Source20origin candidates/17retained; all exclusion/quality rows preserved. No new threshold, likelihood or confidence claim; main conclusion is descriptive.',
            '', '## Next action','Final reviewed decision is in experiment.md. A later separately approved diagnostic may sample at the one fixed centre, without choosing offsets from width/error. No new width, correction application or rescoring was done in E029.']
        (a.output/'README_analysis.md').write_text('\n'.join(lines)+'\n')
        receipt.update(execution='succeeded',retrieval='verified_local',figure_sets=3,output=str(a.output.resolve()))
    except Exception as error:receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
