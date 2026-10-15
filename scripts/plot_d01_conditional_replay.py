#!/usr/bin/env python3
"""Render all eight E025 cases from saved evaluated outputs, no measurement rerun."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image

from d01_conditional_interface import ARMS, dump_new, summarize

COLORS = {"reference":"#111111", "persistence":"#888888", "secant":"#0072B2"}
MARKERS = {"reference":"o", "persistence":"s", "secant":"^"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--qa-directory",type=Path,required=True)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"):raise RuntimeError("clean committed renderer required")
    args.output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();cpu=time.process_time()
    receipt=dict(experiment_id="S03-E025-D01",run_id="S03-E025-D01-R002",role="render_only",
                 code_commit=git("rev-parse","HEAD"),git_dirty=False,hostname=socket.gethostname(),
                 pid=os.getpid(),python=sys.executable,command=sys.argv,gpu=None,
                 source=str(args.source.resolve()),output=str(args.output.resolve()),
                 started_at_utc=datetime.now(timezone.utc).isoformat(),execution="running",retrieval="pending")
    try:
        original_receipt=json.loads((args.source/"runtime_receipt.json").read_text())
        if original_receipt["execution"]!="succeeded" or original_receipt["protocol"]!="conditional-interface-v1":
            raise ValueError("source run not qualified")
        rows=json.loads((args.source/"evaluated_rows.json").read_text())
        cases=json.loads(args.ledger.read_text())["cases"]
        metrics,summary=summarize(rows,cases)
        if summary!=json.loads((args.source/"summary.json").read_text()):
            raise ValueError("source summary differs from saved evaluated rows")
        spec=importlib.util.spec_from_file_location("figure_visual_qa",args.qa_directory/"visual_qa.py")
        qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                             "pdf.fonttype":42,"svg.fonttype":"none"})
        issues={}
        def save(fig,stem):
            fig.canvas.draw()
            report=qa.audit_layout(fig)
            issues[stem]=report
            if any(level=="FAIL" for level,_ in report):raise RuntimeError("figure glyph audit failed")
            fig.savefig(args.output/f"{stem}.png",dpi=180)
            fig.savefig(args.output/f"{stem}.pdf")
            with Image.open(args.output/f"{stem}.png") as im:
                im.convert("L").save(args.output/f"{stem}_grayscale.png")
            plt.close(fig)
        def footer(fig):
            fig.text(.5,.015,"S03-E025-D01-R001 | controlled beam | viewed development | native first-frame px, not mm",
                     ha="center",fontsize=9)
        def panels(title):
            fig,axes=plt.subplots(4,2,figsize=(12,13),sharex=True,sharey=True)
            fig.subplots_adjust(left=.08,right=.98,bottom=.075,top=.90,hspace=.34,wspace=.13)
            fig.suptitle(title,y=.98,fontsize=15)
            for i,(ax,c,m) in enumerate(zip(axes.flat,cases,metrics)):
                ax.set_title(f"{chr(97+i)}  {c['case_id']} | common {m['N_C']}/{m['N']}",fontsize=11,loc="left")
                ax.set_xticks(range(1,13));ax.set_xlim(.5,12.5)
                ax.grid(axis="y",color=".91",linewidth=.6)
            for ax in axes[-1]:ax.set_xlabel("Fixed transect ID (categorical)")
            footer(fig)
            return fig,axes
        fig,axes=panels("Given nominal L*: half-depth image width, all eight cases")
        for ax,c in zip(axes.flat,cases):
            rr=sorted((r for r in rows if r["case_id"]==c["case_id"]),key=lambda r:r["transect_id"])
            for name,dx in (("reference",0),("persistence",-.15),("secant",.15)):
                points=[(r["transect_id"]+dx,r["reference_px"] if name=="reference" else r["arms"][name]["prediction_px"])
                        for r in rr if (r["R"] if name=="reference" else r["arms"][name]["success"])]
                if points:ax.scatter(*zip(*points),s=23,color=COLORS[name],marker=MARKERS[name],label=name)
        max_width=max([r["reference_px"] for r in rows if r["R"]]+
                      [r["arms"][a]["prediction_px"] for r in rows for a in ARMS if r["arms"][a]["success"]])
        axes[0,0].set_ylim(0,max_width*1.08)
        fig.supylabel("Half-depth image width (px)",x=.015)
        handles=[Line2D([],[],linestyle="none",marker=MARKERS[n],color=COLORS[n],label=n)
                 for n in ("reference","persistence","secant")]
        fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.5,.955),ncol=3,frameon=False)
        save(fig,"F01_all_case_widths")
        fig,axes=panels("Prediction minus same-operator reference: all transects, all cases")
        max_error=0
        for ax,c in zip(axes.flat,cases):
            ax.axhline(0,color=".3",lw=.8)
            rr=[r for r in rows if r["case_id"]==c["case_id"] and r["C"]]
            for name,dx in (("persistence",-.10),("secant",.10)):
                errors=[r["arms"][name]["prediction_px"]-r["reference_px"] for r in rr]
                max_error=max(max_error,max(map(abs,errors),default=0))
                ax.scatter([r["transect_id"]+dx for r in rr],errors,s=25,color=COLORS[name],marker=MARKERS[name])
        axes[0,0].set_ylim(-max_error*1.15,max_error*1.15)
        fig.supylabel("Signed prediction error (px)",x=.015)
        fig.legend(handles=handles[1:],loc="upper center",bbox_to_anchor=(.5,.955),ncol=2,frameon=False)
        save(fig,"F02_all_case_signed_errors")
        fig,ax=plt.subplots(figsize=(11,6.5))
        fig.subplots_adjust(left=.18,right=.98,bottom=.16,top=.82)
        for i,m in enumerate(metrics):
            p,s=m["persistence_MAE_px"],m["secant_MAE_px"]
            if p is not None:
                ax.plot([p,s],[i,i],color=".8",lw=1)
                for name,value in (("persistence",p),("secant",s)):
                    ax.scatter(value,i,s=48,marker=MARKERS[name],color=COLORS[name])
                ax.annotate(f"delta {s-p:+.3f}",(max(p,s),i),xytext=(12,0),textcoords="offset points",va="center",fontsize=9)
        ax.set_yticks(range(8),[c["case_id"] for c in cases]);ax.invert_yaxis()
        ax.set_xlim(0,max(m[a+"_MAE_px"] for m in metrics for a in ARMS)*1.45)
        ax.set_xlabel("Common-support case MAE (px); left is better")
        ax.grid(axis="x",color=".92")
        eq=summary["equal_beam"]
        fig.suptitle("Per-case comparison: original secant versus persistence",y=.97,fontsize=14)
        fig.text(.5,.91,f"Equal-beam MAE: persistence {eq['persistence_MAE_px']:.6f}, secant {eq['secant_MAE_px']:.6f} px\n"
                 f"Paired delta (secant - persistence): {eq['delta_MAE_px']:+.6f} px; descriptive, no holdout",
                 ha="center",fontsize=11)
        ax.legend(handles=handles[1:],loc="lower right",frameon=False)
        footer(fig);save(fig,"F03_case_MAE_comparison")
        fig,ax=plt.subplots(figsize=(11,6))
        fig.subplots_adjust(left=.17,right=.87,bottom=.20,top=.82)
        keys=["N_E","N_EQ","persistence_success","secant_success","N_R_on_EQ","N_C"]
        denominators=[[m["N"],m["N"],m["N_EQ"],m["N_EQ"],m["N_EQ"],m["N"]] for m in metrics]
        values=np.array([[m[k]/d if d else np.nan for k,d in zip(keys,ds)] for m,ds in zip(metrics,denominators)])
        im=ax.imshow(values,vmin=0,vmax=1,cmap="viridis",aspect="auto")
        for i,(m,ds) in enumerate(zip(metrics,denominators)):
            for j,(k,d) in enumerate(zip(keys,ds)):
                ax.text(j,i,f"{m[k]}/{d}",ha="center",va="center",color="black" if values[i,j]>.55 else "white")
        ax.set_yticks(range(8),[c["case_id"] for c in cases])
        ax.set_xticks(range(6),["E / N","E & Q / N","P success / E&Q","S success / E&Q","R / E&Q","Common C / N"],rotation=15,ha="right")
        fig.colorbar(im,ax=ax,label="Coverage fraction",fraction=.04,pad=.03)
        fig.suptitle("Coverage and denominators: no transect removed",y=.97,fontsize=14)
        fig.text(.5,.90,"E = historical eligibility; Q = valid query; R = measurable reference; P/S = method output",ha="center",fontsize=10)
        footer(fig);save(fig,"F04_coverage")
        dump_new(args.output/"layout_audit.json",issues)
        guide=f"""# Analysis: S03-E025-D01

