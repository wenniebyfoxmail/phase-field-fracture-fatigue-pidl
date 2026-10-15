"""E021: one fixed median-of-widths support, no image sampling or forecast."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import numpy as np
from d01_background_anchor_diagnostic import write_csv

ARMS=("original_H","background_aligned")
LOADS=(10,30,40,50)
GRID=np.arange(-10,10.25,.5)
CENTRES=np.arange(-2,2.25,.5)
OFFSETS=np.arange(-2,2.25,.5)
EPS=1e-8  # arithmetic equality only, NOT metrology tolerance
E020_COMMIT="84c34422d52c7ff3f062add41a7bfe7537935861"

def read_csv(path):
    with path.open(newline="") as f: return list(csv.DictReader(f))

def boolean(x):
    if str(x).lower() not in ("true","false"): raise ValueError("malformed boolean")
    return str(x).lower()=="true"

def key(r):
    return int(r["stage_index"]),int(r["transect_id"]),r["arm"]

def index(t):
    i=int(round((t+10)*2))
    if not 0<=i<len(GRID) or GRID[i]!=t: raise ValueError("off-grid support")
    return i

def estimates(values,valid,centre):
    idx=index(centre)
    points=[index(centre+x) for x in OFFSETS]
    ok=bool(np.all(valid[points]))
    point=float(values[idx]) if valid[idx] else np.nan
    median=float(np.median(values[points])) if ok else np.nan
    return point,median,bool(valid[idx]),ok,int(np.sum(valid[points]))

def sensitivity(v):
    v=np.asarray(v,float)
    return float(max(abs(v[0]-v[1]),abs(v[2]-v[1]))) if np.isfinite(v).all() else np.nan

def direction(v):
    return 0 if abs(v)<=EPS else (1 if v>0 else -1)

def clean(value):
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list): return [clean(v) for v in value]
    if isinstance(value,(float,np.floating)) and not np.isfinite(value): return None
    return value

def paired_summary(rows):
    matched=[r for r in rows if r["paired_valid"]]
    d=np.array([r["paired_change_px"] for r in matched])
    return dict(opportunities=len(rows),matched=len(matched),
                median_point_px=float(np.median([r["point_sensitivity_px"] for r in matched])) if matched else None,
                median_segment_px=float(np.median([r["segment_sensitivity_px"] for r in matched])) if matched else None,
                median_paired_change_px=float(np.median(d)) if matched else None,
                improved=int(np.sum(d < -EPS)),equal=int(np.sum(abs(d)<=EPS)),worsened=int(np.sum(d>EPS)))

def stage_summary(rows):
    matched=[r for r in rows if r["paired_valid"]]
    nz=[r for r in matched if direction(r["point_increment_px"])!=0]
    zero=[r for r in matched if direction(r["point_increment_px"])==0]
    return dict(opportunities=len(rows),matched=len(matched),
                median_point_increment_px=float(np.median([r["point_increment_px"] for r in matched])) if matched else None,
                median_segment_increment_px=float(np.median([r["segment_increment_px"] for r in matched])) if matched else None,
                median_absolute_distortion_px=float(np.median([r["absolute_distortion_px"] for r in matched])) if matched else None,
                maximum_absolute_distortion_px=max([r["absolute_distortion_px"] for r in matched],default=None),
                nonzero_point_increments=len(nz),sign_agreement=sum(direction(r["point_increment_px"])==direction(r["segment_increment_px"]) for r in nz),
                zero_point_increments=len(zero),nonzero_segment_when_point_zero=sum(direction(r["segment_increment_px"])!=0 for r in zero))

def load_snapshot(root):
    receipt=json.loads((root/"runtime_receipt.json").read_text())
    if receipt["execution"]!="succeeded" or receipt["code_commit"]!=E020_COMMIT or receipt["git_status"]!="":
        raise ValueError("E020 runtime identity mismatch")
    if [receipt[k] for k in ("measurement_rows","adjacent_rows","curve_rows")]!=[3936,3840,96]:
        raise ValueError("E020 receipt coverage mismatch")
    rows=read_csv(root/"measurements.csv");pairs=read_csv(root/"adjacent_pairs.csv")
    curves=read_csv(root/"curve_summaries.csv");replay=read_csv(root/"t0_replay.csv")
    wanted={(j,t,a) for j in range(4) for t in range(1,13) for a in ARMS}
    groups={k:[] for k in wanted}
    if len(rows)!=3936 or len(pairs)!=3840 or len(curves)!=96 or len(replay)!=96: raise ValueError("cached counts mismatch")
    seen=set()
    for r in rows:
        k=key(r);i=int(r["t_index"])
        if k not in wanted or not 0<=i<41 or (k,i) in seen: raise ValueError("measurement key mismatch")
        seen.add((k,i))
        if float(r["load_kN"])!=LOADS[k[0]] or float(r["tangent_px"])!=GRID[i]: raise ValueError("measurement grid mismatch")
        if boolean(r["valid"]) and (not np.isfinite(float(r["width_px"])) or float(r["width_px"])<1): raise ValueError("invalid finite width")
        groups[k].append(r)
    for group in groups.values():
        group.sort(key=lambda r:int(r["t_index"]))
        if len(group)!=41: raise ValueError("curve coverage mismatch")
    event_tags={k:False for k in wanted};pseen=set()
    for r in pairs:
        k=key(r);i=int(r["t_index_a"])
        if k not in wanted or not 0<=i<40 or (k,i) in pseen: raise ValueError("pair key mismatch")
        pseen.add((k,i))
        if float(r["load_kN"])!=LOADS[k[0]] or float(r["tangent_a_px"])!=GRID[i] or float(r["tangent_b_px"])!=GRID[i+1]: raise ValueError("pair grid mismatch")
        x,y=groups[k][i:i+2];valid=boolean(x["valid"]) and boolean(y["valid"])
        flags=[boolean(r[name+"_candidate"]) for name in ("switch","split","merge")]
        event=boolean(r["any_band_event"])
        if boolean(r["paired_valid"])!=valid or event!=any(flags) or (not valid and event): raise ValueError("pair validity/union mismatch")
        if valid:
            delta=float(r["width_change_px"])
            if not np.isfinite(delta) or abs(delta-(float(y["width_px"])-float(x["width_px"])))>EPS: raise ValueError("pair width delta mismatch")
        if GRID[i]>=-4 and GRID[i+1]<=4 and event: event_tags[k]=True
    for table in (curves,replay):
        if len({key(r) for r in table})!=96 or {key(r) for r in table}!=wanted: raise ValueError("summary/replay keys mismatch")
    for r in curves:
        k=key(r);values=[float(x["width_px"]) for x in groups[k] if boolean(x["valid"])]
        if int(r["valid_profiles"])!=len(values) or int(r["total_profiles"])!=41: raise ValueError("curve counts mismatch")
        if values and (not np.isfinite(float(r["width_range_px"])) or abs(float(r["width_range_px"])-(max(values)-min(values)))>EPS): raise ValueError("curve range mismatch")
    for r in replay:
        k=key(r);ok=boolean(groups[k][20]["valid"])
        difference=float(r["abs_replay_difference_px"])
        if boolean(r["t0_valid"])!=ok or (ok and (not np.isfinite(difference) or difference>EPS or difference<0)): raise ValueError("zero replay mismatch")
    return groups,event_tags

def calculate(groups,event_tags):
    centres=[];comparisons=[];stages=[];by_key={}
    for k,group in sorted(groups.items()):
        j,t,arm=k;values=np.array([float(r["width_px"]) for r in group]);valid=np.array([boolean(r["valid"]) for r in group])
        estimates_by_c={}
        for c in CENTRES:
            p,m,pok,mok,count=estimates(values,valid,c)
            row=dict(stage_index=j,load_kN=LOADS[j],transect_id=t,arm=arm,centre_px=float(c),point_px=p,segment_px=m,
                     point_valid=pok,segment_valid=mok,support_valid_count=count,support_total=9,support_event=event_tags[k])
            centres.append(row);estimates_by_c[float(c)]=row
        endpoints=[estimates_by_c[c] for c in (-2.,0.,2.)]
        pok=all(r["point_valid"] for r in endpoints);mok=all(r["segment_valid"] for r in endpoints)
        sp=sensitivity([r["point_px"] for r in endpoints]) if pok else np.nan
        sm=sensitivity([r["segment_px"] for r in endpoints]) if mok else np.nan
        comparisons.append(dict(stage_index=j,load_kN=LOADS[j],transect_id=t,arm=arm,point_valid=pok,segment_valid=mok,
                                paired_valid=pok and mok,point_sensitivity_px=sp,segment_sensitivity_px=sm,
                                paired_change_px=sm-sp if pok and mok else np.nan,support_event=event_tags[k]))
        by_key[k]=estimates_by_c[0.]
    for arm in ARMS:
        for j in range(3):
            for t in range(1,13):
                a,b=by_key[(j,t,arm)],by_key[(j+1,t,arm)]
                ok=all(r[name] for r in (a,b) for name in ("point_valid","segment_valid"))
                dp=b["point_px"]-a["point_px"] if ok else np.nan
                dm=b["segment_px"]-a["segment_px"] if ok else np.nan
                stages.append(dict(arm=arm,transect_id=t,stage_a=j,stage_b=j+1,load_a_kN=LOADS[j],load_b_kN=LOADS[j+1],paired_valid=ok,
                                   point_increment_px=dp,segment_increment_px=dm,absolute_distortion_px=abs(dm-dp) if ok else np.nan,
                                   ratio=dm/dp if ok and abs(dp)>EPS else np.nan))
    return centres,comparisons,stages

def run(source,output,budget=60):
    if not 0<budget<=60: raise ValueError("budget must be in (0,60]")
    output.mkdir(parents=True,exist_ok=False)
    start,cpu=time.monotonic(),time.process_time()
    receipt=dict(experiment_id="S03-E021-D01",protocol="short-support-v1",execution="running",started_utc=datetime.now(timezone.utc).isoformat(),
                 hostname=socket.gethostname(),pid=os.getpid(),code_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                 git_status=subprocess.check_output(["git","status","--short"],text=True),source=str(source),budget_seconds=budget,
                 thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
                 input_files=[])
    try:
        receipt["input_files"]=[dict(name=n,bytes=(source/n).stat().st_size) for n in ("measurements.csv","adjacent_pairs.csv","curve_summaries.csv","t0_replay.csv","runtime_receipt.json")]
        groups,tags=load_snapshot(source)
        if max(time.monotonic()-start,time.process_time()-cpu)>=budget: raise TimeoutError("input budget")
        centres,comparisons,stages=calculate(groups,tags)
        if max(time.monotonic()-start,time.process_time()-cpu)>=budget: raise TimeoutError("calculation budget")
        if (len(centres),len(comparisons),len(stages))!=(864,96,72): raise ValueError("output coverage mismatch")
        for name,rows in (("centre_estimates.csv",centres),("sensitivity_comparison.csv",comparisons),("stage_changes.csv",stages)): write_csv(output/name,rows)
        summary=dict(experiment_id="S03-E021-D01",protocol="short-support-v1",support_span_px=4,support_positions=9,
                     centre_rows=864,sensitivity_rows=96,stage_rows=72,
                     centre_point_valid=sum(r["point_valid"] for r in centres),centre_segment_valid=sum(r["segment_valid"] for r in centres),
                     primary_original_H=paired_summary([r for r in comparisons if r["arm"]==ARMS[0]]),
                     by_arm=[dict(arm=arm,sensitivity=paired_summary([r for r in comparisons if r["arm"]==arm]),
                                  stage_retention=stage_summary([r for r in stages if r["arm"]==arm]),
                                  by_stage=[dict(load_kN=LOADS[j],**paired_summary([r for r in comparisons if r["arm"]==arm and r["stage_index"]==j])) for j in range(4)],
                                  by_support_event=[dict(event=event,**paired_summary([r for r in comparisons if r["arm"]==arm and r["support_event"]==event])) for event in (False,True)],
                                  by_transition=[dict(load_a_kN=LOADS[j],load_b_kN=LOADS[j+1],**stage_summary([r for r in stages if r["arm"]==arm and r["stage_a"]==j])) for j in range(3)]) for arm in ARMS],
                     physical_reference=False,new_forecast_scores=False,independent_units=1)
        (output/"summary.json").write_text(json.dumps(clean(summary),indent=2,allow_nan=False)+"\n")
        receipt.update(execution="succeeded",centre_rows=len(centres),sensitivity_rows=len(comparisons),stage_rows=len(stages))
    except Exception as exc:
        receipt.update(execution="stopped",error=repr(exc));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        if max(receipt["wall_seconds"],receipt["cpu_seconds"])>=budget: receipt["execution"]="budget_stopped"
        (output/"runtime_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        if receipt["execution"]=="budget_stopped": raise TimeoutError("CPU/wall budget")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();run(args.source,args.output)
