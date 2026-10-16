"""E032: fixed background-only positional stress sets, never error-selected."""
from __future__ import annotations
import argparse
import csv
import itertools
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
from d01_crack_profile_diagnostic import S, native_gray, sample_profile, measure, forecast
from md01_relative_stage_pilot import FILES, EXPECTED, now, save

PROTOCOL="md01-position-sensitivity-v1"
LABELS=("M","L1","R1","L2","R2")
FRACTIONS=(-1.,-.5,0.,.5,1.)


def old_paths(root):
    r=root/"runs"
    return dict(snapshot=r/"S03-E031-MD01-R001/predictions_saved_before_target.json",
                history=r/"S03-E031-MD01-R001/measurements.json",
                target=r/"S03-E031-MD01-R002/measurements.json",
                summary=r/"S03-E031-MD01-R002/summary.json",
                geometry=r/"S03-E031-MD01-R001/geometry_saved_before_measurement.json",
                history_profiles=r/"S03-E031-MD01-R001/profiles.npz",
                target_profiles=r/"S03-E031-MD01-R002/profiles.npz")


def metadata_lock(snapshot, target):
    """Positions depend on geometry/background ONLY, not any width/error field."""
    g=snapshot["geometry"]
    n=np.asarray(g["normal"],float)
    if n.shape!=(2,) or not np.isfinite(n).all() or abs(np.linalg.norm(n)-1)>1e-12:
        raise ValueError("invalid fixed unit normal")
    t=np.array([-n[1],n[0]])
    registrations=[r["registration"] for r in snapshot["history"]]+[target[0]["registration"]]
    if len(registrations)!=3: raise ValueError("three source registrations required")
    residuals={"27":{label:[0.,0.] for label in LABELS}}
    provenance=[]
    for stage,reg in zip((28,29),registrations[1:]):
        if not reg["valid"] or len(reg["patches"])!=4 or not all(p["valid"] for p in reg["patches"]):
            raise ValueError("expected the four previously accepted anchors, no reselection")
        residuals[str(stage)]={"M":[0.,0.]}
        for label,patch,expected_center in zip(LABELS[1:],reg["patches"],g["background_centers"]):
            if patch["center"]!=expected_center: raise ValueError("anchor identity/order changed")
            delta=np.array([patch["dx"]-reg["dx"],patch["dy"]-reg["dy"]])
            residuals[str(stage)][label]=delta.tolist()
            provenance.append(dict(stage=stage,label=label,center=patch["center"],residual_xy=delta.tolist(),
                                   normal_px=float(delta@n),tangent_px=float(delta@t)))
    rn=max(abs(r["normal_px"]) for r in provenance)
    rt=max(abs(r["tangent_px"]) for r in provenance)
    profiles=[];cache={}
    def pid(stage,offset):
        key=(stage,*map(float,offset))
        if key not in cache:
            name=f"P{len(profiles):03d}"
            cache[key]=name
            profiles.append(dict(id=name,stage=stage,offset_xy=list(key[1:]),
                                 offset_normal_px=float(np.asarray(offset)@n),
                                 offset_tangent_px=float(np.asarray(offset)@t)))
        return cache[key]
    cases=[]
    for i,fn in enumerate(FRACTIONS):
        for j,ft in enumerate(FRACTIONS):
            delta=fn*rn*n+ft*rt*t
            cases.append(dict(id=f"C{i}{j}",family="common",normal_fraction=fn,tangent_fraction=ft,
                              profile_ids=[pid(s,delta) for s in (27,28,29)],paired_anchor=False,
                              anchor28=None,anchor29=None))
    for a,b in itertools.product(LABELS,repeat=2):
        cases.append(dict(id=f"I_{a}_{b}",family="independent",normal_fraction=None,tangent_fraction=None,
                          profile_ids=[pid(27,[0.,0.]),pid(28,residuals["28"][a]),pid(29,residuals["29"][b])],
                          paired_anchor=a==b,anchor28=a,anchor29=b))
    return dict(protocol=PROTOCOL,role="viewed-development finite sensitivity, no error selection",
                geometry=g,normal=n.tolist(),tangent=t.tolist(),envelope_normal_px=rn,envelope_tangent_px=rt,
                registrations=registrations,residual_provenance=provenance,residual_xy=residuals,
                fractions=list(FRACTIONS),labels=list(LABELS),profiles=profiles,cases=cases,
                nominal_profile_ids=[pid(s,[0.,0.]) for s in (27,28,29)])