## Scientific question
Does the history-only interface reproduce the eight viewed conditional-query cases,
with predictions saved before evaluation target decoding and explicit coverage?

## Evidence identity
- Numerical Run: {args.source.resolve()} (S03-E025-D01-R001).
- Renderer: S03-E025-D01-R002; {Path(__file__).resolve()}.
- Exact scored rows: evaluated_rows.json; predictions_before_evaluation.json precedes reference decoding.
- References: E015 cached same-operator half-depth image widths, NOT independent physical truth.
- Cases: all eight ledger cases in fixed order, T1-12 each; three beams, not96 independent specimens.
- Missing capabilities: unseen data, material-coordinate truth, physical aperture and prospective ingestion.

## Reading order and figure guide
1. F03_case_MAE_comparison: paired per-case MAE; negative annotated secant-persistence delta favors secant.
   Equal-beam MAE P={eq['persistence_MAE_px']:.9f}, S={eq['secant_MAE_px']:.9f}px,
   delta={eq['delta_MAE_px']:.9f}px. No statistical significance or threshold claim.
2. F01_all_case_widths: all reference/P/S widths, shared y limits, categorical transects, no connecting curves.
   Each beam's first-frame pixels are not a shared millimetre calibration. Jitter only separates markers.
3. F02_all_case_signed_errors: all common-support errors, common symmetric scale, zero is exact reference.
   These errors are software-observable mismatch, not physical metrology error. No CI/error bar is implied.
