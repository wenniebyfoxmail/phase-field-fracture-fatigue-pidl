"""E024 compare signed background CHECK residuals with E023 finite bands."""
import argparse
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import numpy as np
from d01_short_support import ARMS,LOADS,EPS,read_csv,boolean,clean
from d01_relative_tolerance import RHOS,EXPECTED_COUNTS,bounds
from d01_background_anchor_diagnostic import write_csv

BG_COMMIT="ac56fdb6348f4cb3636271cee6b10e9cc5bb3212"
TOL_COMMIT="9f41bb7b76a0b95370e0c5f687a1e2c18fdbf3e9"
STATES=("proxy_compatible","beyond_stable_band","common_sensitive","outside_grid","unassessable")
OFFSETS=[(-100,-24),(-100,24),(100,-24),(100,24),(-100,-72),(-100,72),(100,-72),(100,72)]

def pair_key(r):
    arm,j,t=r["arm"],int(r["stage_a"]),int(r["transect_id"])
    if arm not in ARMS or j not in range(3) or t not in range(1,13) or int(r["stage_b"])!=j+1:
        raise ValueError("pair key")
    if (float(r["load_a_kN"]),float(r["load_b_kN"]))!=(LOADS[j],LOADS[j+1]):raise ValueError("pair loads")
    return arm,j,t

def bg_key(r):
    j,t=int(r["stage_index"]),int(r["transect_id"])
    if j not in range(4) or t not in range(1,13) or float(r["load_kN"])!=LOADS[j]:raise ValueError("background key/load")
    return j,t

def require_close(a,b,what):
    if not np.isfinite([a,b]).all() or abs(a-b)>EPS:raise ValueError(what)

def load_background(source,manifest_path):
    receipt=json.loads((source/"runtime_receipt.json").read_text())
    if (receipt.get("code_commit"),receipt.get("git_status"),receipt.get("execution"),receipt.get("anchor_rows"),receipt.get("translation_rows"))!=(BG_COMMIT,"","succeeded",288,48):raise ValueError("background receipt identity")
    manifest={}
    for r in read_csv(manifest_path):
        t,k=int(r["transect_id"]),int(r["anchor_id"])
        if t not in range(1,13) or k not in range(8) or (t,k) in manifest:raise ValueError("manifest key/duplicate")
        if r["role"]!=("fit" if k<4 else "check") or (int(r["offset_n"]),int(r["offset_t"]))!=OFFSETS[k]:raise ValueError("manifest geometry")
        if boolean(r["eligible_first_frame"])!=((t,k)!=(1,5)):raise ValueError("frozen exclusion")
        manifest[t,k]=r
    if len(manifest)!=96:raise ValueError("manifest coverage")
    trans={}
    for r in read_csv(source/"translations.csv"):
        key=bg_key(r)
        if key in trans:raise ValueError("duplicate translation")
        if key[0]==0 and not boolean(r["available"]):raise ValueError("origin translation must be available")
        if boolean(r["available"]):
            if not np.isfinite([float(r["shift_n"]),float(r["shift_t"])]).all():raise ValueError("nonfinite translation")
            if key[0]==0 and (float(r["shift_n"])!=0 or float(r["shift_t"])!=0):raise ValueError("origin translation")
        trans[key]=r
    if len(trans)!=48:raise ValueError("translation coverage")
    anchors={}
    for r in read_csv(source/"anchor_matches.csv"):
        j,t=bg_key(r);k=int(r["anchor_id"]);key=j,t,k
        if j==0 or k not in range(8) or key in anchors:raise ValueError("anchor key/duplicate")
        m=manifest[t,k]
        if (r["role"],int(r["offset_n"]),int(r["offset_t"]))!=(m["role"],int(m["offset_n"]),int(m["offset_t"])):raise ValueError("anchor role/geometry")
        available=boolean(r["available"]);correction=boolean(trans[j,t]["available"])
        if boolean(r["correction_available"])!=correction:raise ValueError("correction flag")
        if not boolean(m["eligible_first_frame"]) and (available or r["reason"]!="unsafe_first_frame"):raise ValueError("excluded anchor")
        if available:
            n,tt=float(r["shift_n"]),float(r["shift_t"])
            require_close(float(r["before_residual_px"]),math.hypot(n,tt),"before norm replay")
            if correction:
                cn,ct=float(trans[j,t]["shift_n"]),float(trans[j,t]["shift_t"])
                require_close(float(r["after_residual_px"]),math.hypot(n-cn,tt-ct),"after norm replay")
        anchors[key]=r
    if len(anchors)!=288:raise ValueError("anchor coverage")
    for j in range(1,4):
        for t in range(1,13):
            fit=[anchors[j,t,k] for k in range(4)]
            valid=all(boolean(r["available"]) for r in fit)
            if boolean(trans[j,t]["available"])!=valid:raise ValueError("FIT correction availability")
            if valid:
                for component in ("shift_n","shift_t"):
                    require_close(float(trans[j,t][component]),float(np.median([float(r[component]) for r in fit])),"FIT median replay")
    return manifest,trans,anchors

