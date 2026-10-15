"""Frozen Beam4 tangent scan: unchanged half-depth, operational component events."""
import argparse
import csv
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import time

import numpy as np
from d01_background_anchor_diagnostic import load_inputs, load_gray, local_grid, source_sample, write_csv
from independent_d01_halfdepth import sampling_grid, native_to_source, median_source_profile, measure

TANGENTS = np.arange(-10.,10.25,.5)
ARMS = ("original_H","background_aligned")


def halfdepth_components(s, result):
    """Enumerate bounded intervals using the frozen functional's own half level."""
    if not result["valid"]:
        return []
    d=result["deficit"]; half=result["depth"]/2
    mask=d>=half
    edges=np.diff(np.r_[False,mask,False].astype(int))
    starts,ends=np.flatnonzero(edges==1),np.flatnonzero(edges==-1)
    components=[]
    def crossing(i,j):
        return float(s[i]+(half-d[i])*(s[j]-s[i])/(d[j]-d[i]))
    for start,end in zip(starts,ends):
        # match frozen measure: reaching index0/last on the below-level side censors.
        if start<=1 or end>=len(s)-1:
            continue
        left,right=crossing(start-1,start),crossing(end-1,end)
        if right-left>=1:
            components.append([left,right])
    selected=[c for c in components if c[0]<=result["peak_px"]<=c[1]]
    if len(selected)!=1 or not np.allclose(selected[0],[result["left_px"],result["right_px"]],atol=1e-8,rtol=0):
        raise ValueError("component enumeration disagrees with unchanged measure")
    return components


def overlap(a,b):
    return min(a[1],b[1])-max(a[0],b[0])>0


def classify_pair(a,b):
    paired=bool(a["valid"] and b["valid"])
    result=dict(paired_valid=paired,switch_candidate=False,split_candidate=False,merge_candidate=False,
                any_band_event=False,width_change_px=np.nan,peak_change_px=np.nan)
    if not paired:
        return result
    ia=[a["left_px"],a["right_px"]]; ib=[b["left_px"],b["right_px"]]
    switch=not overlap(ia,ib)
    split=sum(overlap(ia,c) for c in b["components"])>1
    merge=sum(overlap(ib,c) for c in a["components"])>1
    result.update(switch_candidate=switch,split_candidate=split,merge_candidate=merge,
                  any_band_event=bool(switch or split or merge),
                  width_change_px=float(b["width_px"]-a["width_px"]),
                  peak_change_px=float(b["peak_px"]-a["peak_px"]))
    return result


def read_csv(path):
    with path.open(newline="") as f: return list(csv.DictReader(f))


def input_digest(paths):
    digest=hashlib.sha256()
    for path in paths:
        data=path.read_bytes()
        digest.update(path.name.encode()+b"\0"+str(len(data)).encode()+b"\0"+data)
    return digest.hexdigest()


def validate_records(translations,expected):
    corrections={(int(r["stage_index"]),int(r["transect_id"])):r for r in translations}
    identities={(j,t) for j in range(4) for t in range(1,13)}
    if len(translations)!=48 or set(corrections)!=identities: raise ValueError("translation identity mismatch")
    for (j,t),r in corrections.items():
        if float(r["load_kN"])!=(10,30,40,50)[j] or r["available"].lower() not in ("true","false"):
            raise ValueError("translation stage/validity malformed")
        if r["available"].lower()=="true":
            shift=np.array([float(r["shift_n"]),float(r["shift_t"])])
            if not np.isfinite(shift).all(): raise ValueError("nonfinite translation")
            if j==0 and not np.array_equal(shift,np.zeros(2)): raise ValueError("origin translation must be zero")
        elif j==0: raise ValueError("origin translation must be available")
    references={(int(r["stage_index"]),int(r["transect_id"]),r["arm"]):r for r in expected if r["variant"]=="baseline"}
    wanted={(j,t,arm) for j,t in identities for arm in ARMS}
    if len(expected)!=480 or len(references)!=96 or set(references)!=wanted: raise ValueError("reference identity mismatch")
    for (j,t,arm),r in references.items():
        if float(r["load_kN"])!=(10,30,40,50)[j] or r["valid"].lower() not in ("true","false"):
            raise ValueError("reference stage/validity malformed")
        if r["valid"].lower()=="true" and not np.isfinite(float(r["width_px"])):
            raise ValueError("nonfinite valid replay reference")
    return corrections,references