4. F04_coverage: numerator/denominator printed in each cell, fraction0-1. R and arm success conditional on E&Q;
   E, E&Q and C relative to nominal12. Missing and failure reasons remain in evaluated_rows.json.

## Cross-figure interpretation and allowed conclusion
All cases and coverage must be read with the unchanged old-development role. Numerical consistency
checks in legacy_comparison.json test software replay, not new independent prediction validation.
The figure set can expose which cases/transects favor each method without deleting difficult positions.

## Blocked conclusion
No physical opening accuracy, material-point tracking, blind/independent-beam or road generalisation,
causal load intervention, future load known at historical origin, or autonomous rollout evidence.

## Storyline impact and next action
Retain original half-depth observable and simple baselines. Consult experiment.md and independent
reviews for final C1 verdict; a visual improvement does not create a C2/C3 validation claim.
PNG/PDF and grayscale copies are generated from the same saved outputs; layout_audit.json records
programmatic QA. Human-agent visual inspection is separately recorded after opening the PNGs.
"""
        (args.output/"README_analysis.md").write_text(guide)
        receipt.update(execution="succeeded",retrieval="verified_local",figure_sets=4,numerical_rerun=False)
    except Exception as error:
        receipt.update(execution="failed",error=f"{type(error).__name__}:{error}")
        raise
    finally:
        receipt.update(ended_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-start,
                       cpu_seconds=time.process_time()-cpu)
        dump_new(args.output/"runtime_receipt.json",receipt)


if __name__=="__main__":main()
