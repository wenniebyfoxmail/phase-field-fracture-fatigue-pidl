"""E035 fixed background-only stress sets; old code and scores untouched."""
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
from d01_crack_profile_diagnostic import S,native_gray,sample_profile,measure
from md01_fixed_24_26 import SOURCE,FILES,verified,prediction,now,save

PROTOCOL="md01-24-26-position-v1"
LABELS=("M","L1","R1","L2","R2")
FRACTIONS=(-1.,-.5,0.,.5,1.)
OLD=SOURCE.parent
HISTORY=OLD/"runs/S03-E034-MD01-R005"
TARGET=OLD/"runs/S03-E034-MD01-R006"


def paths():
    return dict(snapshot=HISTORY/"predictions_saved_before_target.json",
                history=HISTORY/"history_snapshot.json",history_profiles=HISTORY/"profiles.npz",
                geometry=HISTORY/"geometry_saved_before_formal_measurement.json",
                target=TARGET/"target_measurement.json",target_profiles=TARGET/"profiles.npz",
                summary=TARGET/"summary.json",
                original_summary=OLD/"runs/S03-E034-MD01-R002/summary.json",
                original_snapshot=OLD/"runs/S03-E034-MD01-R002/predictions_saved_before_target.json")


def build_lock(h,target):
    """Only geometry and background fields influence positions; no width access."""
    g=h["geometry"]; n=np.array(g["normal"],float);t=np.array([-n[1],n[0]])
    if n.shape!=(2,) or not np.isfinite(n).all() or abs(np.linalg.norm(n)-1)>1e-12:
        raise ValueError("Fixed unit normal required")
    regs=[r["registration"] for r in h["history"]]+[target["registration"]]
    residuals={"24":{label:[0.,0.] for label in LABELS}}; provenance=[]
    for stage,reg in zip((25,26),regs[1:]):
        if not reg["valid"] or len(reg["patches"])!=4 or not all(p["valid"] for p in reg["patches"]):
            raise ValueError("Four original accepted anchors required")
        residuals[str(stage)]={"M":[0.,0.]}
        for label,p,center in zip(LABELS[1:],reg["patches"],g["background_centers"]):
            if p["center"]!=center:raise ValueError("Anchor identity/order mismatch")
            d=np.array([p["dx"]-reg["dx"],p["dy"]-reg["dy"]])
            residuals[str(stage)][label]=d.tolist()
            provenance.append(dict(stage=stage,label=label,center=center,residual_xy=d.tolist(),
                                   normal_px=float(d@n),tangent_px=float(d@t)))
    rn=max(abs(r["normal_px"]) for r in provenance);rt=max(abs(r["tangent_px"]) for r in provenance)
    profiles=[];cache={}
    def pid(stage,d):
        key=(stage,*map(float,d))
        if key not in cache:
            name=f"P{len(profiles):03d}";cache[key]=name
            profiles.append(dict(id=name,stage=stage,offset_xy=list(key[1:]),
                                 offset_normal_px=float(np.array(d)@n),offset_tangent_px=float(np.array(d)@t)))
        return cache[key]
    cases=[]
    for i,fn in enumerate(FRACTIONS):
        for j,ft in enumerate(FRACTIONS):
            d=fn*rn*n+ft*rt*t
            cases.append(dict(id=f"C{i}{j}",family="common",normal_fraction=fn,tangent_fraction=ft,
                              anchor25=None,anchor26=None,paired_anchor=False,
                              profile_ids=[pid(s,d) for s in (24,25,26)]))
    for a,b in itertools.product(LABELS,repeat=2):
        cases.append(dict(id=f"I_{a}_{b}",family="independent",normal_fraction=None,tangent_fraction=None,
                          anchor25=a,anchor26=b,paired_anchor=a==b,
                          profile_ids=[pid(24,[0.,0.]),pid(25,residuals["25"][a]),pid(26,residuals["26"][b])]))
    return dict(protocol=PROTOCOL,role="one viewed development query, finite stress sets",
                geometry=g,normal=n.tolist(),tangent=t.tolist(),registrations=regs,
                envelope_normal_px=rn,envelope_tangent_px=rt,residual_provenance=provenance,
                residual_xy=residuals,fractions=list(FRACTIONS),labels=list(LABELS),profiles=profiles,cases=cases,
                nominal_profile_ids=[pid(s,[0.,0.]) for s in (24,25,26)])


