#!/usr/bin/env python3
"""E026 figures: fixed T1 stages, saved numerics and CRC-verified existing JPEGs."""
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

from d01_background_anchor_diagnostic import load_inputs,load_gray
from independent_d01_halfdepth import native_to_source
from d01_conditional_interface import dump_new
from d01_t1_local_audit import read_csv,ARMS,STAGES,LOADS,T,S

BLUE="#0072B2";ORANGE="#D55E00"
STAGE_COLORS=["#009E73",BLUE,ORANGE]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--inputs",type=Path,required=True);p.add_argument("--qa-directory",type=Path,required=True)
    args=p.parse_args();repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"):raise RuntimeError("clean committed renderer required")
    args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id="S03-E026-D01",run_id="S03-E026-D01-R002",role="render_only",
                 code_commit=git("rev-parse","HEAD"),git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),
                 command=sys.argv,python=sys.executable,gpu=None,source=str(args.source.resolve()),
                 started_utc=datetime.now(timezone.utc).isoformat(),execution="running",retrieval="pending")
    try:
        r=json.loads((args.source/"runtime_receipt.json").read_text())
        if r["execution"]!="succeeded" or r["protocol"]!="T1-local-audit-v1":raise ValueError("unqualified source")
        summary=json.loads((args.source/"summary.json").read_text())
        rows=read_csv(args.source/"measurements.csv");positions=read_csv(args.source/"position_counterfactuals.csv")
        corrections={int(r["stage_index"]):r for r in read_csv(args.source/"translations.csv")}
        checks=read_csv(args.source/"check_support.csv")
        g,H,_,_=load_inputs(args.inputs);tr=g["transects"][0]
        n=np.array(tr["normal"]);tangent=np.array([-n[1],n[0]]);center=np.array(tr["center"])
        cache=np.load(args.source/"selected_cache.npz",allow_pickle=False)
        spec=importlib.util.spec_from_file_location("figureqa",args.qa_directory/"visual_qa.py")
        qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        plt.rcParams.update({"font.size":10,"pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})
        audits={}
        def footer(fig):
            fig.text(.5,.015,"E026-R001 | Beam4 T1 | posthoc development | optical native px, not physical opening",ha="center",fontsize=9)
        def save(fig,name):
            fig.canvas.draw();audits[name]=qa.audit_layout(fig)
            if any(a=="FAIL" for a,_ in audits[name]):raise RuntimeError("glyph audit")
            fig.savefig(args.output/f"{name}.png",dpi=300);fig.savefig(args.output/f"{name}.pdf")
            with Image.open(args.output/f"{name}.png") as im:im.convert("L").save(args.output/f"{name}_grayscale.png")
            plt.close(fig)
        def subset(arm,j):
            return sorted([r for r in rows if r["arm"]==arm and int(r["stage_index"])==j],key=lambda r:float(r["tangent_px"]))
        def zero(arm,j):return next(r for r in subset(arm,j) if float(r["tangent_px"])==0)
        # Native crops are not warped; bottom strips were already sampled in E020.
        fig,axes=plt.subplots(2,3,figsize=(13,8))
        fig.subplots_adjust(left=.06,right=.98,bottom=.10,top=.86,hspace=.34,wspace=.22)
        fig.suptitle("Where T1 samples the same three existing photographs",y=.98,fontsize=15)
        fig.text(.5,.92,"Top: untouched native gray crops + mapped sample lines | Bottom: cached registered strip, original H",ha="center")
        sources=[]
        for col,(j,load) in enumerate(zip(STAGES,LOADS)):
            stage=g["stages"][j];image=load_gray(stage);sources.append(stage)
            def mapped(s,tt=0,aligned=False):
                correction=corrections[j]
                delta=(float(correction["shift_n"])*n+float(correction["shift_t"])*tangent) if aligned else 0
                points=center+np.asarray(s)[:,None]*n+tt*tangent+delta
                return native_to_source(points,np.linalg.inv(H[j]),g["native_shape"],g["working_shape"])
            c=mapped(np.array([0.]))[0];cx,cy=np.rint(c).astype(int)
            if cx-55<0 or cy-55<0 or cx+55>image.shape[1] or cy+55>image.shape[0]:raise ValueError("crop outside image")
            ax=axes[0,col];crop=image[cy-55:cy+55,cx-55:cx+55]
            ax.imshow(crop,cmap="gray",vmin=0,vmax=255,extent=(cx-55-c[0],cx+55-c[0],cy+55-c[1],cy-55-c[1]),interpolation="nearest")
            for tt in (-2,0,2):
                q=mapped(np.array([-35.,35.]),tt)
                ax.plot(q[:,0]-c[0],q[:,1]-c[1],color=BLUE,lw=1.3 if tt==0 else .65,alpha=.9 if tt==0 else .6)
            q=mapped(np.array([-35.,35.]),aligned=True)
            ax.plot(q[:,0]-c[0],q[:,1]-c[1],color=ORANGE,lw=1.3,ls="--")
            ax.set_title(f"{int(load)} kN | {Path(stage['source_image']).name}",fontsize=10)
            ax.set_xlabel("Native source x offset (px)");ax.set_ylabel("Native source y offset (px)")
            ax.set_xlim(-55,55);ax.set_ylim(55,-55)
            ax=axes[1,col];strip=cache[f"st{j}_tr1_original_H_strip"]
            ax.imshow(strip,origin="lower",extent=(-60.5,60.5,-14.25,14.25),cmap="gray",vmin=0,vmax=255,interpolation="nearest",aspect="auto")
            for yy in (-2,2):ax.axhline(yy,color=BLUE,lw=.65)
            z=zero(ARMS[0],j);ax.plot([float(z["left_px"]),float(z["right_px"])],[0,0],color=BLUE,lw=2,marker="|")
            ax.set_xlim(-35,35);ax.set_ylim(-10,10)
            ax.set_xlabel("Frozen normal coordinate s (px)");ax.set_ylabel("Frozen tangent t (px)")
            ax.set_title(f"Median5 band t=-2..2 | width {float(z['width_px']):.3f}px",fontsize=10)
        fig.legend(handles=[Line2D([],[],color=BLUE,label="original sampling"),Line2D([],[],color=ORANGE,ls="--",label="existing FIT shift")],
                   loc="lower center",bbox_to_anchor=(.5,.045),ncol=2,frameon=False)
        footer(fig);save(fig,"F01_native_and_registered_context")
        # Original and existing-aligned profiles share gray and deficit scales.
        fig,axes=plt.subplots(2,3,figsize=(13,8),sharex="row",sharey="row")
        fig.subplots_adjust(left=.07,right=.98,bottom=.11,top=.85,hspace=.25,wspace=.12)
        fig.suptitle("Half-depth crossing moves: fixed operator, two existing sample locations",y=.98,fontsize=14)
        fig.text(.5,.92,"Shoulder fit uses |s|=45..60; same gray scale and no new smoothing",ha="center")
        for col,(j,load) in enumerate(zip(STAGES,LOADS)):
            for arm,color,ls in ((ARMS[0],BLUE,"-"),(ARMS[1],ORANGE,"--")):
                key=f"st{j}_tr1_{arm}";z=zero(arm,j)
                axes[0,col].plot(S,cache[key+"_profile"],color=color,ls=ls,lw=1.5)
                axes[0,col].plot(S,cache[key+"_background"],color=color,ls=":",lw=.8)
                ax=axes[1,col];ax.plot(S,cache[key+"_deficit"],color=color,ls=ls,lw=1.5)
                ax.hlines(float(z["half_level"]),float(z["left_px"]),float(z["right_px"]),color=color,lw=1.5,linestyle=ls)
                ax.scatter([float(z["left_px"]),float(z["right_px"])],[float(z["half_level"])]*2,color=color,s=25,marker="o" if arm==ARMS[0] else "s")
            axes[0,col].set_title(f"{int(load)} kN | O {float(zero(ARMS[0],j)['width_px']):.2f} / A {float(zero(ARMS[1],j)['width_px']):.2f}px")
            axes[0,col].set_xlim(-60,60);axes[0,col].set_ylim(0,255)
            axes[1,col].set_xlim(-25,30);axes[1,col].set_ylim(-10,100)
            for ax in axes[:,col]:ax.grid(color=".92",lw=.5);ax.set_xlabel("Normal coordinate s (px)")
        axes[0,0].set_ylabel("Median intensity / background (gray)")
        axes[1,0].set_ylabel("Intensity deficit (gray)")
        fig.legend(handles=[Line2D([],[],color=BLUE,label="O: original H"),Line2D([],[],color=ORANGE,ls="--",label="A: existing background shift")],loc="lower center",bbox_to_anchor=(.5,.04),ncol=2,frameon=False)
        footer(fig);save(fig,"F02_profiles_and_crossings")
        fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey="row")
        fig.subplots_adjust(left=.08,right=.98,bottom=.11,top=.84,hspace=.28,wspace=.14)
        fig.suptitle("Location response on the fixed +/-2 px / 0.5 px grid",y=.98,fontsize=14)
        fig.text(.5,.92,"Same nominal tangent position at each stage; not verified material coordinates",ha="center")
        for col,arm in enumerate(ARMS):
            for j,load,color,marker in zip(STAGES,LOADS,STAGE_COLORS,("o","s","^")):
                axes[0,col].plot(T,[float(r["width_px"]) for r in subset(arm,j)],color=color,marker=marker,lw=1.3,label=f"{int(load)} kN")
            rr=[r for r in positions if r["arm"]==arm and r["mode"]=="common" and r["valid"]=="True"]
            for name,color,marker,label in (("delta_history",BLUE,"o","40-30"),("delta_next",ORANGE,"s","50-40"),("secant_error","#555555","^","secant error")):
                axes[1,col].plot([float(r["t30"]) for r in rr],[float(r[name]) for r in rr],color=color,marker=marker,lw=1.2,label=label)
            axes[0,col].set_title(arm.replace("_"," "))
            for ax in axes[:,col]:ax.axvline(0,color=".6",lw=.6,ls=":");ax.grid(color=".92",lw=.5)
            axes[1,col].axhline(0,color=".3",lw=.7);axes[1,col].set_xlabel("Common tangent offset t (px)")
        axes[0,0].set_ylabel("Half-depth width (px)");axes[1,0].set_ylabel("Stage change / signed error (px)")
        axes[0,0].legend(frameon=False,fontsize=9);axes[1,0].legend(frameon=False,fontsize=9)
        footer(fig);save(fig,"F03_position_response")
        fig,axes=plt.subplots(2,2,figsize=(12,9),sharey="row")
        fig.subplots_adjust(left=.08,right=.98,bottom=.14,top=.85,hspace=.33,wspace=.14)
        fig.suptitle("Last-query error = preceding change minus observed next change",y=.98,fontsize=14)
        fig.text(.5,.92,"Top: nominal t=0 | Bottom: complete deterministic grid, not uncertainty probabilities",ha="center")
        for col,arm in enumerate(ARMS):
            a=summary["by_arm"][col];nom=a["nominal"];ax=axes[0,col]
            ax.plot(LOADS,[nom["w30"],nom["w40"],nom["w50"]],color="black",marker="o",lw=1.3,label="same-operator reference")
            ax.plot([40,50],[nom["w40"],nom["secant"]],color=BLUE,marker="^",ls="--",lw=1.3,label="secant")
            ax.plot([40,50],[nom["w40"],nom["persistence"]],color=".55",marker="s",ls=":",lw=1.3,label="persistence")
            ax.set_xticks(LOADS);ax.set_xlabel("Nominal load (kN)");ax.set_title(arm.replace("_"," "))
            ax.text(.03,.06,f"d_history {nom['delta_history']:+.3f}, d_next {nom['delta_next']:+.3f}\nsecant error {nom['secant_error']:+.3f}px",transform=ax.transAxes,fontsize=10)
            ax.set_ylim(0,20);ax.grid(color=".92",lw=.5)
            ax=axes[1,col]
            for group,(mode,method,color,marker) in enumerate((("common","persistence_error",".55","s"),("common","secant_error",BLUE,"^"),("independent","persistence_error",".55","s"),("independent","secant_error",BLUE,"^"))):
                rr=[r for r in positions if r["arm"]==arm and r["mode"]==mode and r["valid"]=="True"]
                values=np.array([float(r[method]) for r in rr]);x=group+np.linspace(-.13,.13,len(values))
                ax.scatter(x,values,color=color,marker=marker,s=20 if mode=="common" else 5,alpha=.8 if mode=="common" else .3)
                ax.plot([group,group],[values.min(),values.max()],color=color,lw=1)
            ax.axhline(0,color=".2",lw=.8);ax.set_ylim(-20,20)
            ax.set_xticks(range(4),["P common\nn=9","S common\nn=9","P independent\nn=729","S independent\nn=729"],fontsize=9)
            ax.grid(axis="y",color=".92",lw=.5)
        axes[0,0].set_ylabel("Half-depth width (px)");axes[1,0].set_ylabel("Prediction minus reference (px)")
        axes[0,0].legend(frameon=False,loc="upper right",fontsize=8)
        fig.text(.5,.065,"Grid points are counterfactual sample locations, not independent specimens; vertical segments show tested min/max, not CI.",ha="center",fontsize=9)
        footer(fig);save(fig,"F04_prediction_decomposition")
        dump_new(args.output/"layout_audit.json",audits)
        dump_new(args.output/"source_image_identity.json",sources)
        guide="""# Analysis: S03-E026-D01

## Scientific question
Why is B4 last-query T1 secant error large: optical trend reversal or location/measurement support sensitivity?
Posthoc diagnostic, not independent physical truth. Same frozen half-depth operator throughout.

## Evidence identity
Numerics: SOURCE, E026-R001; renderer R002 from saved CSV/NPZ plus three existing CRC-verified E012 JPEGs.
Existing E020 profiles/strips and E019 FIT translations; CHECK not fitted. T1 has only3/4 usable CHECK anchors,
witha5 first-frame excluded. No new registration, training, source acquisition or E025 rescoring.

## Reading order and guide
1. F04: nominal30/40/50 trajectory plus persistence/secant, and every9 common/729 independent grid errors per arm.
   e_secant=d_history-d_next when clip inactive. Min/max bars are deterministic tested ranges, not CI/probability.
2. F01: top native110x110 gray crops centred at inverse-H original T1, identical gray0..255, no warp/smoothing.
   Source x/y offsets are centred at mapped sample centre. Blue original five-line band; orange existing FIT-shifted centreline.
   Bottom: E020 original-H resampled raw-photo-derived strips, not untouched raw pixels; local n/t coordinates,
   fixed window s±35,t±10 and gray0..255, blue half-depth segment at t0. Location mapping is a proxy, not material truth.
3. F02: all3 median gray and deficit profiles, same axes. Shoulders±45..60 define linear background;
   half-depth crossings mark the selected connected band. Orange sample is previously aligned proxy, not truth.
4. F03: every9 fixed tangential positions, widths then30->40/40->50 changes and last-query signed error.
   Curves connect the existing ordered position grid, not smoothed data or new estimates between grid points.

## Cross-figure interpretation
Use summary.json for exact numbers. Raw-image context and half-depth edge motion can suggest geometric/optical
mechanisms but cannot identify real crack opening. A change after background proxy correction demonstrates
sample-location sensitivity; it does not prove correction accuracy. A stable common-shift reversal need not
survive independently shifted stages. Absence of band-event flags does not prove physical edge continuity.

## Allowed and blocked conclusions
Allowed: reproduce cached half-depth functional, locate left/right crossing contributions, compare existing
sample locations and deterministic finite-grid sensitivity, decompose the already-viewed optical prediction error.
Blocked: physical width decrease/reopening, calibrated uncertainty, real displacement bounded by±2, improved
forecast score, independent validation or using the target to choose a better offset. No old record is changed.

## Storyline impact and next action
Keep original measurement/score. Consult experiment.md and independent review for outcome/one bounded next repair.
layout_audit.json records mechanical QA; actual visual review is recorded separately after opening final PNGs.
""".replace("SOURCE",str(args.source.resolve()))
        (args.output/"README_analysis.md").write_text(guide)
        receipt.update(execution="succeeded",retrieval="verified_local",figure_sets=4,numerical_rerun=False,
                       source_image_count=3,output=str(args.output.resolve()))
    except Exception as error:
        receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(args.output/"runtime_receipt.json",receipt)


if __name__=="__main__":main()