def load_tolerance(source):
    receipt=json.loads((source/"runtime_receipt.json").read_text())
    if (receipt.get("experiment_id"),receipt.get("protocol"),receipt.get("code_commit"),receipt.get("git_status"),receipt.get("execution"),receipt.get("pair_rows"),receipt.get("band_rows"))!=("S03-E023-D01","relative-tolerance-v1",TOL_COMMIT,"","succeeded",72,648):raise ValueError("tolerance receipt identity")
    pairs={};bands={}
    for r in read_csv(source/"pair_bounds.csv"):
        key=pair_key(r)
        if key in pairs:raise ValueError("duplicate tolerance pair")
        if boolean(r["eligible"]) and (not boolean(r["baseline_valid"]) or not np.isfinite(float(r["baseline_delta_px"])) or abs(float(r["baseline_delta_px"]))<=EPS):raise ValueError("invalid eligible D0")
        if boolean(r["eligible"]) and int(r["valid_cells"])!=81:raise ValueError("eligible full81 support")
        pairs[key]=r
    for r in read_csv(source/"band_metrics.csv"):
        key=pair_key(r);rho=float(r["rho_px"])
        if key not in pairs or rho not in RHOS or (key,rho) in bands:raise ValueError("band key/duplicate")
        eligible=boolean(r["eligible"])
        if eligible!=boolean(pairs[key]["eligible"]):raise ValueError("band eligibility")
        if int(r["grid_cells"])!=EXPECTED_COUNTS[list(RHOS).index(rho)]:raise ValueError("band cell count")
        if eligible:
            boolean(r["direction_stable"]);boolean(r["amplitude_stable"])
            if int(r["valid_cells"])!=int(r["grid_cells"]):raise ValueError("eligible band support")
            response,ratio=float(r["max_abs_deviation_px"]),float(r["max_deviation_to_signal"])
            if not np.isfinite([response,ratio]).all() or min(response,ratio)<0:raise ValueError("band response")
            require_close(ratio,response/abs(float(pairs[key]["baseline_delta_px"])),"band ratio replay")
            if boolean(r["amplitude_stable"])!=(response<abs(float(pairs[key]["baseline_delta_px"]))):raise ValueError("strict amplitude replay")
        bands[key,rho]=r
    if len(pairs)!=72 or len(bands)!=648:raise ValueError("tolerance coverage")
    for key,pair in pairs.items():
        for prefix,field in (("","direction_stable"),("amplitude_","amplitude_stable")):
            flags=[boolean(bands[key,float(rho)][field]) if boolean(pair["eligible"]) else None for rho in RHOS]
            expected=bounds(flags)
            if pair[prefix+"status"]!=expected["status"]:raise ValueError("bounds status replay")
            for name in ("largest_stable_tested_px","first_loss_tested_px"):
                val=pair[prefix+name]; exp=expected[name]
                if exp is None:
                    if val not in ("","None"):raise ValueError("missing bound replay")
                else:require_close(float(val),exp,"bound replay")
    return pairs,bands