def comparison(widths):
    if len(widths)!=3: raise ValueError("exactly three stage widths required")
    if any(w is None or not np.isfinite(w) for w in widths):
        return dict(valid=False,reason="profile_missing",w27=widths[0],w28=widths[1],w29=widths[2],
                    persistence=None,secant=None,raw_secant=None,persistence_abs_error=None,
                    secant_abs_error=None,delta_abs_error=None)
    a,b,c=map(float,widths)
    p=float(forecast([a,b],[27,28],29,"persistence"))
    q=float(forecast([a,b],[27,28],29,"secant"))
    return dict(valid=True,reason="ok",w27=a,w28=b,w29=c,persistence=p,secant=q,raw_secant=2*b-a,
                persistence_abs_error=abs(p-c),secant_abs_error=abs(q-c),delta_abs_error=abs(q-c)-abs(p-c))


def summarize(rows):
    result={}
    for family in ("common","independent"):
        allrows=[r for r in rows if r["family"]==family]
        valid=[r for r in allrows if r["valid"]]
        ds=[r["delta_abs_error"] for r in valid]
        result[family]=dict(nominal=len(allrows),valid=len(valid),missing=len(allrows)-len(valid),
                           secant_better=sum(d < -1e-10 for d in ds),tie=sum(abs(d)<=1e-10 for d in ds),
                           persistence_better=sum(d > 1e-10 for d in ds),
                           min_delta=min(ds) if ds else None,max_delta=max(ds) if ds else None)
    return result


