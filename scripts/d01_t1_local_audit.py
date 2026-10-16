#!/usr/bin/env python3
"""E026: existing T1 cache only; optical trend and position counterfactuals."""
import argparse
import csv
from datetime import datetime, timezone
import itertools
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
from independent_d01_halfdepth import measure
from d01_tangent_width_response import halfdepth_components, classify_pair
from d01_conditional_interface import dump_new, write_csv

ARMS=("original_H","background_aligned")
STAGES=(1,2,3)
LOADS=(30.,40.,50.)
T=np.arange(-2.,2.01,.5)
S=np.arange(-60.,60.01,.25)
SOURCE_COMMIT="84c34422d52c7ff3f062add41a7bfe7537935861"


def read_csv(path):
    with Path(path).open(newline="") as f:return list(csv.DictReader(f))


def decompose(widths):
    w=np.asarray(widths,dtype=float)
    if w.shape!=(3,) or not np.isfinite(w).all():raise ValueError("three finite widths required")
    a,b,c=map(float,w);raw=2*b-a;pred=float(np.clip(raw,0,120))
    dh=b-a;dn=c-b
    return dict(w30=a,w40=b,w50=c,delta_history=dh,delta_next=dn,
                persistence=b,secant_raw=raw,secant=pred,clip_active=pred!=raw,
                persistence_error=b-c,secant_error=pred-c,
                raw_error_identity=dh-dn,reversal_down_up=dh<0 and dn>0)


def position_cases(widths,valid,arm):
    w=np.asarray(widths,float);v=np.asarray(valid,bool)
    if w.shape!=(3,9) or v.shape!=w.shape:raise ValueError("3x9 position grid required")
    if not np.isfinite(w[v]).all():raise ValueError("nonfinite valid profile")
    output=[]
    for mode,indices in (("common",[(k,k,k) for k in range(9)]),
                         ("independent",itertools.product(range(9),repeat=3))):
        for a,b,c in indices:
            good=bool(v[0,a] and v[1,b] and v[2,c])
            r=dict(arm=arm,mode=mode,t30=float(T[a]),t40=float(T[b]),t50=float(T[c]),valid=good)
            r.update(decompose([w[0,a],w[1,b],w[2,c]]) if good else
                     {key:None for key in decompose([1,1,1])})
            output.append(r)
    return output


def summarize(rows):
    summary=[]
    for arm in ARMS:
        d=dict(arm=arm)
        nominal=next(r for r in rows if r["arm"]==arm and r["mode"]=="common" and r["t30"]==0)
        d["nominal"]={k:nominal[k] for k in decompose([1,1,1])}
        for mode in ("common","independent"):
            rr=[r for r in rows if r["arm"]==arm and r["mode"]==mode]
            good=[r for r in rr if r["valid"]]
            stats=dict(total=len(rr),valid=len(good),reversal_down_up=sum(r["reversal_down_up"] for r in good),
                       clip_active=sum(r["clip_active"] for r in good))
            for key in ("delta_history","delta_next","secant_error","persistence_error"):
                stats[key+"_min"]=min((r[key] for r in good),default=None)
                stats[key+"_max"]=max((r[key] for r in good),default=None)
            d[mode]=stats
        summary.append(d)
    return dict(by_arm=summary,domain="controlled-experiment",role="posthoc_viewed_development",
                unit="native_first_frame_px",physical_turn_identified=False,
                actual_relative_position_within_grid_proven=False)


def extract(cache,records):
    selected={};rows=[];profile_arrays={};stage_pairs=[]
    for arm in ARMS:
        for j,load in zip(STAGES,LOADS):
            key=f"st{j}_tr1_{arm}"
            profiles=np.asarray(cache[key+"_profiles"])[16:25]
            deficits=np.asarray(cache[key+"_deficits"])[16:25]
            strip=np.asarray(cache[key+"_strip"])
            if profiles.shape!=(9,481) or deficits.shape!=profiles.shape or strip.shape!=(57,121):
                raise ValueError("cache shape/offset convention mismatch")
            if not all(np.isfinite(a).all() for a in (profiles,deficits,strip)):raise ValueError("nonfinite cache")
            for k,t in enumerate(T):
                identity=(j,arm,float(t))
                if identity not in records:raise ValueError("selected cached row missing")
                ref=records[identity]
                if ref["valid"] not in ("True","False"):raise ValueError("malformed validity")
                if int(ref["t_index"])!=k+16 or float(ref["load_kN"])!=load:raise ValueError("row convention mismatch")
                r=measure(S,profiles[k]);r["components"]=halfdepth_components(S,r)
                if r["valid"]!=(ref["valid"].lower()=="true"):raise ValueError("validity replay mismatch")
                if np.max(np.abs(r["deficit"]-deficits[k]))>1e-8:raise ValueError("deficit cache mismatch")
                for a,b in (("width_px","width_px"),("left_px","left_px"),("right_px","right_px"),("peak_px","peak_px"),("depth","depth")):
                    if r["valid"] and (not np.isfinite(float(ref[b])) or abs(r[a]-float(ref[b]))>1e-8):
                        raise ValueError(f"cached measurement mismatch:{a}")
                if r["components"]!=json.loads(ref["components_json"]):raise ValueError("component cache mismatch")
                selected[identity]=r
                rows.append(dict(stage_index=j,load_kN=load,arm=arm,tangent_px=float(t),
                    valid=r["valid"],reason=r["reason"],width_px=r["width_px"],left_px=r["left_px"],right_px=r["right_px"],
                    peak_px=r["peak_px"],depth=r["depth"],noise=r["noise"],half_level=r["depth"]/2,
                    component_count=len(r["components"]),components_json=json.dumps(r["components"])))
            profile_arrays[key+"_profile"]=profiles[4]
            profile_arrays[key+"_background"]=selected[(j,arm,0.)]["background"]
            profile_arrays[key+"_deficit"]=deficits[4]
            profile_arrays[key+"_strip"]=strip
        for j in (1,2):
            a,b=selected[(j,arm,0.)],selected[(j+1,arm,0.)]
            r=classify_pair(a,b)
            stage_pairs.append(dict(arm=arm,stage_a=j,stage_b=j+1,
                left_shift=b["left_px"]-a["left_px"],right_shift=b["right_px"]-a["right_px"],
                half_level_change=(b["depth"]-a["depth"])/2,**r))
    positions=[]
    for arm in ARMS:
        widths=[[selected[(j,arm,float(t))]["width_px"] for t in T] for j in STAGES]
        valid=[[selected[(j,arm,float(t))]["valid"] for t in T] for j in STAGES]
        positions.extend(position_cases(widths,valid,arm))
    return rows,stage_pairs,positions,profile_arrays