def residual_rows(manifest,trans,anchors):
    rows=[]
    for arm in ARMS:
        for j in range(4):
            for t in range(1,13):
                for k in range(4,8):
                    eligible=boolean(manifest[t,k]["eligible_first_frame"])
                    anchor_available=j==0 or boolean(anchors[j,t,k]["available"])
                    correction_available=boolean(trans[j,t]["available"])
                    valid=eligible and anchor_available and (arm==ARMS[0] or correction_available)
                    if j==0:value=0. if valid else np.nan
                    elif valid:value=float(anchors[j,t,k]["shift_t"])-(float(trans[j,t]["shift_t"]) if arm==ARMS[1] else 0.)
                    else:value=np.nan
                    rows.append(dict(arm=arm,stage_index=j,load_kN=LOADS[j],transect_id=t,anchor_id=k,
                                     eligible_first_frame=eligible,anchor_available=anchor_available,
                                     valid=valid,residual_t_px=value,reference_zero_by_definition=j==0,
                                     excluded_reason="origin_patch_intersects_crack" if not eligible else ""))
    return rows

def classify(complete,tolerance_eligible,common_sensitive,absolute_max,mismatch,bands):
    rho=math.ceil(mismatch/.5)*.5 if complete else np.nan
    outside=bool(complete and (absolute_max>2 or mismatch>4))
    amplitude=None;stable=None
    if not complete or not tolerance_eligible:status="unassessable"
    elif common_sensitive:status="common_sensitive"
    elif outside:status="outside_grid"
    else:
        stable=boolean(bands[rho]["direction_stable"]);amplitude=boolean(bands[rho]["amplitude_stable"])
        status="proxy_compatible" if stable else "beyond_stable_band"
    return dict(status=status,required_tested_rho_px=rho,absolute_outside_grid=outside,
                required_band_direction_stable=stable,required_band_amplitude_stable=amplitude)

def assess(a,b,valid,eligible,tol,bands):
    a,b=np.asarray(a,float),np.asarray(b,float);valid,eligible=np.asarray(valid,bool),np.asarray(eligible,bool)
    if any(x.shape!=(4,) for x in (a,b,valid,eligible)):raise ValueError("four nominal CHECK slots")
    if not eligible.any():raise ValueError("no prescribed eligible support")
    if not np.isfinite(a[valid]).all() or not np.isfinite(b[valid]).all():raise ValueError("nonfinite available residual")
    complete=bool(np.all(valid[eligible]));n=int(eligible.sum())
    m=float(np.max(abs(b[eligible]-a[eligible]))) if complete else np.nan
    absolute=float(max(np.max(abs(a[eligible])),np.max(abs(b[eligible])))) if complete else np.nan
    cross=float(np.max(abs(b[eligible,None]-a[None,eligible]))) if complete else np.nan
    common=tol["status"]=="no_admissible"
    primary=classify(complete,boolean(tol["eligible"]),common,absolute,m,bands)
    sensitivity=classify(complete,boolean(tol["eligible"]),common,absolute,cross,bands)
    return dict(expected_checks=n,valid_checks=int(np.sum(valid&eligible)),nominal_checks=4,
                complete_eligible_checks=complete,full_four_checks=bool(n==4 and complete),
                tolerance_eligible=boolean(tol["eligible"]),common_sensitive=common,
                absolute_max_t_px=absolute,matched_max_relative_t_px=m,cross_max_relative_t_px=cross,
                **primary,**{"cross_"+k:v for k,v in sensitivity.items()},
                last_stable_tested_px=float(tol["largest_stable_tested_px"]) if tol["largest_stable_tested_px"] not in ("","None") else np.nan,
                first_loss_tested_px=float(tol["first_loss_tested_px"]) if tol["first_loss_tested_px"] not in ("","None") else np.nan)

