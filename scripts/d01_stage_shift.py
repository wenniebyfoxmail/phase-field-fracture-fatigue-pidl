"""E022 fixed-grid stage difference: common versus Cartesian location shifts."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import numpy as np
from d01_short_support import ARMS,LOADS,EPS,boolean,index,load_snapshot,clean
from d01_background_anchor_diagnostic import write_csv

SHIFTS=np.arange(-2,2.25,.5)

def evaluate(a,b,va,vb):
    """Rows=next-stage shift, columns=previous-stage shift; diagonal=common."""
    a,b=np.asarray(a,float),np.asarray(b,float)
    va,vb=np.asarray(va,bool),np.asarray(vb,bool)
    if any(x.shape!=(9,) for x in (a,b,va,vb)): raise ValueError("nine shifts required")
    if not np.isfinite(a[va]).all() or not np.isfinite(b[vb]).all(): raise ValueError("nonfinite valid input")
    valid=vb[:,None]&va[None,:]
    matrix=np.where(valid,b[:,None]-a[None,:],np.nan)
    origin=bool(va[4] and vb[4]);d0=float(b[4]-a[4]) if origin else np.nan
    deviations=matrix-d0 if origin else np.full((9,9),np.nan)
    matched=bool(va.all() and vb.all())
    row=dict(paired_valid=matched,baseline_valid=origin,baseline_delta_px=d0,
             common_valid=int(np.diag(valid).sum()),independent_valid=int(valid.sum()))
    metrics=("common_rms_px","independent_rms_px","paired_rms_change_px","common_to_independent_ratio",
             "common_max_abs_px","independent_max_abs_px","grid_covariance_px2","identity_residual_px2",
             "common_rms_to_signal_ratio","independent_rms_to_signal_ratio","common_loss_fraction","independent_loss_fraction")
    row.update({k:np.nan for k in metrics})
    row.update(baseline_nonzero=bool(origin and abs(d0)>EPS),common_opposite=None,independent_opposite=None,
               common_zero=None,independent_zero=None,common_sign_loss=None,independent_sign_loss=None,
               common_nonzero_if_baseline_zero=None,independent_nonzero_if_baseline_zero=None)
    if matched:
        common=np.diag(deviations)
        c=float(np.sqrt(np.mean(common**2)));i=float(np.sqrt(np.mean(deviations**2)))
        cov=float(np.mean((a-a.mean())*(b-b.mean())))
        residual=i*i-c*c-2*cov
        if abs(residual)>EPS: raise ValueError("finite-grid covariance identity mismatch")
        row.update(common_rms_px=c,independent_rms_px=i,paired_rms_change_px=c-i,
                   common_to_independent_ratio=c/i if i>EPS else np.nan,
                   common_max_abs_px=float(np.max(abs(common))),independent_max_abs_px=float(np.max(abs(deviations))),
                   grid_covariance_px2=cov,identity_residual_px2=residual,
                   common_rms_to_signal_ratio=c/abs(d0) if abs(d0)>EPS else np.nan,
                   independent_rms_to_signal_ratio=i/abs(d0) if abs(d0)>EPS else np.nan)
        if abs(d0)>EPS:
            for name,values in (("common",np.diag(matrix)),("independent",matrix)):
                opposite=int(np.sum(values < -EPS)) if d0>0 else int(np.sum(values > EPS))
                zero=int(np.sum(abs(values)<=EPS))
                row.update({name+"_opposite":opposite,name+"_zero":zero,name+"_sign_loss":bool(opposite or zero),
                            name+"_loss_fraction":(opposite+zero)/values.size})
        else:
            row.update(common_nonzero_if_baseline_zero=int(np.sum(abs(np.diag(matrix))>EPS)),
                       independent_nonzero_if_baseline_zero=int(np.sum(abs(matrix)>EPS)))
    return row,matrix,deviations,valid

def summary(rows):
    matched=[r for r in rows if r["paired_valid"]]
    nonzero=[r for r in matched if r["baseline_nonzero"]]
    ratio=[r["common_to_independent_ratio"] for r in matched if np.isfinite(r["common_to_independent_ratio"])]
    def med(k): return float(np.median([r[k] for r in matched])) if matched else None
    return dict(opportunities=len(rows),matched=len(matched),median_common_rms_px=med("common_rms_px"),
                median_independent_rms_px=med("independent_rms_px"),median_paired_rms_change_px=med("paired_rms_change_px"),
                common_lower=sum(r["paired_rms_change_px"] < -EPS for r in matched),
                equal=sum(abs(r["paired_rms_change_px"])<=EPS for r in matched),
                common_higher=sum(r["paired_rms_change_px"] > EPS for r in matched),
                ratio_support=len(ratio),zero_independent_rms=sum(r["independent_rms_px"]<=EPS for r in matched),
                median_common_to_independent_ratio=float(np.median(ratio)) if ratio else None,
                nonzero_baseline_pairs=len(nonzero),zero_baseline_pairs=len(matched)-len(nonzero),
                common_pairs_with_sign_loss=sum(r["common_sign_loss"] for r in nonzero),
                independent_pairs_with_sign_loss=sum(r["independent_sign_loss"] for r in nonzero),
                common_pairs_with_opposite_sign=sum(r["common_opposite"]>0 for r in nonzero),
                independent_pairs_with_opposite_sign=sum(r["independent_opposite"]>0 for r in nonzero),
                mean_common_grid_loss_fraction=float(np.mean([r["common_loss_fraction"] for r in nonzero])) if nonzero else None,
                mean_independent_grid_loss_fraction=float(np.mean([r["independent_loss_fraction"] for r in nonzero])) if nonzero else None,
                common_pairs_rms_at_least_signal=sum(r["common_rms_px"]>=abs(r["baseline_delta_px"]) for r in nonzero),
                independent_pairs_rms_at_least_signal=sum(r["independent_rms_px"]>=abs(r["baseline_delta_px"]) for r in nonzero),
                maximum_identity_residual_px2=max([abs(r["identity_residual_px2"]) for r in matched],default=None))

def calculate(groups,check=lambda:None):
    metrics=[];perturbations=[];indices=[index(x) for x in SHIFTS]
    for arm in ARMS:
        for j in range(3):
            for t in range(1,13):
                check()
                old,new=groups[(j,t,arm)],groups[(j+1,t,arm)]
                a=np.array([float(old[k]["width_px"]) for k in indices]);b=np.array([float(new[k]["width_px"]) for k in indices])
                va=[boolean(old[k]["valid"]) for k in indices];vb=[boolean(new[k]["valid"]) for k in indices]
                row,matrix,deviations,valid=evaluate(a,b,va,vb)
                identity=dict(arm=arm,stage_a=j,stage_b=j+1,load_a_kN=LOADS[j],load_b_kN=LOADS[j+1],transect_id=t)
                metrics.append(dict(identity,**row))
                for ib,db in enumerate(SHIFTS):
                    for ia,da in enumerate(SHIFTS):
                        perturbations.append(dict(identity,shift_a_px=float(da),shift_b_px=float(db),common=ia==ib,
                                                  valid_difference=bool(valid[ib,ia]),baseline_valid=row["baseline_valid"],
                                                  baseline_delta_px=row["baseline_delta_px"],stage_delta_px=float(matrix[ib,ia]),deviation_px=float(deviations[ib,ia])))
    return metrics,perturbations

def run(source,output,budget=60):
    if not 0<budget<=60: raise ValueError("budget must be in (0,60]")
    output.mkdir(parents=True,exist_ok=False);start,cpu=time.monotonic(),time.process_time()
    receipt=dict(experiment_id="S03-E022-D01",protocol="stage-shift-v1",execution="running",started_utc=datetime.now(timezone.utc).isoformat(),
                 hostname=socket.gethostname(),pid=os.getpid(),code_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                 git_status=subprocess.check_output(["git","status","--short"],text=True),source=str(source),budget_seconds=budget,
                 thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},input_files=[])
    def check():
        if max(time.monotonic()-start,time.process_time()-cpu)>=budget: raise TimeoutError("CPU/wall budget")
    try:
        receipt["input_files"]=[dict(name=n,bytes=(source/n).stat().st_size) for n in ("measurements.csv","adjacent_pairs.csv","curve_summaries.csv","t0_replay.csv","runtime_receipt.json")]
        groups,_=load_snapshot(source);check();metrics,perturbations=calculate(groups,check)
        if (len(metrics),len(perturbations))!=(72,5832): raise ValueError("coverage mismatch")
        write_csv(output/"pair_metrics.csv",metrics);write_csv(output/"perturbations.csv",perturbations)
        result=dict(experiment_id="S03-E022-D01",protocol="stage-shift-v1",pair_rows=72,perturbation_rows=5832,
                    common_rows=sum(r["common"] for r in perturbations),valid_differences=sum(r["valid_difference"] for r in perturbations),
                    primary_original_H=summary([r for r in metrics if r["arm"]==ARMS[0]]),
                    by_arm=[dict(arm=arm,overall=summary([r for r in metrics if r["arm"]==arm]),
                                 by_transition=[dict(load_a_kN=LOADS[j],load_b_kN=LOADS[j+1],**summary([r for r in metrics if r["arm"]==arm and r["stage_a"]==j])) for j in range(3)]) for arm in ARMS],
                    physical_reference=False,new_forecast_scores=False,independent_specimens=1)
        (output/"summary.json").write_text(json.dumps(clean(result),indent=2,allow_nan=False)+"\n")
        check();receipt.update(execution="succeeded",pair_rows=len(metrics),perturbation_rows=len(perturbations))
    except Exception as exc:
        receipt.update(execution="stopped",error=repr(exc));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        if max(receipt["wall_seconds"],receipt["cpu_seconds"])>=budget: receipt["execution"]="budget_stopped"
        (output/"runtime_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        if receipt["execution"]=="budget_stopped": raise TimeoutError("finalisation budget")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();run(args.source,args.output)
