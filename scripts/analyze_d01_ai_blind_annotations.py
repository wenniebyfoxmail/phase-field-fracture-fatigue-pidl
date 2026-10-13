#!/usr/bin/env python3
"""Reveal frozen AI visual annotations; disagreement is NOT reference accuracy."""
import argparse
import csv
from datetime import datetime, timezone
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
import numpy as np
from PIL import Image


FIELDS=("left_px","right_px","left_min_px","left_max_px","right_min_px","right_max_px")


def dump(path,value): path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def table(path,rows):
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def load_annotations(path):
    with path.open(newline="") as f: rows=list(csv.DictReader(f))
    if [r["task_id"] for r in rows]!=[f"task_{i:03d}" for i in range(1,31)]:
        raise ValueError("30 ordered anonymous task responses required")
    for r in rows:
        if r["quality"] not in ("visible","uncertain","occluded"): raise ValueError("invalid annotation status")
        if r["confidence"] not in ("high","medium","low"): raise ValueError("invalid confidence")
        for field in FIELDS:
            value=None if r[field].strip()=="" else float(r[field])
            if value is not None and (not np.isfinite(value) or not 0<=value<=120 or abs(value*2-round(value*2))>1e-6):
                raise ValueError(f"invalid/overprecise strip coordinate: {r['task_id']} {field}")
            r[field]=value
        points=[r["left_px"],r["right_px"]]
        if r["quality"]=="visible" and (None in points or points[0]>=points[1]):
            raise ValueError(f"visible pair missing or reversed: {r['task_id']}")
        for side in ("left","right"):
            low,point,high=[r[side+suffix] for suffix in ("_min_px","_px","_max_px")]
            if None not in (low,point,high) and not low<=point<=high:
                raise ValueError(f"plausible range excludes point: {r['task_id']}")
        r["width_px"]=points[1]-points[0] if None not in points else None
    return rows


def difference(left,right,reference):
    ref_left,ref_right=reference
    return {"endpoint_disagreement_px":float((abs(left-ref_left)+abs(right-ref_right))/2),
            "width_disagreement_px":float(abs((right-left)-(ref_right-ref_left))),
            "signed_width_difference_px":float((right-left)-(ref_right-ref_left))}


def statistics(values):
    valid=[v for v in values if v is not None and np.isfinite(v)]
    return {"n":len(valid),"mean":float(np.mean(valid)) if valid else None,
            "median":float(np.median(valid)) if valid else None,
            "max":float(np.max(valid)) if valid else None}


def self_test():
    d=difference(10,20,(11,21))
    assert d["endpoint_disagreement_px"]==1 and d["width_disagreement_px"]==0
    d=difference(10,23,(11,21))
    assert d["endpoint_disagreement_px"]==1.5 and d["signed_width_difference_px"]==3
    assert statistics([None,2,4])["mean"]==3
    groups={0:["task_003","task_010"],1:["task_001"]}
    assert min(groups[0])=="task_003"
    assert np.allclose(np.array([60,70])-60,[0,10])
    print("Endpoint-vs-width discrepancy, missing values, ex-ante representative and coordinate conversion: passed")