def write_rows(path,rows):
    with path.open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def execute(a):
    start,cpu=time.monotonic(),time.process_time()
    a.output.mkdir(parents=True,exist_ok=False)
    r=dict(protocol=PROTOCOL,execution="running",started_at_utc=now(),host=socket.gethostname(),
           pid=os.getpid(),runtime=sys.executable,command=sys.argv,
           commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
           dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
           lock=str(a.lock),source_root=str(a.old_root),source_scope="existing three images only")
    paths=old_paths(a.old_root)
    protected={p:p.read_bytes() for p in paths.values()}
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>110: raise TimeoutError("internal110s budget")
    try:
        lock=json.loads(a.lock.read_text())
        snapshot=json.loads(protected[paths["snapshot"]]);target=json.loads(protected[paths["target"]])
        if lock["protocol"]!=PROTOCOL or lock!=metadata_lock(snapshot,target):
            raise ValueError("background-only position lock changed")
        save(a.output/"input_position_lock.json",lock)
        arrays={"offsets":S};measurements=[];sources=[]
        for stage,filename,(expected_size,_) in zip((27,28,29),FILES,EXPECTED):
            path=a.old_root/"source"/filename
            if path.stat().st_size!=expected_size: raise ValueError("source size differs from E031 identity")
            image=native_gray(path)
            if list(image.shape)!=lock["geometry"]["native_shape"]: raise ValueError("native shape mismatch")
            sources.append(dict(stage=stage,path=str(path),bytes=expected_size,shape=list(image.shape)))
            reg=lock["registrations"][stage-27]
            H=np.array([[1,0,-reg["dx"]],[0,1,-reg["dy"]],[0,0,1]],float)
            for spec in lock["profiles"]:
                if spec["stage"]!=stage: continue
                budget()
                center=np.asarray(lock["geometry"]["center"])+np.asarray(spec["offset_xy"])
                try:
                    prof=sample_profile(image,H,center,lock["normal"])
                    m,d,bg=measure(prof)
                    arrays.update({spec["id"]+"_profile":prof,spec["id"]+"_deficit":d,spec["id"]+"_background":bg})
                except ValueError as error:
                    if str(error)!="profile support leaves source image": raise
                    m=dict(valid=False,reason="sample_out_of_bounds",fwhm_native_px=None)
                measurements.append(dict(**spec,center_first_xy=center.tolist(),measurement=m))
            del image
        byid={r["id"]:r for r in measurements}
        nominal=[byid[p] for p in lock["nominal_profile_ids"]]
        baseline=comparison([r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in nominal])
        old_records=snapshot["history"]+target
        old_summary=json.loads(protected[paths["summary"]])
        for row,old in zip(nominal,old_records):
            if not row["measurement"]["valid"] or abs(row["measurement"]["fwhm_native_px"]-old["measurement"]["fwhm_native_px"])>1e-8:
                raise ValueError("E031 nominal width reproduction mismatch")
        for field,old_field in (("persistence_abs_error","persistence_abs_error_px"),("secant_abs_error","secant_abs_error_px"),("delta_abs_error","delta_abs_error_px")):
            if abs(baseline[field]-old_summary[old_field])>1e-8: raise ValueError("E031 score reproduction mismatch")
        cases=[]
        for spec in lock["cases"]:
            rows=[byid[p] for p in spec["profile_ids"]]
            c=dict(**spec,**comparison([r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in rows]))
            c.update(secant_prediction_change=None,target_change=None,signed_secant_error_change=None,
                     frozen_predictions_delta_abs_error=None)
            if c["valid"]:
                c["secant_prediction_change"]=c["secant"]-baseline["secant"]
                c["target_change"]=c["w29"]-baseline["w29"]
                c["signed_secant_error_change"]=c["secant_prediction_change"]-c["target_change"]
                c["frozen_predictions_delta_abs_error"]=abs(baseline["secant"]-c["w29"])-abs(baseline["persistence"]-c["w29"])
            cases.append(c)
        budget()
        unchanged=all(p.read_bytes()==data for p,data in protected.items())
        if not unchanged: raise ValueError("Protected E031 result content changed")
        summary=dict(protocol=PROTOCOL,baseline=baseline,by_family=summarize(cases),
                     unique_profiles=len(measurements),valid_profiles=sum(r["measurement"]["valid"] for r in measurements),
                     independent_cases=1,scenario_count=len(cases),position_transfer_assumed=True,
                     old_scores_byte_unchanged=unchanged)
        save(a.output/"measurements.json",measurements);save(a.output/"summary.json",summary)
        save(a.output/"scenarios.json",cases);np.savez_compressed(a.output/"profiles.npz",**arrays)
        write_rows(a.output/"scenarios.csv",cases)
        write_rows(a.output/"profile_measurements.csv",[dict(id=x["id"],stage=x["stage"],
                   normal_px=x["offset_normal_px"],tangent_px=x["offset_tangent_px"],
                   width_px=x["measurement"]["fwhm_native_px"],valid=x["measurement"]["valid"],
                   reason=x["measurement"]["reason"]) for x in measurements])
        r.update(execution="succeeded",retrieval="verified_local",sources=sources,
                 protected_old_files=[str(p) for p in paths.values()],old_scores_byte_unchanged=True)
        print(json.dumps(summary,indent=2))
    except Exception as error:
        r.update(execution="failed",error=repr(error));raise
    finally:
        r.update(ended_at_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        save(a.output/"run_receipt.json",r)


def self_test():
    g=dict(normal=[1.,0.],center=[100.,100.],background_centers=[[70,80],[130,80],[70,120],[130,120]])
    def reg(scale):
        return dict(valid=True,dx=10.,dy=20.,patches=[dict(valid=True,center=c,dx=10.+v*scale,dy=20.+w*scale)
                      for c,(v,w) in zip(g["background_centers"],[(-2,1),(2,-1),(-3,2),(3,-2)])])
    snap=dict(geometry=g,history=[dict(registration=dict(dx=0.,dy=0.)),dict(registration=reg(1))])
    target=[dict(registration=reg(2))]
    lock=metadata_lock(snap,target)
    assert json.loads(json.dumps(lock))==lock
    assert lock["envelope_normal_px"]==6 and lock["envelope_tangent_px"]==4
    assert len(lock["cases"])==50 and len({c["id"] for c in lock["cases"]})==50
    assert all(c["profile_ids"][0]==lock["nominal_profile_ids"][0] for c in lock["cases"] if c["family"]=="independent")
    other=dict(snap,forbidden_width=999,forbidden_error=-999)
    assert metadata_lock(other,target)==lock
    assert comparison([10.,14.,19.])["delta_abs_error"]==-4
    assert comparison([10.,14.,14.])["delta_abs_error"]==4
    assert not comparison([10.,None,14.])["valid"]
    assert comparison([100.,119.,125.])["secant"]==120
    rows=[dict(family="common",**comparison([10.,14.,19.])),dict(family="independent",**comparison([10.,None,19.]))]
    assert summarize(rows)["common"]["secant_better"]==1 and summarize(rows)["independent"]["missing"]==1
    from independent_d01_halfdepth import measure as independent_measure
    for sigma in (1.5,3.,8.):
        profile=180+.02*S-100*np.exp(-S*S/(2*sigma*sigma))
        assert abs(measure(profile)[0]["fwhm_native_px"]-independent_measure(S,profile)["width_px"])<1e-10
    print("Metadata-only locking, common/independent sets, widths/errors/missingness/clipping, independent half-depth: passed")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("prepare","run","self-test"))
    p.add_argument("--old-root",type=Path);p.add_argument("--output",type=Path);p.add_argument("--lock",type=Path)
    a=p.parse_args()
    if a.phase=="self-test": self_test()
    elif a.phase=="prepare":
        paths=old_paths(a.old_root)
        lock=metadata_lock(json.loads(paths["snapshot"].read_text()),json.loads(paths["target"].read_text()))
        save(a.output,lock)
        print(json.dumps({k:lock[k] for k in ("envelope_normal_px","envelope_tangent_px")},indent=2))
        print("profiles",len(lock["profiles"]),"scenarios",len(lock["cases"]))
    else: execute(a)
