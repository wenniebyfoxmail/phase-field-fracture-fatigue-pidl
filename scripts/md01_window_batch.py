"""E036 four locked windows; history batch must precede every target."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import numpy as np
from PIL import Image, ImageOps
from d01_crack_profile_diagnostic import S,native_gray,sample_profile,measure
from md01_early_relative import now,save,prediction,unavailable,registration_safe,profile_safe,self_test

PROTOCOL="md01-four-windows-v1"
ROOT=Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive")
EXP=ROOT/"experiments/S03-E036-MD01"
SOURCE=EXP/"raw_images"
META=ROOT/"open_data/md01_tack_metadata_20261016"


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lock(path):
    lock=json.loads(path.read_text())
    if lock["protocol"]!=PROTOCOL or [w["stages"] for w in lock["windows"]]!=[list(range(s,s+3)) for s in (12,15,18,21)]:
        raise ValueError("Protocol/window mismatch")
    for name,digest in lock["metadata_sha256"].items():
        if sha(META/name)!=digest:raise ValueError("Metadata changed")
    old_guard(lock)
    return lock


def old_guard(lock):
    if not all(sha(p)==v for p,v in lock["protected_old_hashes"].items()):raise ValueError("Protected old payload changed")


def verify(f):
    p=SOURCE/f["filename"]
    if p.stat().st_size!=f["size"] or sha(p)!=f["content_details"]["sha256_hash"]:raise ValueError("Source identity conflict")
    return dict(filename=f["filename"],step=f["step"],file_id=f["id"],bytes=p.stat().st_size,sha256=sha(p))


def acquire(f):
    p=SOURCE/f["filename"]
    if p.exists():raise ValueError("Refuse source overwrite/retry")
    url=f"https://data.mendeley.com/public-files/datasets/dns97tfdjn/files/{f['id']}/file_downloaded"
    if url!=f["content_details"]["download_url"]:raise ValueError("Source URL conflict")
    subprocess.run(["curl","--fail","--location","--max-time","60","--silent","--show-error","--output",str(p),url],check=True,timeout=65)
    return dict(**verify(f),acquired_at_utc=now())


def classify(d1,d2):
    if d1*d2<0:return "direction_reversal"
    if d1>0 and 0<=d2<d1:return "growth_deceleration"
    if d1>0 and d2>=d1:return "growth_no_deceleration"
    if d1==0:return "flat_history"
    return "other"


def score(h,target=None):
    widths=[r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in h["history"]]
    ref=target["measurement"] if target else None
    r=bool(ref["valid"]) if ref else None
    common=bool(h["E"] and r and all(v["success"] for v in h["predictions"]["arms"].values()))
    out=dict(case=h["case"],stages=h["stages"],E=h["E"],R=r,target_attempted=target is not None,
             common_scored=int(common),w1=widths[0],w2=widths[1],w3=ref["fwhm_native_px"] if r else None,
             delta_abs_error_px=None,gain_px=None,d1=None,d2=None,stratum=None,methods={},
             reason="ok" if common else (ref["reason"] if target else "history_ineligible" if not h["E"] else "awaiting_target"))
    for arm,value in h["predictions"]["arms"].items():
        scored=bool(h["E"] and r and value["success"])
        out["methods"][arm]=dict(value,scored=scored,abs_error_px=abs(value["prediction_px"]-out["w3"]) if scored else None)
    if common:
        out.update(delta_abs_error_px=out["methods"]["stage_trend"]["abs_error_px"]-out["methods"]["persistence"]["abs_error_px"])
        out.update(gain_px=-out["delta_abs_error_px"],d1=out["w2"]-out["w1"],d2=out["w3"]-out["w2"])
        out["stratum"]=classify(out["d1"],out["d2"])
    return out


def summarize(rows):
    valid=[r for r in rows if r["common_scored"]]
    d=[r["delta_abs_error_px"] for r in valid]
    return dict(protocol=PROTOCOL,opportunities=4,histories_eligible=sum(r["E"] for r in rows),
                targets_attempted=sum(r["target_attempted"] for r in rows),common_scored=len(d),coverage=len(d)/4,
                conditional_common_coverage=len(d)/sum(r["E"] for r in rows) if any(r["E"] for r in rows) else None,
                mean_delta_abs_error_px=float(np.mean(d)) if d else None,
                mean_abs_error_px={a:float(np.mean([r["methods"][a]["abs_error_px"] for r in valid])) if valid else None for a in ("persistence","stage_trend")},
                trend_better=sum(x<0 for x in d),tie=sum(x==0 for x in d),persistence_better=sum(x>0 for x in d),
                missing=4-len(d),strata={s:sum(r["stratum"]==s for r in valid) for s in ("direction_reversal","growth_deceleration","growth_no_deceleration","flat_history","other")},
                unit="per-window native first-history pixels",physical_units=1,independent_specimen_validation=False)


def histories(a,lock,budget):
    if any((SOURCE/w["files"][2]["filename"]).exists() for w in lock["windows"]):raise ValueError("Any target present before all histories")
    cfgs=json.loads(a.geometry.read_text());rows=[]
    if set(cfgs)!=set(w["id"] for w in lock["windows"]):raise ValueError("Need exactly four first-image configurations")
    for w in lock["windows"]:
        budget();out=a.output/w["id"];out.mkdir();cfg=cfgs[w["id"]];arrays={};records=[]
        ids=[verify(f) for f in w["files"][:2]]
        if cfg.get("no_identifiable_trace"):
            geom=cfg
            records=[dict(step=f["step"],filename=f["filename"],attempted=False,registration=dict(valid=None,reason="profile_not_defined"),measurement=unavailable("no_identifiable_historical_crack_trace")) for f in w["files"][:2]]
        else:
            if (cfg["reference_image"]!=w["files"][0]["filename"] or cfg["patch_size"]!=61 or cfg["translation_radius"]!=80
                or cfg["correlation_min"]!=.6 or cfg["required_background_patches"]!=3 or len(cfg["background_centers"])!=4
                or not np.isclose(np.linalg.norm(cfg["normal"]),1,atol=1e-12)):
                raise ValueError("Fixed first-image geometry/settings required")
            first,second=(native_gray(SOURCE/f["filename"]) for f in w["files"][:2])
            if list(first.shape)!=cfg["native_shape"]:raise ValueError("First image shape mismatch")
            try:shift=measure(sample_profile(first,np.eye(3),cfg["rough_center"],cfg["normal"]))[0]["peak_offset_native_px"]
            except ValueError as error:
                if str(error)!="profile support leaves source image":raise
                shift=0.
            geom=dict(cfg,center=(np.array(cfg["rough_center"])+shift*np.array(cfg["normal"])).tolist(),refinement_native_px=float(shift))
            save(out/"geometry_saved_before_formal_measurement.json",geom)
            regs=[dict(valid=True,reason="first_image",dx=0.,dy=0.,patches=[]),registration_safe(first,second,cfg)]
            for im,f,reg in zip((first,second),w["files"][:2],regs):
                found,data=profile_safe(im,geom,reg)
                records.append(dict(step=f["step"],filename=f["filename"],attempted=True,registration=reg,measurement=found))
                if data is not None:arrays.update({f"s{f['step']}_{k}":v for k,v in data.items()})
            del first,second
        pred=prediction([r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in records])
        h=dict(protocol=PROTOCOL,case=w["id"],stages=w["stages"],geometry=geom,history=records,predictions=pred,E=pred["E"],
               source_identities=ids,saved_at_utc=now(),target_file_present_at_save=False)
        save(out/"history_snapshot.json",h);save(out/"predictions_saved_before_target.json",h)
        np.savez_compressed(out/"profiles.npz",offsets=S,**arrays);rows.append(score(h))
        print(w["id"],"history E",h["E"],flush=True)
    budget();save(a.output/"histories_closed.json",dict(protocol=PROTOCOL,closed_at_utc=now(),all_four_closed=True,cases=rows,
         target_files_absent=all(not (SOURCE/w["files"][2]["filename"]).exists() for w in lock["windows"])))


def targets(a,lock,budget):
    closure=json.loads((a.history/"histories_closed.json").read_text())
    if closure["protocol"]!=PROTOCOL or not closure["all_four_closed"] or not closure["target_files_absent"]:raise ValueError("Closed batch required")
    frozen={p:p.read_bytes() for p in a.history.rglob("*") if p.is_file()};rows=[];ids=[]
    for w in lock["windows"]:
        budget();out=a.output/w["id"];out.mkdir()
        h=json.loads((a.history/w["id"]/"predictions_saved_before_target.json").read_text())
        if h["protocol"]!=PROTOCOL or h["case"]!=w["id"] or h["stages"]!=w["stages"] or h["target_file_present_at_save"]:raise ValueError("History identity mismatch")
        if not h["E"]:
            if (SOURCE/w["files"][2]["filename"]).exists():raise ValueError("Ineligible target present")
            row=score(h)
        else:
            ids.append(acquire(w["files"][2]));budget()
            first,target=(native_gray(SOURCE/f["filename"]) for f in (w["files"][0],w["files"][2]))
            prev=h["history"][-1]["registration"]
            reg=registration_safe(first,target,h["geometry"],seed=(prev["dx"],prev["dy"]))
            found,data=profile_safe(target,h["geometry"],reg)
            ref=dict(step=w["stages"][2],filename=w["files"][2]["filename"],attempted=True,measurement=found,registration=reg,
                     acquired_after_all_histories=True,measured_at_utc=now())
            save(out/"target_measurement.json",ref)
            if data is not None:np.savez_compressed(out/"profiles.npz",offsets=S,**{f"s{w['stages'][2]}_{k}":v for k,v in data.items()})
            row=score(h,ref);del first,target
        save(out/"summary.json",row);rows.append(row);print(w["id"],row["reason"],"gain",row["gain_px"],flush=True)
    budget()
    if any(p.read_bytes()!=v for p,v in frozen.items()):raise ValueError("Historical payload changed")
    save(a.output/"cases.json",rows);save(a.output/"summary.json",summarize(rows));save(a.output/"source_identities.json",ids)
    flat=[{k:r[k] for k in ("case","stages","E","R","target_attempted","common_scored","w1","w2","w3","d1","d2","stratum","gain_px","delta_abs_error_px","reason")}|{a0+"_"+k:r["methods"][a0][k] for a0 in ("persistence","stage_trend") for k in ("prediction_px","abs_error_px")} for r in rows]
    with (a.output/"cases.csv").open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(flat[0]),lineterminator="\n");writer.writeheader();writer.writerows(flat)
    print(json.dumps(summarize(rows),indent=2))


def execute(a):
    lock=load_lock(a.lock);start=time.monotonic();cpu=time.process_time();a.output.mkdir(parents=True,exist_ok=False);SOURCE.mkdir(parents=True,exist_ok=True)
    receipt=dict(protocol=PROTOCOL,phase=a.phase,started_at_utc=now(),host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,
      command=sys.argv,commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
      execution="running",lock_sha256=sha(a.lock))
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>(590 if a.phase=="acquire-history" else 110):raise TimeoutError("Phase budget")
    try:
        if a.phase=="acquire-history":
            if any((SOURCE/f["filename"]).exists() for w in lock["windows"] for f in w["files"]):raise ValueError("Source already present")
            ids=[]
            for w in lock["windows"]:
                for f in w["files"][:2]:budget();ids.append(acquire(f));print("acquired",f["filename"],flush=True)
                with Image.open(SOURCE/w["files"][0]["filename"]) as raw:
                    im=ImageOps.exif_transpose(raw).convert("RGB");preview=im.copy();preview.thumbnail((1500,1000));preview.save(a.output/(w["id"]+"_first_preview.png"),dpi=(300,300))
                    crop=im.crop((3800,900,4800,3500));crop.thumbnail((700,1820));crop.save(a.output/(w["id"]+"_first_crop.png"),dpi=(300,300))
            save(a.output/"source_identities.json",ids)
        elif a.phase=="history":histories(a,lock,budget)
        else:targets(a,lock,budget)
        old_guard(lock);receipt.update(execution="succeeded",retrieval="verified_local",protected_old_hashes_unchanged=True)
    except Exception as error:receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_at_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu);save(a.output/"run_receipt.json",receipt)


def tests():
    self_test()
    assert classify(5,2)=="growth_deceleration" and classify(5,-2)=="direction_reversal" and classify(5,6)=="growth_no_deceleration"
    assert classify(5,0)=="growth_deceleration" and classify(0,0)=="flat_history" and classify(-2,-3)=="other"
    h=dict(case="fake",stages=[12,13,14],E=True,history=[dict(measurement=dict(valid=True,fwhm_native_px=w)) for w in (10.,15.)],predictions=prediction([10.,15.]))
    r=score(h,dict(measurement=dict(valid=True,fwhm_native_px=17.)))
    assert r["gain_px"]==-1 and r["stratum"]=="growth_deceleration" and r["common_scored"]==1
    r=score(h,dict(measurement=dict(valid=False,reason="low_contrast",fwhm_native_px=None)))
    assert r["gain_px"] is None and r["R"] is False and r["common_scored"]==0
    assert summarize([r]*4)["coverage"]==0 and summarize([r]*4)["mean_delta_abs_error_px"] is None
    print("E036 formulas,strata,missingness,coverage and original half-depth: passed")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("self-test","acquire-history","history","target"))
    for k in ("lock","geometry","history","output"):p.add_argument("--"+k,type=Path)
    a=p.parse_args()
    if a.phase=="self-test":tests()
    else:execute(a)