def analyze(args,receipt,repo):
    # Proof of response freeze is checked BEFORE private key or algorithms read.
    tracked="docs/research/S03/S03-E017-D01/evidence/annotations.csv"
    frozen=subprocess.check_output(["git","show",f"HEAD:{tracked}"],cwd=repo)
    if frozen!=args.annotations.read_bytes(): raise ValueError("annotation file differs from committed frozen response")
    rows=load_annotations(args.annotations)
    for path in (args.annotations,args.exposure_note):
        if not path.is_file(): raise ValueError("missing frozen annotation/exposure record")
    exposure_frozen=subprocess.check_output(["git","show","HEAD:docs/research/S03/S03-E017-D01/evidence/exposure_note.md"],cwd=repo)
    if exposure_frozen!=args.exposure_note.read_bytes(): raise ValueError("exposure note not frozen")
    receipt["annotation_freeze_commit"]=receipt["source_commit"]
    receipt["reveal_started_at_utc"]=datetime.now(timezone.utc).isoformat()
    key=json.loads((args.source/"private_blind_key.json").read_text())
    if len(key)!=30 or {k["task_id"] for k in key}!={r["task_id"] for r in rows}: raise ValueError("reveal key identities mismatch")
    by_id={r["task_id"]:r for r in rows}; grouped={}
    for k in key: grouped.setdefault(k["unique_index"],[]).append(k)
    if len(grouped)!=24 or sorted(map(len,grouped.values()))!=[1]*18+[2]*6: raise ValueError("unexpected unique/repeat structure")
    data={b:np.load(args.source/f"Beam{b}_checks.npz") for b in (4,5,6)}
    unique=[]; duplicate=[]
    for index,items in sorted(grouped.items()):
        item=min(items,key=lambda k:k["task_id"]); a=by_id[item["task_id"]]
        beam=item["beam"]; stage=item["stage_index"]; transect=item["transect_id"]
        candidates={"half_depth":data[beam]["half_depth_edges"][stage,transect-1]+60,
                    "gradient":data[beam]["gradient_edges"][stage,transect-1]+60}
        eligible=a["quality"]=="visible" and all(np.isfinite(v).all() for v in candidates.values())
        record={"unique_index":index,"representative_task":item["task_id"],"beam":beam,
                "stage_index":stage,"nominal_stage_kN":float(data[beam]["loads_kN"][stage]),
                "transect_id":transect,"quality":a["quality"],"confidence":a["confidence"],
                "primary_eligible":bool(eligible),**{f:a[f] for f in FIELDS},"AI_width_px":a["width_px"],"notes":a["notes"]}
        for name,edges in candidates.items():
            record[name+"_left_px"]=float(edges[0]) if np.isfinite(edges[0]) else None
            record[name+"_right_px"]=float(edges[1]) if np.isfinite(edges[1]) else None
            metrics=difference(*edges,(a["left_px"],a["right_px"])) if eligible else {k:None for k in ("endpoint_disagreement_px","width_disagreement_px","signed_width_difference_px")}
            record.update({name+"_"+k:v for k,v in metrics.items()})
            if eligible and None not in [a[f] for f in FIELDS]:
                record[name+"_both_edges_in_plausible_ranges"]=bool(a["left_min_px"]<=edges[0]<=a["left_max_px"] and a["right_min_px"]<=edges[1]<=a["right_max_px"])
            else: record[name+"_both_edges_in_plausible_ranges"]=None
        unique.append(record)
        if len(items)==2:
            first,second=sorted(items,key=lambda k:k["task_id"]); a1=by_id[first["task_id"]]; a2=by_id[second["task_id"]]
            valid=a1["quality"]==a2["quality"]=="visible"
            delta=difference(a2["left_px"],a2["right_px"],(a1["left_px"],a1["right_px"])) if valid else {k:None for k in ("endpoint_disagreement_px","width_disagreement_px","signed_width_difference_px")}
            duplicate.append({"unique_index":index,"first_task":first["task_id"],"second_task":second["task_id"],"beam":beam,
                              "first_quality":a1["quality"],"second_quality":a2["quality"],"quality_agreement":a1["quality"]==a2["quality"],
                              "both_visible":valid,"first_width_px":a1["width_px"],"second_width_px":a2["width_px"],**delta})
    table(args.output/"unique_task_comparison.csv",unique); table(args.output/"duplicate_consistency.csv",duplicate)
    perbeam=[]
    for beam in (4,5,6):
        selected=[r for r in unique if r["beam"]==beam]; valid=[r for r in selected if r["primary_eligible"]]
        record={"beam":beam,"unique_tasks":len(selected),"primary_eligible":len(valid),
                "uncertain":sum(r["quality"]=="uncertain" for r in selected),"occluded":sum(r["quality"]=="occluded" for r in selected)}
        for name in ("half_depth","gradient"):
            for metric in ("endpoint_disagreement_px","width_disagreement_px","signed_width_difference_px"):
                record[name+"_"+metric]=statistics([r[name+"_"+metric] for r in valid])
            flags=[r[name+"_both_edges_in_plausible_ranges"] for r in valid if r[name+"_both_edges_in_plausible_ranges"] is not None]
            record[name+"_both_edges_in_subjective_ranges"]={"n":len(flags),"inside":sum(flags)}
        perbeam.append(record)
    aggregate={name:float(np.mean([r[name+"_endpoint_disagreement_px"]["mean"] for r in perbeam]))
               if all(r[name+"_endpoint_disagreement_px"]["mean"] is not None for r in perbeam) else None
               for name in ("half_depth","gradient")}
    summary={"run_id":args.output.name,"protocol":"ai-visual-development-v1","task_views":30,"unique_tasks":24,
             "primary_eligible_unique_tasks":sum(r["primary_eligible"] for r in unique),
             "annotation_view_quality_counts":{q:sum(r["quality"]==q for r in rows) for q in ("visible","uncertain","occluded")},
             "per_beam":perbeam,"equal_beam_mean_endpoint_disagreement_px":aggregate,
             "duplicates":{"pairs":6,"both_visible":sum(r["both_visible"] for r in duplicate),
                           "quality_agreement_pairs":sum(r["quality_agreement"] for r in duplicate),
                           "endpoint_disagreement_px":statistics([r["endpoint_disagreement_px"] for r in duplicate]),
                           "width_disagreement_px":statistics([r["width_disagreement_px"] for r in duplicate])},
             "reference_status":"AI_VISUAL_ASSISTANCE_ONLY_HUMAN_REFERENCE_PENDING","human_annotations_included":False,
             "physical_width_validated":False,"forecast_rescored":False,"formal_review":"pending"}
    dump(args.output/"summary.json",summary); figures(unique,duplicate,args.source,args.output)
    receipt.update(execution="succeeded",retrieval="verified_local",ended_at_utc=datetime.now(timezone.utc).isoformat())
    print(json.dumps(summary,indent=2))


