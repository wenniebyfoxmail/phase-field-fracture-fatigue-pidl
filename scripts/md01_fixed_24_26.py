"""E034 exact scope; reuse unchanged metrology, with stage-typed history saves."""
import argparse
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
from d01_crack_profile_diagnostic import S, native_gray, sample_profile, measure
from md01_early_relative import (save, now, prediction, unavailable, registration_safe,
                                 profile_safe, self_test)

PROTOCOL="relative-stage-24-26-v1.1"
FILES=("IMG_0394.JPG","IMG_0397.JPG","IMG_0400.JPG")
IDS=("dc36397c-859e-491b-9310-587730d52c56","b6fc372e-0b53-4e98-af71-6c550d0675d3",
     "79dbc65d-89a0-4e1d-8b4b-6c2999f6741e")
BASE=Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive")
SOURCE=BASE/"experiments/S03-E034-MD01/raw_images"
METADATA=BASE/"open_data/md01_tack_metadata_20261016/fixed_camera_file_metadata.json"


def official(i):
    rows=[r for r in json.loads(METADATA.read_text()) if r["filename"]==FILES[i] and r["id"]==IDS[i]]
    if len(rows)!=1: raise ValueError("Nonunique official identity")
    return rows[0]


def verified(i):
    p=SOURCE/FILES[i]; row=official(i)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if p.stat().st_size!=row["size"] or digest!=row["content_details"]["sha256_hash"]:
        raise ValueError("Source identity conflict")
    return dict(filename=FILES[i],file_id=IDS[i],bytes=p.stat().st_size,sha256=digest)


def acquire(i):
    p=SOURCE/FILES[i]
    if p.exists(): raise ValueError("Refuse source overwrite")
    url=f"https://data.mendeley.com/public-files/datasets/dns97tfdjn/files/{IDS[i]}/file_downloaded"
    if official(i)["content_details"]["download_url"]!=url: raise ValueError("URL conflict")
    subprocess.run(["curl","--fail","--location","--max-time","60","--silent","--show-error",
                    "--output",str(p),url],check=True,timeout=65)
    return dict(**verified(i),acquired_at_utc=now())


def summary(snapshot, target=None):
    pred=snapshot["predictions"]
    r=bool(target["measurement"]["valid"]) if target else None
    width=target["measurement"]["fwhm_native_px"] if r else None
    both=bool(snapshot["E"] and r and all(v["success"] for v in pred["arms"].values()))
    result=dict(protocol=PROTOCOL,E=snapshot["E"],R=r,target_attempted=target is not None,
                unit="native_step24_reference_px",opportunities=1,common_scored=int(both),
                coverage=int(both),conditional_common_coverage=int(both) if snapshot["E"] and target else None,
                target_width_px=width,delta_abs_error_px=None,methods={})
    for arm,value in pred["arms"].items():
        scored=bool(snapshot["E"] and r and value["success"])
        result["methods"][arm]=dict(value,scored=scored,
                   abs_error_px=abs(value["prediction_px"]-width) if scored else None)
    if both: result["delta_abs_error_px"]=(result["methods"]["stage_trend"]["abs_error_px"]-
                                          result["methods"]["persistence"]["abs_error_px"])
    return result


