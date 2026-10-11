#!/usr/bin/env python3
"""S03-E011 development-only next-loading-stage image-observable baselines."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from d01_directional_scale_repeatability import crc32_file
from d01_local_registration_holdout import evaluate_registration, transformed_corners
from d01_multiview_repeatability import load_gray, register, ridge_response
from d01_remote_manifest_audit import extract_entry

BOXES={4:((3300,1200,4450,2750),(1800,1400,2400,2300)),
       5:((3100,1350,4650,2750),(1500,1400,2300,2400)),
       6:((2200,1350,3900,2900),(1000,1400,1700,2300))}
ARMS=("persistence","secant","conservative_secant")


def predict(prefix, load_prefix, next_load, arm):
    """The API never accepts future observations or fitted parameters."""
    if len(prefix)!=len(load_prefix) or len(prefix)<2:
        raise ValueError("two aligned historical observations required")
    dl=float(load_prefix[-1]-load_prefix[-2])
    if dl<=0 or next_load<=load_prefix[-1]:
        raise ValueError("loading labels must strictly increase")
    weight={"persistence":0.,"secant":1.,"conservative_secant":.5}[arm]
    return np.clip(prefix[-1]+weight*(prefix[-1]-prefix[-2])*(next_load-load_prefix[-1])/dl,0,1)


def grid_means(crop):
    ys=np.linspace(0,crop.shape[0],17).astype(int)
    xs=np.linspace(0,crop.shape[1],17).astype(int)
    return np.array([[crop[y1:y2,x1:x2].mean() for x1,x2 in zip(xs[:-1],xs[1:])]
                     for y1,y2 in zip(ys[:-1],ys[1:])],dtype=float)


def bounds(box,scale):
    x0,y0,x1,y1=np.rint(np.array(box)*scale).astype(int)
    return int(x0),int(y0),int(x1),int(y1)


def crop_box(image,box):
    x0,y0,x1,y1=box
    result=image[y0:y1,x0:x1]
    if result.size==0: raise ValueError("empty observation/control box")
    return result


def dump(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def write_csv(path,rows):
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def self_test():
    history=np.array([np.zeros((2,2))+.1,np.zeros((2,2))+.3])
    loads=np.array([10.,30.])
    assert np.allclose(predict(history,loads,40,"secant"),.4)
    assert np.allclose(predict(history,loads,40,"conservative_secant"),.35)
    assert np.allclose(predict(history,loads,40,"persistence"),.3)
    sequence=np.concatenate([history,np.zeros((1,2,2))+.9])
    first=predict(sequence[:2],loads,40,"secant")
    sequence[2]=0
    assert np.array_equal(first,predict(sequence[:2],loads,40,"secant"))
    assert np.allclose(grid_means(np.full((32,48),.2)),.2)
    print("unequal-load, clipping-range, prefix-only and grid checks passed")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test: self_test(); return
    if args.archive is None or args.output is None: parser.error("archive/output required")
    repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("commit source before execution")
    if args.output.exists(): raise FileExistsError("fresh output required")
    args.output.mkdir(parents=True)
    receipt={"experiment_id":"S03-E011","run_id":"S03-E011-R001","protocol":"development-v1",
             "role":"exploratory_image_observable_forecast","producer":"Mac-PIDL",
             "hostname":socket.gethostname(),"pid":os.getpid(),"commit":git("rev-parse","HEAD"),
             "git_dirty":False,"python":sys.executable,"command":sys.argv,"gpu":None,
             "started_at_utc":datetime.now(timezone.utc).isoformat(),"execution":"running",
             "retrieval":"pending","independent_code_review":"not_formally_reviewed_development"}
    dump(args.output/"run_receipt.json",receipt)
    manifest=json.loads((args.archive/"S03-E004/analysis/remote_zip_manifest.json").read_text())
    with (args.archive/"S03-E004/analysis/load_stop_mapping.csv").open() as f:
        mapping=list(csv.DictReader(f))
    groups={}; excluded=[]
    for beam in (4,5,6):
        selected=[]
        for row in mapping:
            if row["beam_id"]!=f"Beam {beam}": continue
            if row["status"]!="nominal_time_join_available" or not row["load_step_label"].isdigit():
                excluded.append({"beam":beam,"photo_time_s":row["photo_time_s"],"reason":"non-numeric_final_stage_outside_original_machine_coverage"})
                continue
            time=int(row["photo_time_s"])
            relative=f"Beam {beam}/G{beam}-IB-Fixed/G{beam}-IB_t={time}.JPG"
            entries=[e for e in manifest["entries"] if e["path"].endswith("/"+relative)]
            if len(entries)!=1: raise ValueError(f"non-unique stage source: {relative}")
            selected.append({"beam":beam,"nominal_load_kN":int(row["load_step_label"]),
                             "filename_time_s":time,"saved_as":relative,"entry":entries[0]})
        selected.sort(key=lambda r:r["filename_time_s"])
        if np.any(np.diff([r["nominal_load_kN"] for r in selected])<=0):
            raise ValueError("stage ordering conflict")
        groups[beam]=selected
    dump(args.output/"selected_sequences_before_pixel_access.json",{"groups":groups,"excluded":excluded,
         "exact_camera_logger_synchronization_claimed":False})
    acquisitions=[]
    for states in groups.values():
        for item in states:
            cached=args.archive/"S03-E006/analysis/raw_images"/item["saved_as"]
            target=args.output/"raw_images"/item["saved_as"]
            if cached.is_file():
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(cached,target)
                source="reused_S03-E006"
            else:
                extract_entry(manifest["source_url"],item["entry"],args.output/"raw_images")
                source="remote_range_extract"
            if target.stat().st_size!=item["entry"]["uncompressed_bytes"] or crc32_file(target)!=item["entry"]["crc32"]:
                raise ValueError(f"source size/CRC mismatch: {target}")
            _,_,native=load_gray(target)
            acquisitions.append({"beam":item["beam"],"load_kN":item["nominal_load_kN"],
                                 "filename_time_s":item["filename_time_s"],"source":source,
                                 "saved_as":item["saved_as"],"bytes":target.stat().st_size,
                                 "crc32":item["entry"]["crc32"],"native_shape":list(native),"verified":True})
            dump(args.output/"acquisition_receipt.json",acquisitions)
    image_rows=[]; forecast_rows=[]; results=[]
    roi_fig,roi_axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
    for col,(beam,states) in enumerate(groups.items()):
        origin,scale,native=load_gray(args.output/"raw_images"/states[0]["saved_as"])
        if native!=(3744,5616): raise ValueError("unexpected fixed-image geometry")
        observation,control=[bounds(box,scale) for box in BOXES[beam]]
        control_values=crop_box(origin,control)
        med_ref=float(np.median(control_values)); iqr_ref=float(np.quantile(control_values,.75)-np.quantile(control_values,.25))
        if iqr_ref<=0: raise ValueError("control reference has no intensity support")
        roi_axes[col].imshow(origin,cmap="gray",vmin=0,vmax=255)
        for box,color,label in ((observation,"#D55E00","crack-neighbourhood ROI"),(control,"#0072B2","photometric control")):
            x0,y0,x1,y1=box; roi_axes[col].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,lw=2,edgecolor=color,label=label))
        roi_axes[col].set_title(f"Beam {beam} | first 10 kN state only")
        roi_axes[col].legend(fontsize=8,loc="lower left")
        fields=[]; photos=[]; jitters=[]; matrices=[]; raw_fields=[]
        for j,state in enumerate(states):
            im,_,_=load_gray(args.output/"raw_images"/state["saved_as"])
            if j==0:
                aligned=origin; mask=np.ones(origin.shape,bool); homography=np.eye(3)
                inliers=0; reprojection=0.
            else:
                reg=register(im,origin,scale)
                corners=transformed_corners(im.shape,reg.homography) if reg.homography is not None else None
                valid,reason=evaluate_registration(reg,"fixed",corners)
                if not valid: raise ValueError(f"registration failed {state['saved_as']}: {reason}")
                aligned,mask=warp_image(im,reg.homography,origin.shape)
                homography=reg.homography; inliers=reg.inliers; reprojection=reg.median_reprojection_native_px
            if min(float(crop_box(mask,b).mean()) for b in (observation,control))<.99:
                raise ValueError("origin-frozen ROI support below .99")
            values=crop_box(aligned,control)
            med=float(np.median(values)); iqr=float(np.quantile(values,.75)-np.quantile(values,.25))
            if iqr<=0: raise ValueError("invalid control-patch contrast")
            gain=iqr_ref/iqr; offset=med_ref-gain*med
            normalized=np.clip(aligned.astype(float)*gain+offset,0,255).astype(np.uint8)
            response=ridge_response(normalized)
            field=grid_means(crop_box(response,observation))
            raw_field=grid_means(crop_box(ridge_response(aligned),observation))
            jitter=[]
            for axis in (0,1):
                for shift in (-1,1):
                    perturbed=np.roll(response,shift,axis=axis)
                    jitter.append(float(np.abs(grid_means(crop_box(perturbed,observation))-field).mean()))
            fields.append(field); raw_fields.append(raw_field); photos.append(crop_box(normalized,observation))
            jitters.append(float(np.mean(jitter))); matrices.append(homography)
            image_rows.append({"beam":beam,"nominal_load_kN":state["nominal_load_kN"],
                               "filename_time_s":state["filename_time_s"],"source_path":state["saved_as"],
                               "inliers":inliers,"median_reprojection_native_px":reprojection,
                               "photometric_gain":gain,"photometric_offset":offset,
                               "mean_dark_ridge_response":float(field.mean()),
                               "raw_mean_dark_ridge_response":float(raw_field.mean()),
                               "one_working_pixel_shift_sensitivity":jitters[-1]})
        fields=np.stack(fields); loads=np.array([s["nominal_load_kN"] for s in states],dtype=float)
        predictions={arm:[] for arm in ARMS}
        for current in range(1,len(states)-1):
            for arm in ARMS:
                prediction=predict(fields[:current+1],loads[:current+1],loads[current+1],arm)
                predictions[arm].append(prediction)
                forecast_rows.append({"beam":beam,"origin_nominal_kN":loads[current],
                                      "target_nominal_kN":loads[current+1],"arm":arm,
                                      "past_observations":current+1,"target_source":states[current+1]["saved_as"],
                                      "field_MAE":float(np.abs(prediction-fields[current+1]).mean()),
                                      "target_mean":float(fields[current+1].mean()),
                                      "predicted_mean":float(prediction.mean()),
                                      "target_shift_sensitivity":jitters[current+1]})
        predictions={k:np.stack(v) for k,v in predictions.items()}
        np.savez_compressed(args.output/f"Beam{beam}_stage_fields.npz",fields=fields,raw_fields=np.stack(raw_fields),
                            gray_ROIs=np.stack(photos),nominal_loads_kN=loads,homographies=np.stack(matrices),
                            **{k+"_predictions":v for k,v in predictions.items()})
        results.append({"beam":beam,"states":states,"fields":fields,"loads":loads,"photos":photos,"predictions":predictions})
    roi_fig.suptitle("S03-E011-R001 | ROIs fixed from first stage, not selected using future outcomes")
    roi_fig.savefig(args.output/"origin_only_rois.png",dpi=160); plt.close(roi_fig)
    write_csv(args.output/"stage_observables.csv",image_rows)
    write_csv(args.output/"forecast_metrics.csv",forecast_rows)
    per_beam=[]
    for beam in groups:
        losses={arm:float(np.mean([r["field_MAE"] for r in forecast_rows if r["beam"]==beam and r["arm"]==arm])) for arm in ARMS}
        per_beam.append({"beam":beam,"states":len(groups[beam]),"forecast_pairs":len(groups[beam])-2,**losses})
    aggregate={arm:float(np.mean([r[arm] for r in per_beam])) for arm in ARMS}
    summary={"states":sum(len(x) for x in groups.values()),"forecast_pairs":sum(len(x)-2 for x in groups.values()),
             "independent_beams":3,"per_beam":per_beam,"equal_beam_mean_MAE":aggregate,
             "relative_change_vs_persistence":{a:aggregate[a]/aggregate["persistence"]-1 for a in ARMS[1:]},
             "scientific_verdict":"EXPLORATORY_OBSERVABLE_FORECAST_ONLY","physical_crack_geometry_validated":False,
             "autonomous_rollout":False,"next_actual_force_used_as_input":False,"formal_review":"pending"}
    dump(args.output/"summary.json",summary)
    make_figures(results,per_beam,args.output)
    receipt.update(execution="succeeded",retrieval="verified_local",ended_at_utc=datetime.now(timezone.utc).isoformat())
    dump(args.output/"run_receipt.json",receipt); print(json.dumps(summary,indent=2))


def make_figures(results,per_beam,output):
    fig,axes=plt.subplots(3,6,figsize=(16,10),constrained_layout=True)
    for row,result in enumerate(results):
        for col,ax in enumerate(axes[row]):
            if col>=len(result["states"]): ax.axis("off"); continue
            ax.imshow(result["photos"][col],cmap="gray",vmin=0,vmax=255)
            ax.set_title(f"Beam {result['beam']} | {result['loads'][col]:.0f} kN\nt={result['states'][col]['filename_time_s']} filename",fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("S03-E011-R001 | all 14 ordered fixed-camera ROI observations | control-normalized gray, development")
    fig.savefig(output/"ordered_stage_images.png",dpi=180); plt.close(fig)
    colors={"persistence":"#555555","secant":"#0072B2","conservative_secant":"#D55E00"}
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    for ax,result in zip(axes,results):
        ax.plot(result["loads"],result["fields"].mean(axis=(1,2)),"ko-",label="observed",lw=1.5)
        for arm in ARMS:
            ax.plot(result["loads"][2:],result["predictions"][arm].mean(axis=(1,2)),"x--",color=colors[arm],label=arm,lw=1)
        ax.set(title=f"Beam {result['beam']}",xlabel="Nominal scheduled stage (kN)",ylabel="Mean ROI dark-ridge response")
        ax.legend(fontsize=7)
    fig.suptitle("One-step forecasts use observed history; NOT autonomous rollout or a physical crack-width target")
    fig.savefig(output/"stage_forecast_trajectories.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4),constrained_layout=True)
    x=np.arange(3)
    for i,arm in enumerate(ARMS):
        ax.bar(x+(i-1)*.23,[r[arm] for r in per_beam],width=.22,label=arm,color=colors[arm])
    ax.set(xticks=x,xticklabels=["Beam 4 (2 pairs)","Beam 5 (4 pairs)","Beam 6 (2 pairs)"],ylabel="Mean next-stage 16x16 response-field MAE")
    ax.legend(fontsize=8); ax.set_title("S03-E011-R001 | independent beam variation | exploratory baselines")
    fig.savefig(output/"forecast_comparison.png",dpi=180); plt.close(fig)
    vmax=max(float(r["fields"].max()) for r in results)
    fig,axes=plt.subplots(3,5,figsize=(15,9),constrained_layout=True)
    mappable=None
    for row,result in enumerate(results):
        loads=result["loads"]
        axes[row,0].imshow(result["photos"][-1],cmap="gray",vmin=0,vmax=255)
        axes[row,0].set_title(f"Beam {result['beam']} actual next image\n{loads[-2]:.0f} -> {loads[-1]:.0f} kN",fontsize=9)
        arrays=[result["fields"][-1],*[result["predictions"][a][-1] for a in ARMS]]
        titles=["Observed response",*ARMS]
        for col,(field,title) in enumerate(zip(arrays,titles),start=1):
            mappable=axes[row,col].imshow(field,cmap="magma",vmin=0,vmax=vmax)
            error=float(np.abs(field-result["fields"][-1]).mean())
            axes[row,col].set_title(f"{title}\nMAE={error:.5f}" if col>1 else title,fontsize=9)
        for ax in axes[row]: ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(mappable,ax=list(axes[:,1:].ravel()),fraction=.015,pad=.01,label="Normalized dark-ridge response; shared limits")
    fig.suptitle("Last included next-stage target of every beam | source ROI and forecast fields | no crack-mask truth")
    fig.savefig(output/"next_stage_forecast_fields.png",dpi=180); plt.close(fig)


if __name__=="__main__": main()