def comparison(widths):
    out=dict(w24=widths[0],w25=widths[1],w26=widths[2],persistence=None,secant=None,
             raw_secant=None,persistence_abs_error=None,secant_abs_error=None,delta_abs_error=None,
             valid=False,reason="profile_missing")
    if any(w is None or not np.isfinite(w) for w in widths):return out
    a,b,c=map(float,widths);p=prediction([a,b]); arms=p["arms"]
    keep=arms["persistence"]["prediction_px"];trend=arms["stage_trend"]["prediction_px"]
    out.update(valid=True,reason="ok",persistence=keep,secant=trend,raw_secant=2*b-a,
               persistence_abs_error=abs(keep-c),secant_abs_error=abs(trend-c),delta_abs_error=abs(trend-c)-abs(keep-c))
    return out


def summarize(rows):
    out={}
    for family in ("common","independent"):
        rr=[r for r in rows if r["family"]==family];ds=[r["delta_abs_error"] for r in rr if r["valid"]]
        out[family]=dict(nominal=len(rr),valid=len(ds),missing=len(rr)-len(ds),
                         secant_better=sum(d<0 for d in ds),tie=sum(d==0 for d in ds),
                         persistence_better=sum(d>0 for d in ds),
                         min_delta=min(ds) if ds else None,max_delta=max(ds) if ds else None)
    return out


def write_rows(path,rows):
    with path.open("x",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)


def execute(a):
    start,cpu=time.monotonic(),time.process_time();a.output.mkdir(parents=True,exist_ok=False)
    protected={p:p.read_bytes() for p in paths().values()}
    receipt=dict(protocol=PROTOCOL,execution="running",started_at_utc=now(),host=socket.gethostname(),pid=os.getpid(),
                 runtime=sys.executable,command=sys.argv,lock=str(a.lock),source_scope="existing394/397/400 only",
                 commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                 dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines())
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>110:raise TimeoutError("Internal110s budget")
    try:
        p=paths();h=json.loads(protected[p["snapshot"]]);target=json.loads(protected[p["target"]])
        lock=json.loads(a.lock.read_text())
        if lock!=build_lock(h,target):raise ValueError("Background-only lock mismatch")
        save(a.output/"input_position_lock.json",lock)
        arrays={"offsets":S};measurements=[];identities=[]
        for i,(stage,name) in enumerate(zip((24,25,26),FILES)):
            identities.append(verified(i));image=native_gray(SOURCE/name)
            if list(image.shape)!=lock["geometry"]["native_shape"]:raise ValueError("Native shape mismatch")
            reg=lock["registrations"][i];H=np.array([[1,0,-reg["dx"]],[0,1,-reg["dy"]],[0,0,1]],float)
            for spec in lock["profiles"]:
                if spec["stage"]!=stage:continue
                budget();center=np.array(lock["geometry"]["center"])+np.array(spec["offset_xy"])
                try:
                    profile=sample_profile(image,H,center,lock["normal"]);m,d,bg=measure(profile)
                    arrays.update({spec["id"]+"_profile":profile,spec["id"]+"_deficit":d,spec["id"]+"_background":bg})
                except ValueError as error:
                    if str(error)!="profile support leaves source image":raise
                    m=dict(valid=False,reason="sample_out_of_bounds",fwhm_native_px=None)
                measurements.append(dict(**spec,center_first_xy=center.tolist(),measurement=m))
            del image
        byid={r["id"]:r for r in measurements}
        nominal=[byid[x] for x in lock["nominal_profile_ids"]]
        baseline=comparison([r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in nominal])
        for row,old in zip(nominal,h["history"]+[target]):
            if not row["measurement"]["valid"] or abs(row["measurement"]["fwhm_native_px"]-old["measurement"]["fwhm_native_px"])>1e-8:
                raise ValueError("E034 nominal width mismatch")
        with np.load(p["history_profiles"]) as hp,np.load(p["target_profiles"]) as tp:
            for stage,pid in zip((24,25,26),lock["nominal_profile_ids"]):
                old=hp if stage<26 else tp
                for field in ("profile","background","deficit"):
                    if not np.allclose(arrays[pid+"_"+field],old[f"s{stage}_{field}"],rtol=0,atol=1e-8):
                        raise ValueError("E034 nominal array mismatch")
        old_summary=json.loads(protected[p["summary"]])
        for new,old_arm in (("persistence","persistence"),("secant","stage_trend")):
            if abs(baseline[new]-h["predictions"]["arms"][old_arm]["prediction_px"])>1e-8:raise ValueError("E034 prediction mismatch")
            if abs(baseline[new+"_abs_error"]-old_summary["methods"][old_arm]["abs_error_px"])>1e-8:raise ValueError("E034 error mismatch")
        if abs(baseline["delta_abs_error"]-old_summary["delta_abs_error_px"])>1e-8:raise ValueError("E034 delta mismatch")
        cases=[]
        for spec in lock["cases"]:
            rr=[byid[x] for x in spec["profile_ids"]]
            c=dict(**spec,**comparison([r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in rr]))
            c.update(secant_prediction_change=None,target_change=None,signed_secant_error_change=None,frozen_predictions_delta_abs_error=None)
            if c["valid"]:
                c["secant_prediction_change"]=c["secant"]-baseline["secant"]
                c["target_change"]=c["w26"]-baseline["w26"]
                c["signed_secant_error_change"]=c["secant_prediction_change"]-c["target_change"]
                c["frozen_predictions_delta_abs_error"]=abs(baseline["secant"]-c["w26"])-abs(baseline["persistence"]-c["w26"])
            cases.append(c)
        budget()
        if not all(p.read_bytes()==data for p,data in protected.items()):raise ValueError("Protected E034 bytes changed")
        summary=dict(protocol=PROTOCOL,baseline=baseline,by_family=summarize(cases),unique_profiles=len(measurements),
                     valid_profiles=sum(r["measurement"]["valid"] for r in measurements),independent_cases=1,
                     scenario_count=len(cases),position_transfer_assumed=True,old_scores_byte_unchanged=True)
        for name,value in (("measurements.json",measurements),("scenarios.json",cases),("summary.json",summary)):
            save(a.output/name,value)
        np.savez_compressed(a.output/"profiles.npz",**arrays);write_rows(a.output/"scenarios.csv",cases)
        write_rows(a.output/"profile_measurements.csv",[dict(id=r["id"],stage=r["stage"],normal_px=r["offset_normal_px"],
                   tangent_px=r["offset_tangent_px"],width_px=r["measurement"]["fwhm_native_px"],valid=r["measurement"]["valid"],reason=r["measurement"]["reason"]) for r in measurements])
        receipt.update(execution="succeeded",retrieval="verified_local",source_identities=identities,
                       protected_old_files=[str(p) for p in protected],old_scores_byte_unchanged=True)
        print(json.dumps(summary,indent=2))
    except Exception as error:receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_at_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        save(a.output/"run_receipt.json",receipt)