def calculate(manifest,trans,anchors,tolerances,bands):
    stages=residual_rows(manifest,trans,anchors)
    index={(r["arm"],r["stage_index"],r["transect_id"],r["anchor_id"]):r for r in stages}
    pairs=[];checks=[]
    for key,tol in tolerances.items():
        arm,j,t=key;aa=[];bb=[];vv=[];ee=[]
        identity={k:tol[k] for k in ("arm","stage_a","stage_b","load_a_kN","load_b_kN","transect_id")}
        for k in range(4,8):
            a,b=index[arm,j,t,k],index[arm,j+1,t,k];valid=a["valid"] and b["valid"]
            aa.append(a["residual_t_px"]);bb.append(b["residual_t_px"]);vv.append(valid);ee.append(a["eligible_first_frame"])
            checks.append(dict(identity,anchor_id=k,eligible_first_frame=a["eligible_first_frame"],valid=valid,
                               residual_a_t_px=aa[-1],residual_b_t_px=bb[-1],relative_t_px=bb[-1]-aa[-1] if valid else np.nan))
        result=assess(aa,bb,vv,ee,tol,{float(rho):bands[key,float(rho)] for rho in RHOS})
        pairs.append(dict(identity,baseline_delta_px=float(tol["baseline_delta_px"]),**result))
    by_arm=[]
    for arm in ARMS:
        rows=[r for r in pairs if r["arm"]==arm];ck=[r for r in checks if r["arm"]==arm]
        by_arm.append(dict(arm=arm,opportunities=len(rows),eligible_complete=sum(r["complete_eligible_checks"] for r in rows),
                           valid_check_pairs=sum(r["valid"] for r in ck),nominal_check_pairs=len(ck),
                           states={s:sum(r["status"]==s for r in rows) for s in STATES},
                           cross_states={s:sum(r["cross_status"]==s for r in rows) for s in STATES},
                           compatible_with_amplitude_guard=sum(r["status"]=="proxy_compatible" and r["required_band_amplitude_stable"] is True for r in rows),
                           all_absolute_outside=sum(r["absolute_outside_grid"] for r in rows),
                           compatible_partial_static_support=sum(r["status"]=="proxy_compatible" and r["expected_checks"]<4 for r in rows)))
    summary=dict(experiment_id="S03-E024-D01",protocol="check-tolerance-v1",pair_rows=len(pairs),check_pair_rows=len(checks),stage_residual_rows=len(stages),by_arm=by_arm,
                 primary="same-CHECK matched drift versus tested band, original_H36",physical_usable=False,normal_error_qualified=False,new_forecast_scores=False,independent_specimens=1)
    return pairs,checks,stages,summary

def run(background,manifest,tolerance,output,budget=60):
    if not 0<budget<=60:raise ValueError("budget")
    dirty=subprocess.check_output(["git","status","--short"],text=True)
    if dirty:raise RuntimeError("commit source before execution")
    output.mkdir(parents=True,exist_ok=False);start,cpu=time.monotonic(),time.process_time()
    receipt=dict(experiment_id="S03-E024-D01",protocol="check-tolerance-v1",execution="running",started_utc=datetime.now(timezone.utc).isoformat(),hostname=socket.gethostname(),pid=os.getpid(),code_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),git_status=dirty,budget_seconds=budget,thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")})
    def check():
        if max(time.monotonic()-start,time.process_time()-cpu)>=budget:raise TimeoutError("CPU/wall budget")
    try:
        inputs=[background/n for n in ("anchor_matches.csv","translations.csv","runtime_receipt.json")]+[manifest]+[tolerance/n for n in ("pair_bounds.csv","band_metrics.csv","runtime_receipt.json")]
        receipt["input_files"]=[dict(path=str(p),bytes=p.stat().st_size) for p in inputs]
        m,t,a=load_background(background,manifest);p,b=load_tolerance(tolerance);check()
        pairs,checks,stages,result=calculate(m,t,a,p,b);check()
        if (len(pairs),len(checks),len(stages))!=(72,288,384):raise ValueError("output coverage")
        for name,rows in (("position_comparison.csv",pairs),("check_pair_residuals.csv",checks),("stage_residuals.csv",stages)):write_csv(output/name,rows)
        (output/"summary.json").write_text(json.dumps(clean(result),indent=2,allow_nan=False)+"\n");check();receipt.update(execution="succeeded",pair_rows=72,check_pair_rows=288,stage_residual_rows=384)
    except Exception as exc:receipt.update(execution="stopped",error=repr(exc));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        if max(receipt["wall_seconds"],receipt["cpu_seconds"])>=budget:receipt["execution"]="budget_stopped"
        (output/"runtime_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        if receipt["execution"]=="budget_stopped":raise TimeoutError("finalisation budget")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("background","manifest","tolerance","output"):p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args();run(args.background,args.manifest,args.tolerance,args.output)
