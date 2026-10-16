#!/usr/bin/env python3
"""E027 near-background correspondence, independent of width values."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from d01_background_anchor_diagnostic import load_inputs,load_gray,local_grid,source_sample
from d01_conditional_interface import dump_new,write_csv

RADII=(7,11)
SEARCH=6


def candidates():
    return [dict(anchor_id=f"N{k+1:02d}",n=n,t=t) for k,(n,t) in
            enumerate((n,t) for n in (-55,-35,35,55) for t in (-36,-18,0,18,36))]


def refined_peak(scores):
    if scores.shape!=(13,13) or not np.isfinite(scores).all():raise ValueError("13x13 finite NCC scores required")
    y,x=np.unravel_index(np.argmax(scores),scores.shape)
    peak=float(scores[y,x]);other=scores.copy()
    other[max(0,y-1):y+2,max(0,x-1):x+2]=-np.inf
    out=dict(available=False,reason="search_boundary",peak=peak,separation=peak-float(np.max(other)),dn=None,dt=None)
    if y in (0,12) or x in (0,12):return out
    def refine(a,b,c):
        den=a-2*b+c
        return float(np.clip(.5*(a-c)/den,-.5,.5)) if den < -1e-12 else 0.
    out.update(available=True,reason="candidate_match",dn=float(x-SEARCH+refine(scores[y,x-1],peak,scores[y,x+1])),
               dt=float(y-SEARCH+refine(scores[y-1,x],peak,scores[y+1,x])))
    return out


def match(template,search):
    template=np.asarray(template,np.float32);search=np.asarray(search,np.float32)
    if template.ndim!=2 or template.shape[0]!=template.shape[1] or template.shape[0] not in (15,23) or search.shape!=tuple(v+12 for v in template.shape):
        raise ValueError("frozen template/search shape mismatch")
    if not np.isfinite(template).all() or not np.isfinite(search).all():raise ValueError("nonfinite match input")
    if float(np.std(template,dtype=np.float64))<=1:
        return dict(available=False,reason="weak_template",peak=None,separation=None,dn=None,dt=None)
    scores=cv2.matchTemplate(np.ascontiguousarray(search),np.ascontiguousarray(template),cv2.TM_CCOEFF_NORMED)
    return refined_peak(scores)


def receipt_base(repo,run_id,output):
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"):raise RuntimeError("clean committed code required")
    return dict(experiment_id="S03-E027-D01",protocol="near-background-v1",run_id=run_id,
                code_commit=git("rev-parse","HEAD"),git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),
                python=sys.executable,command=sys.argv,gpu=None,started_utc=datetime.now(timezone.utc).isoformat(),
                execution="running",retrieval="pending",output=str(output.resolve()))


def prepare(inputs,output):
    repo=Path(__file__).resolve().parents[1];receipt=receipt_base(repo,"S03-E027-D01-R000",output)
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    try:
        g,H,_,_=load_inputs(inputs);tr=g["transects"][0];image=load_gray(g["stages"][0])
        templates={};manifest=[]
        for c in candidates():
            for radius in RADII:
                patch=source_sample(image,local_grid(tr,c["n"],c["t"],radius),H[0],g)
                source_sample(image,local_grid(tr,c["n"],c["t"],radius+SEARCH),H[0],g)
                templates[f"{c['anchor_id']}_r{radius}"]=patch
            manifest.append(dict(c,primary_radius=7,secondary_radius=11,search_radius=6,
                                 origin_only=True,selection="pending_origin_visual_review"))
        # Clean reference frame plus unselected fixed candidate footprints, no widths/future result.
        nn,tt=np.meshgrid(np.arange(-85,86),np.arange(-60,61))
        n=np.asarray(tr["normal"]);t=np.array([-n[1],n[0]])
        grid=np.asarray(tr["center"])+nn[...,None]*n+tt[...,None]*t
        context=source_sample(image,grid,H[0],g)
        np.savez_compressed(output/"templates.npz",context=context,**templates)
        write_csv(output/"candidates.csv",manifest)
        fig,axes=plt.subplots(1,2,figsize=(13,6))
        for ax in axes:
            ax.imshow(context,origin="lower",extent=(-85.5,85.5,-60.5,60.5),cmap="gray",vmin=0,vmax=255,interpolation="nearest")
            ax.set_xlabel("First-frame normal coordinate n (px)");ax.set_ylabel("First-frame tangent coordinate t (px)")
        axes[0].set_title("10 kN first frame: clean context, no width boundary")
        axes[1].set_title("Fixed candidates: solid23x23 template / dashed35x35 search")
        for c in candidates():
            for radius,style in ((11,"-"),(17,"--")):
                axes[1].add_patch(Rectangle((c["n"]-radius-.5,c["t"]-radius-.5),2*radius+1,2*radius+1,
                                          fill=False,edgecolor="#0072B2",lw=.7,ls=style))
            axes[1].text(c["n"],c["t"],c["anchor_id"],fontsize=8,color="#D55E00",ha="center",va="center")
        fig.tight_layout();fig.savefig(output/"origin_context.png",dpi=200);plt.close(fig)
        fig,axes=plt.subplots(4,5,figsize=(12,10))
        for ax,c in zip(axes.flat,candidates()):
            ax.imshow(templates[f"{c['anchor_id']}_r11"],cmap="gray",vmin=0,vmax=255,interpolation="nearest")
            ax.set_title(f"{c['anchor_id']} | n{c['n']},t{c['t']}",fontsize=10);ax.set_xticks([]);ax.set_yticks([])
        fig.suptitle("First-frame maximum templates only; no target images or match outputs")
        fig.tight_layout(rect=(0,0,1,.96));fig.savefig(output/"origin_template_atlas.png",dpi=200);plt.close(fig)
        dump_new(output/"origin_source.json",dict(source=g["stages"][0],geometry_inputs=str(inputs.resolve()),
                                                candidate_count=20,reference_only=True))
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError("60s origin preparation")
        receipt.update(execution="succeeded",retrieval="verified_local",source_images=1,origin_only=True)
    except Exception as error:
        receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(output/"runtime_receipt.json",receipt)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("prepare",),required=True)
    p.add_argument("--inputs",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();prepare(a.inputs,a.output)


if __name__=="__main__":main()