def self_test():
    g=dict(normal=[1.,0.],center=[100.,100.],background_centers=[[70,80],[130,80],[70,120],[130,120]])
    def reg(scale):return dict(valid=True,dx=10.,dy=20.,patches=[dict(valid=True,center=c,dx=10.+v*scale,dy=20.+w*scale)
        for c,(v,w) in zip(g["background_centers"],[(-2,1),(2,-1),(-3,2),(3,-2)])])
    h=dict(geometry=g,history=[dict(registration=dict(dx=0.,dy=0.)),dict(registration=reg(1))]);target=dict(registration=reg(2))
    lock=build_lock(h,target);assert lock["envelope_normal_px"]==6 and lock["envelope_tangent_px"]==4
    assert len(lock["cases"])==50 and len(lock["profiles"])==83 and json.loads(json.dumps(lock))==lock
    assert build_lock(dict(h,width=-999,error=999),dict(target,width=999,error=-999))==lock
    assert all(c["profile_ids"][0]==lock["nominal_profile_ids"][0] for c in lock["cases"] if c["family"]=="independent")
    assert comparison([10,14,19])["delta_abs_error"]==-4
    assert comparison([10,14,14])["delta_abs_error"]==4
    assert not comparison([10,None,14])["valid"]
    assert comparison([100,119,125])["secant"]==120
    from independent_d01_halfdepth import measure as independent
    for sigma in (1.5,3.,8.):
        profile=180+.02*S-100*np.exp(-S*S/(2*sigma*sigma))
        assert abs(measure(profile)[0]["fwhm_native_px"]-independent(S,profile)["width_px"])<1e-10
    print("Background-only lock,83 profiles/50cases,stage roles,sign/missingness/clipping,half-depth: passed")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("prepare","run","self-test"))
    p.add_argument("--output",type=Path);p.add_argument("--lock",type=Path);a=p.parse_args()
    if a.phase=="self-test":self_test()
    elif a.phase=="prepare":
        lock=build_lock(json.loads(paths()["snapshot"].read_text()),json.loads(paths()["target"].read_text()))
        save(a.output,lock)
        print(json.dumps({k:lock[k] for k in ("envelope_normal_px","envelope_tangent_px")},indent=2))
        print("profiles",len(lock["profiles"]),"cases",len(lock["cases"]))
    else:execute(a)