def validate_background(translations,checks):
    if len(translations)!=3 or {(int(r["stage_index"]),int(r["transect_id"])) for r in translations}!={(j,1) for j in STAGES}:
        raise ValueError("translation identity mismatch")
    if len(checks)!=12 or {(int(r["stage_index"]),int(r["transect_id"]),int(r["anchor_id"])) for r in checks}!={(j,1,k) for j in STAGES for k in range(4,8)}:
        raise ValueError("CHECK identity mismatch")
    for r in translations+checks:
        j=int(r["stage_index"])
        if float(r["load_kN"])!=LOADS[j-1] or r["available"].lower() not in ("true","false"):
            raise ValueError("background load/validity mismatch")
        if r["available"].lower()=="true" and not np.isfinite([float(r["shift_n"]),float(r["shift_t"])]).all():
            raise ValueError("nonfinite available background shift")
        if "anchor_id" in r:
            k=int(r["anchor_id"])
            if r["role"]!="check" or float(r["offset_n"])!=(-100 if k<6 else 100) or float(r["offset_t"])!=(-72 if k%2==0 else 72):
                raise ValueError("CHECK offset/role mismatch")
            if k==5 and r["available"].lower()!="false":raise ValueError("first-frame excluded a5 reintroduced")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"):raise RuntimeError("clean code required")
    args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id="S03-E026-D01",run_id="S03-E026-D01-R001",protocol="T1-local-audit-v1",
                 code_commit=git("rev-parse","HEAD"),git_dirty=False,hostname=socket.gethostname(),
                 pid=os.getpid(),command=sys.argv,python=sys.executable,gpu=None,
                 started_utc=datetime.now(timezone.utc).isoformat(),execution="running",retrieval="pending",
                 output=str(args.output.resolve()),producer="Mac lightweight cache audit",budget_seconds=60)
    try:
        e020=args.archive/"S03-E020-D01/runs/S03-E020-D01-R001/outputs"
        e019=args.archive/"S03-E019-D01/runs/S03-E019-D01-R001/outputs"
        source=json.loads((e020/"runtime_receipt.json").read_text())
        if source["execution"]!="succeeded" or source["code_commit"]!=SOURCE_COMMIT or source["protocol"]!="tangent-response-v1":
            raise ValueError("E020 source run identity changed")
        bg=json.loads((e019/"runtime_receipt.json").read_text())
        if bg["execution"]!="succeeded" or bg["code_commit"]!="ac56fdb6348f4cb3636271cee6b10e9cc5bb3212":
            raise ValueError("E019 source run identity changed")
        records={}
        for r in read_csv(e020/"measurements.csv"):
            if int(r["transect_id"])!=1 or int(r["stage_index"]) not in STAGES or abs(float(r["tangent_px"]))>2:continue
            key=(int(r["stage_index"]),r["arm"],float(r["tangent_px"]))
            if key in records:raise ValueError("duplicate selected profile key")
            records[key]=r
        if len(records)!=54:raise ValueError("selected profile coverage changed")
        with np.load(e020/"source_arrays.npz",allow_pickle=False) as z:
            rows,pairs,positions,arrays=extract(z,records)
        translations=[r for r in read_csv(e019/"translations.csv") if int(r["transect_id"])==1 and int(r["stage_index"]) in STAGES]
        checks=[r for r in read_csv(e019/"anchor_matches.csv") if int(r["transect_id"])==1 and int(r["stage_index"]) in STAGES and r["role"]=="check"]
        validate_background(translations,checks)
        write_csv(args.output/"measurements.csv",rows);write_csv(args.output/"stage_pairs.csv",pairs)
        write_csv(args.output/"position_counterfactuals.csv",positions)
        write_csv(args.output/"translations.csv",translations);write_csv(args.output/"check_support.csv",checks)
        np.savez_compressed(args.output/"selected_cache.npz",normal_offsets=S,**arrays)
        summary=summarize(positions)
        dump_new(args.output/"summary.json",summary)
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError("60s budget")
        receipt.update(execution="succeeded",retrieval="verified_local",measurement_rows=len(rows),
                       position_rows=len(positions),stage_pair_rows=len(pairs),source_E020=str(e020),source_E019=str(e019))
        print(json.dumps(summary,indent=2))
    except Exception as error:
        receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,
                       cpu_seconds=time.process_time()-cpu)
        dump_new(args.output/"runtime_receipt.json",receipt)


if __name__=="__main__":main()
