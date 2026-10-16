#!/usr/bin/env python3
"""E028 render-only residual-to-width diagnostic; no images/measurements rerun."""
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

MODES=('normal_only','tangent_only','joint')
LABELS=('Normal only','Tangent only','Joint n+t')
COLORS=('#0072B2','#D55E00','#009E73');MARKERS=('s','^','o')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--qa-directory',type=Path,required=True);p.add_argument('--run-id',default='S03-E028-D01-R002')
    a=p.parse_args();repo=Path(__file__).resolve().parents[1]
    git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean renderer required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E028-D01',run_id=a.run_id,role='render_only',code_commit=git('rev-parse','HEAD'),git_dirty=False,
        hostname=socket.gethostname(),pid=os.getpid(),python=sys.executable,command=sys.argv,gpu=None,
        started_utc=datetime.now(timezone.utc).isoformat(),execution='running',retrieval='pending',source=str(a.source.resolve()),numerical_rerun=False)
    try:
        numeric=json.loads((a.source/'runtime_receipt.json').read_text())
        if numeric['execution']!='succeeded' or numeric['protocol']!='T1-residual-propagation-v1':raise ValueError('unqualified source')
        summary=json.loads((a.source/'summary.json').read_text());base=summary['baseline'];stats=summary['by_support']
        rr=read_csv(a.source/'source_residuals.csv');mm=read_csv(a.source/'profile_measurements.csv');cc=read_csv(a.source/'coherent_cases.csv')
        bb=read_csv(a.source/'baseline_measurements.csv');cache=np.load(a.source/'profiles.npz',allow_pickle=False)
        ids=[r['anchor30'] for r in cc if r['mode']=='joint'];audits={}
        spec=importlib.util.spec_from_file_location('qa',a.qa_directory/'visual_qa.py');qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
        stat=lambda mode,temp,support:next(r for r in stats if (r['mode'],r['temporal'],r['support'])==(mode,temp,support))
        takeaways='\n'.join(f"- {label}, same-anchor17: error [{stat(mode,'coherent','all_available')['secant_error_min']:.6f}, {stat(mode,'coherent','all_available')['secant_error_max']:.6f}]px; median {stat(mode,'coherent','all_available')['secant_error_median']:.6f}px." for mode,label in zip(MODES,LABELS))
        guides={
            'F01_residuals_and_width_response':('What are the input residual pairs and the resulting stage-width changes?',
                'Columns30/40/50kN. Top: source near-background residual n versus t (px), shared symmetric axes, open=flagged. Bottom: every accepted anchor ID, width change from oldFIT baseline in px for normal-only blue square, tangent-only orange triangle and joint green circle; open=stage flagged, offset markers are only categorical separation. Fixed same axes within rows; no lines across IDs.'),
            'F02_coherent_error_by_anchor':('Can same-anchor residual trajectories produce an error change of the remaining magnitude?',
                'Columns normal-only, tangent-only and joint. Each row is the same anchor across30/40/50kN. x is postclip secant prediction minus same-definition50kN value, px. Gray dotted vertical line is unchanged oldFIT error; black dashed zero. Filled=flags clear at all3 stages, open=at least one review flag. All17 accepted IDs remain, categorical IDs not connected. This is a conditional diagnostic, not new forecast scores.'),
            'F03_temporal_support_ranges':('How much does the result depend on cross-stage correspondence and quality support?',
                'Columns normal-only, tangent-only, joint. Rows: coherent all17, coherent flags-clear intersection, independent-stage Cartesian all17^3, Cartesian flags-clear8*6*5. Segment endpoints are finite scenario extrema; diamond is discrete median. Labels state valid/nominal counts. Shared signed-error axes, zero black dashed and oldFIT gray dotted. Segments are NOT CI, probability or certified error bounds; crossing zero does not assert an exact-zero sampled scenario.'),
            'F04_fixed_N01_profiles':('What does a fixed, non-selected example look like at the profile level?',
                'FixedID N01 in all3stages, not ranked by prediction error. Columns30/40/50kN; x normal offset in native first-frame pixels, y local intensity deficit in gray levels. Gray dashed baseline, blue dotted normal-only, orange dashdot tangent-only, green solid joint. Half-depth crossing endpoints marked at each profile own stored depth/2; widths in legend. Shared scales; no smoothing/renormalisation of cached deficit arrays. Full profiles are cached; display |normal offset|<=20 to expose the fixed peak/crossings, not a changed measurement window.')}
        def save(fig,name):
            fig.canvas.draw();audits[name]=qa.audit_layout(fig)
            if any(level=='FAIL' for level,_ in audits[name]):raise RuntimeError('glyph layout failure')
            fig.text(.5,.012,'E028-R001 | Beam4 T1 | viewed development | transfer assumed, not physical truth | old scores unchanged',ha='center',fontsize=9)
            fig.savefig(a.output/f'{name}.png',dpi=300);fig.savefig(a.output/f'{name}.pdf')
            with Image.open(a.output/f'{name}.png') as im:im.convert('L').save(a.output/f'{name}_grayscale.png',dpi=(300,300))
            question,guide=guides[name]
            for gray in (False,True):
                stem=name+('_grayscale' if gray else '')
                text=f'''# How to read `{stem}`

## Figure question
{question}

## Data provenance
E028-R001 numeric {numeric['code_commit']}; {a.run_id} renderer {receipt['code_commit']}.
Exact saved outputs: {a.source.resolve()}; source_residuals.csv, profile_measurements.csv, coherent_cases.csv, support_statistics.csv, baseline_measurements.csv, profiles.npz and summary.json.
Scripts/d01_residual_width_propagation.py samples3existing CRC-verified E012 JPEGs with E018 fixed geometry/H, E019 oldFIT and E027 paired residuals; E026 nominal baseline reproduced first. This renderer does NOT read JPEGs or recompute measurements/predictions.

## Visual grammar
{guide}
{'Grayscale QA copy; use marker shape, fill and line style rather than hue.' if gray else 'Colourblind-safe palette with marker/line-style/fill redundancy; paired grayscale QA copy supplied.'}

## Panel guide
{guide}

## Key numerical takeaway
Baseline signederror {base['secant_error']:.9f}px;153/153residual profiles valid.
{takeaways}
Flags-clear same-anchor intersection {len(summary['common_flags_clear_ids'])}/17; stage supports8/6/5. No scientific success threshold; finite scenarios describe sensitivity only.

## Limitations and claim boundary
All residuals are background proxies assumed transferable to T1, not certified crack-edge localization error. Same source images/H/sampler and correlated patches; only3stages of1viewed beam/location. Independent-stage combinations deliberately discard temporal pairing. Near-zero or improved counterfactual errors are not new forecasts, proof of causation or a selected correction. Do not change the half-depth definition or old scores.

## Related assets
README_analysis.md, exact numeric tables above; {repo}/docs/research/S03/S03-E028-D01/experiment.md. Colour PNG/PDF and grayscalePNG share source; all profiles stored over full original±60px window.
'''
                (a.output/f'{stem}.md').write_text(text)
            plt.close(fig)
        # Inputs and stage response: raw points, not pooled bars.
        fig,axes=plt.subplots(2,3,figsize=(13,10));fig.subplots_adjust(left=.08,right=.98,bottom=.17,top=.86,hspace=.40,wspace=.20)
        fig.suptitle('Observed background residuals propagated through the unchanged width operator',y=.98,fontsize=14)
        fig.text(.5,.93,'Top: observed n/t residual pairs | Bottom: width change at T1 under transfer assumption | open = review flag',ha='center',fontsize=10)
        lim=max(abs(float(r[k])) for r in rr if r['available']=='True' for k in ('residual_dn','residual_dt'))*1.15
        dwlim=max(abs(float(r['width_px'])-base[f"w{r['load_kN']}"]) for r in mm if r['valid']=='True')*1.15
        for col,j in enumerate((1,2,3)):
            ax=axes[0,col]
            for r in rr:
                if int(r['stage_index'])==j and r['available']=='True':ax.scatter(float(r['residual_dn']),float(r['residual_dt']),s=28,facecolors=COLORS[0] if r['flags_clear']=='True' else 'none',edgecolors=COLORS[0])
            ax.axhline(0,color='.6',lw=.6);ax.axvline(0,color='.6',lw=.6);ax.set_xlim(-lim,lim);ax.set_ylim(-lim,lim)
            ax.set_xlabel('Normal residual (px)');ax.set_ylabel('Tangent residual (px)');ax.set_title(f'{(30,40,50)[col]} kN')
            ax=axes[1,col]
            for i,aid in enumerate(ids):
                for k,mode in enumerate(MODES):
                    r=next(r for r in mm if r['stage_index']==str(j) and r['anchor_id']==aid and r['mode']==mode)
                    if r['valid']=='True':ax.scatter(float(r['width_px'])-base[f'w{(30,40,50)[col]}'],i+(k-1)*.19,s=24,marker=MARKERS[k],facecolors=COLORS[k] if r['flags_clear']=='True' else 'none',edgecolors=COLORS[k])
                    else:ax.text(0,i,'invalid',fontsize=7)
            ax.set_yticks(range(len(ids)),ids);ax.set_ylim(len(ids)-.3,-.7);ax.set_xlim(-dwlim,dwlim);ax.axvline(0,color='.6',lw=.7);ax.set_xlabel('Width change from old FIT (px)');ax.grid(axis='x',color='.93')
        fig.legend(handles=[Line2D([],[],marker=m,color=c,ls='',label=l) for m,c,l in zip(MARKERS,COLORS,LABELS)],loc='lower center',bbox_to_anchor=(.5,.055),ncol=3,frameon=False)
        save(fig,'F01_residuals_and_width_response')
        # Primary: every coherent same-anchor scenario, no best-case selection.
        fig,axes=plt.subplots(1,3,figsize=(13,7),sharex=True,sharey=True);fig.subplots_adjust(left=.08,right=.98,bottom=.16,top=.79,wspace=.13)
        fig.suptitle('Same-anchor residual trajectories: signed conditional-query error',y=.98,fontsize=14)
        fig.text(.5,.91,'Filled = flags clear in all3stages; open = at least one flag | zero crossing is sensitivity, not a repaired forecast',ha='center',fontsize=10)
        for k,(ax,mode,label) in enumerate(zip(axes,MODES,LABELS)):
            for i,aid in enumerate(ids):
                r=next(r for r in cc if r['mode']==mode and r['anchor30']==aid)
                if r['valid']=='True':ax.scatter(float(r['secant_error']),i,marker=MARKERS[k],s=42,facecolors=COLORS[k] if r['flags_clear']=='True' else 'none',edgecolors=COLORS[k])
                else:ax.text(0,i,'invalid',fontsize=8)
            ax.axvline(0,color='black',ls='--',lw=.8);ax.axvline(base['secant_error'],color='.5',ls=':',lw=1.2)
            st=stat(mode,'coherent','all_available');ax.set_title(f"{label}\nmedian {st['secant_error_median']:.3f}px",fontsize=11)
            ax.set_yticks(range(len(ids)),ids);ax.set_ylim(len(ids)-.3,-.7);ax.set_xlabel('Prediction - reference (px)');ax.grid(axis='x',color='.93')
        values=[float(r['secant_error']) for r in cc if r['valid']=='True']+[0,base['secant_error']]
        axes[0].set_xlim(min(values)-.2,max(values)+.2)
        fig.legend(handles=[Line2D([],[],color='black',ls='--',label='Zero error'),Line2D([],[],color='.5',ls=':',label=f"Old FIT baseline {base['secant_error']:.3f}px")],loc='lower center',bbox_to_anchor=(.5,.045),ncol=2,frameon=False)
        save(fig,'F02_coherent_error_by_anchor')
        fig,axes=plt.subplots(1,3,figsize=(13,5.8),sharex=True,sharey=True);fig.subplots_adjust(left=.16,right=.98,bottom=.19,top=.77,wspace=.15)
        fig.suptitle('Temporal pairing matters: finite scenario extrema, NOT probability intervals',y=.98,fontsize=14)
        fig.text(.5,.90,'Diamond = discrete median | endpoint segment = finite min/max, not certified bounds or an exact-zero solution',ha='center',fontsize=10)
        groups=(('coherent','all_available'),('coherent','flags_clear'),('independent_stage','all_available'),('independent_stage','flags_clear'))
        for k,(ax,mode,label) in enumerate(zip(axes,MODES,LABELS)):
            for i,(temp,support) in enumerate(groups):
                st=stat(mode,temp,support)
                if st['valid']:
                    ax.plot([st['secant_error_min'],st['secant_error_max']],[i,i],color=COLORS[k],lw=1.3,marker='|')
                    ax.scatter(st['secant_error_median'],i,color=COLORS[k],marker='D',s=30)
                ax.text(.98,i+.16,f"n={st['valid']}/{st['opportunities']}",transform=ax.get_yaxis_transform(),ha='right',fontsize=8)
            ax.axvline(0,color='black',ls='--',lw=.8);ax.axvline(base['secant_error'],color='.5',ls=':',lw=1.2)
            ax.set_title(label);ax.set_yticks(range(4),('Same anchor / all','Same anchor / clear','Independent / all','Independent / clear'))
            ax.set_ylim(3.5,-.5);ax.set_xlabel('Prediction - reference (px)');ax.grid(axis='x',color='.93')
        values=[s[k] for s in stats if s['valid'] for k in ('secant_error_min','secant_error_max')]+[0]
        axes[0].set_xlim(min(values)-.3,max(values)+.3)
        fig.text(.5,.085,f"17accepted IDs, flags-clear intersection{len(summary['common_flags_clear_ids'])}; independent stage supports8 x6 x5=240 | not independent specimens",ha='center',fontsize=9)
        save(fig,'F03_temporal_support_ranges')
        fig,axes=plt.subplots(1,3,figsize=(13,5.5),sharex=True,sharey=True);fig.subplots_adjust(left=.07,right=.98,bottom=.32,top=.76,wspace=.15)
        fig.suptitle('Fixed N01 profile illustration: old FIT versus residual-shifted sampling',y=.98,fontsize=14)
        fig.text(.5,.90,'Each trace uses its own unchanged half-depth threshold; N01 is fixed by ID, not selected for lower error',ha='center',fontsize=10)
        yy=[]
        for col,j in enumerate((1,2,3)):
            ax=axes[col];br=bb[col];bprof=cache[f'st{j}_baseline_deficit'];xx=cache['normal_offsets']
            ax.plot(xx,bprof,color='.4',ls='--',lw=1.2,label=f"Old FIT w={float(br['width_px']):.3f}")
            ax.plot([float(br['left_px']),float(br['right_px'])],[float(br['depth'])/2]*2,'x',color='.4',ms=5)
            yy.extend(bprof[np.abs(xx)<=20])
            for k,mode in enumerate(MODES):
                r=next(r for r in mm if r['stage_index']==str(j) and r['anchor_id']=='N01' and r['mode']==mode)
                key=f'st{j}_N01_{mode}_deficit'
                if key not in cache:continue
                ax.plot(xx,cache[key],color=COLORS[k],ls=(':','-.','-')[k],lw=1.1,label=f"{LABELS[k]} w={float(r['width_px']):.3f}" if r['valid']=='True' else f"{LABELS[k]} invalid")
                yy.extend(cache[key][np.abs(xx)<=20])
                if r['valid']=='True':ax.plot([float(r['left_px']),float(r['right_px'])],[float(r['depth'])/2]*2,ls='',marker=MARKERS[k],mfc='none',mec=COLORS[k],ms=4)
            ax.set_title(f'{(30,40,50)[col]} kN');ax.set_xlabel('Normal offset (px)');ax.set_xlim(-20,20);ax.legend(loc='upper left',bbox_to_anchor=(0,-.30),fontsize=8,frameon=False)
        axes[0].set_ylabel('Local intensity deficit (gray)');axes[0].set_ylim(min(yy)-10,max(yy)+10)
        save(fig,'F04_fixed_N01_profiles')
        dump_new(a.output/'layout_audit.json',audits)
        lines=['# E028 residual-to-width interpretation','',f"Numeric: {a.source.resolve()} / {numeric['code_commit']}",f"Renderer: {a.run_id} / {receipt['code_commit']}",'',
            '## Question and boundary','Can observed residual-position SCENARIOS generate the remaining optical-query error magnitude? Background-to-T1 transfer is ASSUMED, not verified.',
            'No new correction, new forecast, old eight-case replay or old scoring change. Signs are prediction minus reference. All17 anchors, flags retained; one viewed beam/location.',
            '', '## Numerical result',f"Baseline E026 aligned widths {base['w30']:.9f}/{base['w40']:.9f}/{base['w50']:.9f}px; error {base['secant_error']:.9f}px. Reproduced before propagation.",takeaways,
            f"153/153 profiles;51coherent cases and14739 independent-stage combinations; flags-clear intersection {summary['common_flags_clear_ids']}, not separately chosen best points.",
            '', '## Reading order','F02: all17 coherent scenarios versus baseline and zero. F01: input residuals and stage-width responses. F03: temporal pairing and quality supports. F04: fixedID N01 full-operator profile illustration.',
            '', '## Interpretation','Normal-only finite scenarios cannot remove the miss. Tangent/joint extrema have both signs, including flags-clear same-anchor support; this is conditional sensitivity, NOT cause identification or a guaranteed true-location range.',
            'Joint same-anchor median remains near the old miss; selecting a near-zero scenario would be target-informed tuning, not prediction. Cartesian near-zero errors especially are not a solution or probability.',
            'The unchanged secant raw-error change decomposes as -delta_w30+2delta_w40-delta_w50 plus a separately recorded clip-change. Nonlinear n/t effects need not add.',
            '', '## Data and missingness','E027 has60 nominal source anchor-stage rows/51available. Empty flag text means flags-clear, not imputed missing. E028 sampled17accepted only; excluded IDs are preserved in source_residuals.csv, no replacement.',
            'Flags-clear8/6/5 per stage; Cartesian240 does not create240 physical observations. No zero fill, no Gaussian/CI/significance statements.',
            '', '## Limits / next decision','Residuals are not certified physical errors, and their transfer to the crack band remains unresolved. Do not claim actual crack narrowing/reopening or reliably corrected coordinates.',
            'Independent numerical/visual review and final decision are recorded in experiment.md. Keep the same width/old scores; a later discriminator should separate spatial transfer from residual optical trend, not choose a best background anchor.']
        (a.output/'README_analysis.md').write_text('\n'.join(lines)+'\n')
        receipt.update(execution='succeeded',retrieval='verified_local',figure_sets=4,output=str(a.output.resolve()))
    except Exception as error:receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