def figures(unique,duplicate,source,output):
    colors={"half_depth":"#0072B2","gradient":"#D55E00"}
    fig,axes=plt.subplots(2,3,figsize=(14,7),constrained_layout=True)
    for col,beam in enumerate((4,5,6)):
        items=sorted([r for r in unique if r["beam"]==beam],key=lambda r:(r["stage_index"],r["transect_id"]))
        x=np.arange(len(items)); labels=[f"{'first' if r['stage_index']==0 else 'last'}\nT{r['transect_id']}" for r in items]
        for row,metric in enumerate(("endpoint_disagreement_px","width_disagreement_px")):
            ax=axes[row,col]
            for name in colors:
                values=[r[name+"_"+metric] if r[name+"_"+metric] is not None else np.nan for r in items]
                ax.plot(x,values,"o-",color=colors[name],lw=1.2,label=name.replace("_"," "))
            for i,r in enumerate(items):
                if not r["primary_eligible"]: ax.text(i,0,"?",color=".5",ha="center",va="bottom")
            ax.set(xticks=x,xticklabels=labels,xlabel="All frozen unique image tasks",ylabel="Mean endpoint difference (px)" if row==0 else "Absolute width difference (px)",ylim=(0,None))
            ax.tick_params(axis="x",labelsize=7); ax.legend(fontsize=8)
            if row==0: ax.set_title(f"Beam {beam} | visible joint support {sum(r['primary_eligible'] for r in items)}/8")
    for row in range(2):
        ymax=max(ax.get_ylim()[1] for ax in axes[row])
        for ax in axes[row]: ax.set_ylim(0,ymax)
    fig.suptitle(f"{output.name} | algorithms versus BLINDED AI visual estimates; disagreement, NOT accuracy\nCentral-row apparent edges versus stored five-line-profile definitions; shared scales, all unique tasks")
    fig.savefig(output/"algorithm_ai_disagreement.png",dpi=165); plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4),constrained_layout=True)
    for metric,color,label in (("endpoint_disagreement_px","#0072B2","mean left/right difference"),("width_disagreement_px","#D55E00","width difference")):
        ax.plot(np.arange(6),[r[metric] if r[metric] is not None else np.nan for r in duplicate],"o-",color=color,label=label,lw=1.3)
    labels=[f"{r['first_task']}\n{r['second_task']}" for r in duplicate]
    for i,r in enumerate(duplicate):
        if not r["both_visible"]: ax.text(i,0,"not two visible labels",ha="center",fontsize=7)
    ax.set(xticks=np.arange(6),xticklabels=labels,ylabel="Absolute AI repeat-reading difference (px)",ylim=(0,None))
    ax.tick_params(axis="x",labelsize=8); ax.legend(fontsize=8)
    ax.set_title(f"{output.name} | ALL six hidden-repeat pairs, one AI annotator/context\nPossible recognition/recall and 0.5px quantization; NOT independent metrology repeatability")
    fig.savefig(output/"ai_duplicate_consistency.png",dpi=165); plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    fig.set_constrained_layout_pads(hspace=.1,wspace=.04)
    for col,beam in enumerate((4,5,6)):
        cases=sorted([r for r in unique if r["beam"]==beam and r["transect_id"]==6],key=lambda r:r["stage_index"])
        if len(cases)!=2: raise ValueError("frozen six-example rule unavailable")
        for row,r in enumerate(cases):
            with Image.open(source/"blind_packet"/(r["representative_task"]+".png")) as im: image=np.array(im)
            ax=axes[row,col]; ax.imshow(image,cmap="gray",vmin=0,vmax=255,extent=(-.5,120.5,48.5,-.5),interpolation="nearest")
            for name,color in colors.items():
                for side in ("left","right"):
                    x=r[name+"_"+side+"_px"]
                    if x is not None: ax.plot([x,x],[18,30],color=color,lw=1.5,ls="--" if name=="gradient" else "-")
            for side in ("left","right"):
                point=r[side+"_px"]; low=r[side+"_min_px"]; high=r[side+"_max_px"]
                if low is not None and high is not None: ax.axvspan(low,high,color="#CC79A7",alpha=.18)
                if point is not None: ax.plot(point,24,"o",color="#CC79A7",ms=5)
            ax.set(title=f"Beam {beam} | {r['nominal_stage_kN']:.0f} kN | T6\nAI: {r['quality']} / {r['confidence']}",xlabel="Strip pixel-center x",ylabel="Row y",xlim=(15,105))
    fig.suptitle(f"{output.name} | fixed ID 6 first/last of every beam, NO selected best examples\nPurple=AI point/plausible range; blue=half-depth; orange=gradient. AI-assisted, NOT human/physical truth")
    fig.savefig(output/"ai_algorithm_edge_overlay.png",dpi=165); plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","annotations","exposure-note","output"): p.add_argument("--"+name,type=Path)
    p.add_argument("--self-test",action="store_true"); args=p.parse_args()
    if args.self_test: self_test(); return
    if any(getattr(args,k.replace("-","_")) is None for k in ("source","annotations","exposure-note","output")): p.error("all paths required")
    repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("freeze annotation/code before reveal")
    if args.output.exists(): raise FileExistsError("fresh output required")
    args.output.mkdir(parents=True); started=time.monotonic()
    receipt={"experiment_id":"S03-E017-D01","run_id":args.output.name,"protocol":"ai-visual-development-v1",
             "producer":"Mac-PIDL CPU analysis","hostname":socket.gethostname(),"pid":os.getpid(),
             "source_commit":git("rev-parse","HEAD"),"git_dirty":False,"command":sys.argv,"python":sys.executable,
             "started_at_utc":datetime.now(timezone.utc).isoformat(),"execution":"running","retrieval":"pending",
             "formal_review":"pending_development_only","gpu":None}
    dump(args.output/"run_receipt.json",receipt)
    try: analyze(args,receipt,repo)
    except Exception as error:
        receipt.update(execution="failed",retrieval="partial_local",error=f"{type(error).__name__}: {error}")
        dump(args.output/"run_receipt.json",receipt); raise
    receipt["runtime_seconds"]=time.monotonic()-started; dump(args.output/"run_receipt.json",receipt)


if __name__=="__main__": main()