def execute(a):
    start,cpu=time.monotonic(),time.process_time()
    a.output.mkdir(parents=True,exist_ok=False); SOURCE.mkdir(parents=True,exist_ok=True)
    receipt=dict(protocol=PROTOCOL,phase=a.phase,started_at_utc=now(),host=socket.gethostname(),
                 pid=os.getpid(),runtime=sys.executable,command=sys.argv,
                 commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                 dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines())
    if a.phase=="acquire-history":
        if (SOURCE/FILES[2]).exists(): raise ValueError("Target already acquired")
        receipt["source_identities"]=[]
        for i in (0,1):
            receipt["source_identities"].append(acquire(i))
            with Image.open(SOURCE/FILES[i]) as raw:
                im=ImageOps.exif_transpose(raw).convert("RGB")
                im.thumbnail((1600,1200)); im.save(a.output/f"step{24+i}_preview.png")
        receipt["target_acquired"]=False
    elif a.phase=="history":
        if (SOURCE/FILES[2]).exists(): raise ValueError("Target cannot precede history save")
        receipt["source_identities"]=[verified(i) for i in (0,1)]
        cfg=json.loads(a.geometry.read_text()); arrays={}; records=[]
        if cfg.get("no_identifiable_trace"):
            geom=cfg
            for i in (0,1): records.append(dict(step=24+i,filename=FILES[i],attempted=False,
                measurement=unavailable("no_identifiable_historical_crack_trace"),
                registration=dict(attempted=False,valid=None,reason="profile_not_defined")))
        else:
            first,second=(native_gray(SOURCE/FILES[i]) for i in (0,1))
            if not np.isclose(np.linalg.norm(cfg["normal"]),1,atol=1e-9): raise ValueError("Unit normal required")
            shift=0.
            if list(first.shape)==cfg["native_shape"]:
                try: shift=measure(sample_profile(first,np.eye(3),cfg["rough_center"],cfg["normal"]))[0]["peak_offset_native_px"]
                except ValueError as error:
                    if str(error)!="profile support leaves source image": raise
            geom=dict(cfg,center=(np.array(cfg["rough_center"])+np.array(cfg["normal"])*shift).tolist(),
                      refinement_native_px=float(shift))
            save(a.output/"geometry_saved_before_formal_measurement.json",geom)
            regs=[dict(valid=True,reason="first_image",dx=0.,dy=0.,patches=[]),registration_safe(first,second,cfg)]
            for i,im in enumerate((first,second)):
                found,data=profile_safe(im,geom,regs[i])
                records.append(dict(step=24+i,filename=FILES[i],attempted=True,measurement=found,registration=regs[i]))
                if data is not None: arrays.update({f"s{24+i}_{k}":v for k,v in data.items()})
        widths=[r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in records]
        pred=prediction(widths)
        h=dict(protocol=PROTOCOL,E=pred["E"],geometry=geom,history=records,predictions=pred,
               E_reasons=[r["measurement"]["reason"] for r in records if not r["measurement"]["valid"]],
               origin_step=25,target_step=26,unit="native_step24_reference_px",saved_at_utc=now(),
               target_file_present_at_save=False)
        save(a.output/"history_snapshot.json",h)
        np.savez_compressed(a.output/"profiles.npz",offsets=S,**arrays)
        save(a.output/"predictions_saved_before_target.json",h)
        if json.loads((a.output/"predictions_saved_before_target.json").read_text())!=h: raise ValueError("Save mismatch")
        save(a.output/"summary.json",summary(h)); receipt["E"]=h["E"]
        print(json.dumps(h,indent=2))
    else:
        hp=a.history/"predictions_saved_before_target.json"; before=hp.read_bytes(); h=json.loads(before)
        if (h["protocol"]!=PROTOCOL or h["origin_step"]!=25 or h["target_step"]!=26 or
            not h["E"] or h["target_file_present_at_save"] or
            not all(v["success"] for v in h["predictions"]["arms"].values())):
            raise ValueError("Eligible closed history required")
        receipt["history_saved_at_utc"]=h["saved_at_utc"]
        acquire(2); receipt["target_acquired_at_utc"]=now()
        receipt["source_identities"]=[verified(i) for i in (0,2)]
        first,target=native_gray(SOURCE/FILES[0]),native_gray(SOURCE/FILES[2])
        prev=h["history"][-1]["registration"]
        reg=registration_safe(first,target,h["geometry"],seed=(prev["dx"],prev["dy"]))
        found,data=profile_safe(target,h["geometry"],reg)
        ref=dict(step=26,filename=FILES[2],attempted=True,measurement=found,registration=reg)
        save(a.output/"target_measurement.json",ref)
        if data is not None: np.savez_compressed(a.output/"profiles.npz",offsets=S,**{f"s26_{k}":v for k,v in data.items()})
        result=summary(h,ref); save(a.output/"summary.json",result)
        if hp.read_bytes()!=before: raise ValueError("Historical snapshot changed")
        receipt["history_snapshot_unchanged"]=True
        print(json.dumps(result,indent=2))
    receipt.update(execution="succeeded",retrieval="verified_local",ended_at_utc=now(),
                   wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
    save(a.output/"run_receipt.json",receipt)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("phase",choices=("self-test","acquire-history","history","target"))
    for key in ("geometry","history","output"): p.add_argument("--"+key,type=Path)
    a=p.parse_args()
    if a.phase=="self-test":
        self_test()
        fake=dict(E=False,predictions=prediction([None,None]))
        r=summary(fake); assert r["R"] is None and not r["target_attempted"] and r["common_scored"]==0
        fake=dict(E=True,predictions=prediction([10.,14.]))
        r=summary(fake,dict(measurement=dict(valid=True,fwhm_native_px=19.)))
        assert r["delta_abs_error_px"]==-4. and r["common_scored"]==1
        print("E034 stage roles, paired score sign, coverage: passed")
    else:
        try: execute(a)
        except Exception as error:
            if a.output.is_dir() and not (a.output/"failed_receipt.json").exists():
                save(a.output/"failed_receipt.json",dict(execution="failed",phase=a.phase,
                     error=f"{type(error).__name__}: {error}",command=sys.argv,ended_at_utc=now()))
            raise
