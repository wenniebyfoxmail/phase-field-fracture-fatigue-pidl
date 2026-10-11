#!/usr/bin/env python3
"""Existing-image resampling null and preregistered sigma=1 observation repair."""
import argparse
import csv
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from d01_multiview_repeatability import load_gray,ridge_response,warp_image
from d01_stage_forecast_diagnostic import BOXES,ARMS,bounds,crop_box,grid_means,predict,dump,write_csv


def response_field(image,box,smooth):
    if smooth: image=cv2.GaussianBlur(image,(0,0),1.0)
    return grid_means(crop_box(ridge_response(image),box))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("commit before execution")
    if args.output.exists(): raise FileExistsError("fresh run output required")
    args.output.mkdir(parents=True)
    receipt={"experiment_id":"S03-E013-D01","run_id":"S03-E013-D01-R001",
             "role":"C0_development_counterfactual_and_observable_repair","commit":git("rev-parse","HEAD"),
             "git_dirty":False,"producer":"Mac-PIDL","hostname":socket.gethostname(),"pid":os.getpid(),
             "command":sys.argv,"python":sys.executable,"gpu":None,"source":str(args.source),
             "started_at_utc":datetime.now(timezone.utc).isoformat(),"execution":"running"}
    dump(args.output/"run_receipt.json",receipt)
    with (args.source/"stage_observables.csv").open() as f: observations=list(csv.DictReader(f))
    nulls=[]; scores=[]; per_beam=[]
    translation=np.array([[1.,0.,.5],[0.,1.,.5],[0.,0.,1.]])
    for beam in (4,5,6):
        with np.load(args.source/f"Beam{beam}_stage_fields.npz") as f:
            transforms=f["homographies"].copy(); loads=f["nominal_loads_kN"].copy()
        rows=[r for r in observations if int(r["beam"])==beam]
        origin,scale,_=load_gray(args.source/"raw_images"/rows[0]["source_path"])
        box=bounds(BOXES[beam][0],scale)
        translated,_=warp_image(origin,translation,origin.shape)
        returned,_=warp_image(translated,np.linalg.inv(translation),origin.shape)
        null_fields={}
        for smooth in (False,True):
            before=response_field(origin,box,smooth)
            after=response_field(returned,box,smooth)
            null_fields[str(smooth)]=(before,after)
            nulls.append({"beam":beam,"uniform_sigma_working_px":1. if smooth else 0.,
                          "null_field_MAE":float(np.abs(after-before).mean()),
                          "original_mean":float(before.mean()),"resampled_mean":float(after.mean())})
        fields=[]
        for j,row in enumerate(rows):
            image,_,_=load_gray(args.source/"raw_images"/row["source_path"])
            aligned,_=warp_image(image,transforms[j],origin.shape) if j else (image,None)
            normalized=np.clip(aligned.astype(float)*float(row["photometric_gain"])+float(row["photometric_offset"]),0,255).astype(np.uint8)
            fields.append(response_field(normalized,box,True))
        fields=np.stack(fields)
        predictions={arm:[] for arm in ARMS}
        for current in range(1,len(fields)-1):
            for arm in ARMS:
                pred=predict(fields[:current+1],loads[:current+1],loads[current+1],arm)
                predictions[arm].append(pred)
                scores.append({"beam":beam,"origin_nominal_kN":loads[current],"target_nominal_kN":loads[current+1],
                               "arm":arm,"field_MAE":float(np.abs(pred-fields[current+1]).mean())})
        losses={a:float(np.mean([r["field_MAE"] for r in scores if r["beam"]==beam and r["arm"]==a])) for a in ARMS}
        per_beam.append({"beam":beam,**losses})
        np.savez_compressed(args.output/f"Beam{beam}_smoothed_fields.npz",fields=fields,nominal_loads_kN=loads,
                            **{a+"_predictions":np.stack(v) for a,v in predictions.items()},
                            raw_null_original=null_fields["False"][0],raw_null_resampled=null_fields["False"][1],
                            smooth_null_original=null_fields["True"][0],smooth_null_resampled=null_fields["True"][1])
    write_csv(args.output/"resampling_null.csv",nulls)
    write_csv(args.output/"smoothed_forecast_metrics.csv",scores)
    before=float(np.mean([r["null_field_MAE"] for r in nulls if r["uniform_sigma_working_px"]==0]))
    after=float(np.mean([r["null_field_MAE"] for r in nulls if r["uniform_sigma_working_px"]==1]))
    aggregate={a:float(np.mean([r[a] for r in per_beam])) for a in ARMS}
    summary={"equal_beam_mean_null_MAE_raw":before,"equal_beam_mean_null_MAE_smooth":after,
             "null_reduction_fraction":1-after/before,"smoothed_target_per_beam":per_beam,
             "smoothed_target_equal_beam_MAE":aggregate,
             "smoothed_relative_change_vs_persistence":{a:aggregate[a]/aggregate["persistence"]-1 for a in ARMS[1:]},
             "physical_scene_changed_in_null":False,"registration_refit":False,
             "scientific_verdict":"DEVELOPMENT_COUNTERFACTUAL_ONLY","physical_crack_geometry_validated":False}
    dump(args.output/"summary.json",summary)
    fig,axes=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
    x=np.arange(3)
    for shift,sigma,color in ((-.18,0,"#0072B2"),(.18,1,"#D55E00")):
        axes[0].bar(x+shift,[r["null_field_MAE"] for r in nulls if r["uniform_sigma_working_px"]==sigma],width=.34,
                    color=color,label=f"sigma={sigma} working px")
    axes[0].set(xticks=x,xticklabels=["Beam 4","Beam 5","Beam 6"],ylabel="Static-scene resampling discrepancy (MAE)",title="Same image, reversible half-pixel translation")
    axes[0].legend(fontsize=8)
    for i,(arm,color) in enumerate(zip(ARMS,("#555555","#0072B2","#D55E00"))):
        axes[1].bar(x+(i-1)*.23,[r[arm] for r in per_beam],width=.22,label=arm,color=color)
    axes[1].set(xticks=x,xticklabels=["Beam 4","Beam 5","Beam 6"],ylabel="Smoothed next-stage response-field MAE",title="Matched comparisons on the new smoothed target")
    axes[1].legend(fontsize=8)
    fig.suptitle("S03-E013-D01-R001 | one fixed prefilter repair | development, no physical crack truth")
    fig.savefig(args.output/"resampling_null_and_repair.png",dpi=180); plt.close(fig)
    receipt.update(execution="succeeded",retrieval="verified_local",ended_at_utc=datetime.now(timezone.utc).isoformat())
    dump(args.output/"run_receipt.json",receipt); print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