def run(inputs, e019, output, lock_path, budget=120):
    if not 0 < budget <= 120: raise ValueError("budget must be in (0,120]")
    output.mkdir(parents=True,exist_ok=False)
    started,cpu=time.monotonic(),time.process_time()
    receipt=dict(experiment_id="S03-E020-D01",protocol="tangent-response-v1",execution="running",
                 started_utc=datetime.now(timezone.utc).isoformat(),hostname=socket.gethostname(),pid=os.getpid(),
                 code_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                 git_status=subprocess.check_output(["git","status","--short"],text=True),
                 inputs=str(inputs),e019_outputs=str(e019),budget_seconds=budget,
                 thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},sources=[])
    measurements,pairs,curves,arrays,replays=[],[],[],{},[]
    def check():
        if time.monotonic()-started>=budget or time.process_time()-cpu>=budget: raise TimeoutError("CPU/wall budget")
    try:
        lock=json.loads(lock_path.read_text())
        paths=[inputs/"geometry.json",inputs/"Beam4_inputs.npz",e019/"translations.csv",e019/"width_variants.csv"]
        if [p.name for p in paths]!=lock["ordered_files"]: raise ValueError("input lock file order mismatch")
        receipt["input_snapshot_digest"]=input_digest(paths)
        if receipt["input_snapshot_digest"]!=lock["snapshot_digest"]: raise ValueError("frozen input snapshot changed")
        prior=json.loads((e019/"runtime_receipt.json").read_text())
        if prior["execution"]!="succeeded" or prior["code_commit"]!=lock["expected_E019_computation_commit"]:
            raise ValueError("E019 runtime identity changed")
        g,h,s,loads=load_inputs(inputs)
        translations=read_csv(e019/"translations.csv")
        expected=read_csv(e019/"width_variants.csv")
        corrections,references=validate_records(translations,expected)
        for j,stage in enumerate(g["stages"]):
            check(); image=load_gray(stage); receipt["sources"].append(stage)
            for tr in g["transects"]:
                correction=corrections[(j,tr["id"])]
                if float(correction["load_kN"])!=loads[j]: raise ValueError("translation stage/load mismatch")
                n=np.asarray(tr["normal"],float); tangent=np.array([-n[1],n[0]])
                for arm in ARMS:
                    check()
                    available=arm=="original_H" or correction["available"].lower()=="true"
                    delta=np.zeros(2) if arm=="original_H" else (float(correction["shift_n"])*n+float(correction["shift_t"])*tangent if available else None)
                    if available and not np.isfinite(delta).all(): raise ValueError("nonfinite frozen correction")
                    identity=dict(stage_index=j,load_kN=float(loads[j]),transect_id=tr["id"],arm=arm)
                    results,profiles,deficits=[],[],[]
                    for ti,t in enumerate(TANGENTS):
                        check()
                        if available:
                            points=sampling_grid(tr["center"],tr["normal"],s,tangent_offsets=np.arange(-2,3)+t)+delta
                            source=native_to_source(points,np.linalg.inv(h[j]),g["native_shape"],g["working_shape"])
                            profile=median_source_profile(image,source)
                            result=measure(s,profile)
                            result["components"]=halfdepth_components(s,result)
                            profiles.append(profile); deficits.append(result["deficit"])
                        else:
                            result=dict(valid=False,reason="unavailable_correction",width_px=np.nan,left_px=np.nan,right_px=np.nan,
                                        peak_px=np.nan,depth=np.nan,components=[])
                            profiles.append(np.full(len(s),np.nan)); deficits.append(np.full(len(s),np.nan))
                        results.append(result)
                        row=dict(identity,t_index=ti,tangent_px=float(t),**{k:result[k] for k in ("width_px","left_px","right_px","peak_px","depth","valid","reason")},
                                 components_json=json.dumps(result["components"]))
                        measurements.append(row)
                        if ti:
                            pairs.append(dict(identity,t_index_a=ti-1,tangent_a_px=float(TANGENTS[ti-1]),tangent_b_px=float(t),**classify_pair(results[ti-1],result)))
                    zero=results[20]; reference=references[(j,tr["id"],arm)]
                    if zero["valid"]!=(reference["valid"].lower()=="true"): raise ValueError("t0 validity replay mismatch")
                    difference=abs(zero["width_px"]-float(reference["width_px"])) if zero["valid"] else np.nan
                    if zero["valid"] and (not np.isfinite([zero["width_px"],float(reference["width_px"]),difference]).all() or difference>1e-8):
                        raise ValueError("t0 width replay mismatch/nonfinite")
                    replays.append(dict(identity,t0_valid=zero["valid"],abs_replay_difference_px=difference))
                    key=f"st{j}_tr{tr['id']}_{arm}"
                    arrays[key+"_profiles"]=np.array(profiles)
                    arrays[key+"_deficits"]=np.array(deficits)
                    if available:
                        raw_grid=sampling_grid(tr["center"],tr["normal"],np.arange(-60,61),tangent_offsets=np.arange(-14,14.25,.5))+delta
                        arrays[key+"_strip"]=source_sample(image,raw_grid,h[j],g)
                    cp=[r for r in pairs[-40:] if r["paired_valid"]]
                    vals=[r["width_px"] for r in results if r["valid"]]
                    curves.append(dict(identity,valid_profiles=len(vals),total_profiles=41,paired_adjacent=len(cp),
                                       band_events=sum(r["any_band_event"] for r in cp),
                                       width_range_px=max(vals)-min(vals) if vals else np.nan,
                                       max_adjacent_width_change_px=max([abs(r["width_change_px"]) for r in cp],default=np.nan),
                                       max_adjacent_peak_change_px=max([abs(r["peak_change_px"]) for r in cp],default=np.nan)))
        if len(measurements)!=3936 or len(pairs)!=3840 or len(curves)!=96: raise ValueError("scan coverage mismatch")
        check(); receipt["execution"]="succeeded"
    except Exception as exc:
        receipt.update(execution="stopped",error=repr(exc)); raise
    finally:
        for name,rows in (("measurements.csv",measurements),("adjacent_pairs.csv",pairs),("curve_summaries.csv",curves),("t0_replay.csv",replays)):
            write_csv(output/name,rows)
        if arrays: np.savez_compressed(output/"source_arrays.npz",**arrays)
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-started,
                       cpu_seconds=time.process_time()-cpu,measurement_rows=len(measurements),adjacent_rows=len(pairs),curve_rows=len(curves))
        if receipt["wall_seconds"]>=budget or receipt["cpu_seconds"]>=budget: receipt["execution"]="budget_stopped"
        (output/"runtime_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        if receipt["execution"]=="budget_stopped": raise TimeoutError("budget finalization")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs",type=Path,required=True); p.add_argument("--e019",type=Path,required=True)
    p.add_argument("--lock",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    run(a.inputs,a.e019,a.output,a.lock)

if __name__=="__main__": main()
