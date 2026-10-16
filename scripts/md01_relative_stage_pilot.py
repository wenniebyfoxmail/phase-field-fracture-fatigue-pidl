"""MD01 three-stage, history-first pilot. No workbook response access or training."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

import cv2
import numpy as np

from d01_crack_profile_diagnostic import S, native_gray, sample_profile, measure, forecast

FILES = ("IMG_0403.JPG", "IMG_0406.JPG", "IMG_0409.JPG")
EXPECTED = (
    (18651977, "0cb0b64c232198122144ccb35e9a53c41af9e658a0ecef1aff097524c794f032"),
    (17498663, "7228ffacef032c4c9232d403a544b343260efd5801d2d5fd0e0a9d5625b50a62"),
    (18624477, "fd64a042256ff730c07023a2cd9f039d2b43d4ee435f55a2445b053ce727ffd6"),
)
PROTOCOL = "relative-stage-halfdepth-v1"


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def identity(path, index):
    size, digest = EXPECTED[index]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != size or actual != digest:
        raise ValueError(f"Official source identity mismatch: {path.name}")
    return dict(filename=path.name, bytes=size, sha256=actual)


def parabola(a, b, c):
    denominator = a - 2*b + c
    return float(np.clip(.5*(a-c)/denominator, -1, 1)) if denominator < -1e-12 else 0.


def match_background(first, later, config, seed=(0.,0.)):
    """Map first -> later with fixed off-crack patches, never width optimization."""
    half = config["patch_size"]//2
    radius = config["translation_radius"]
    patches = []
    seed_x, seed_y = (int(round(v)) for v in seed)
    if first.shape != later.shape:
        return dict(valid=False, reason="native_shape_changed", patches=[], dx=None, dy=None)
    for x, y in config["background_centers"]:
        x, y = int(x), int(y)
        sx, sy = x+seed_x, y+seed_y
        if min(x-half, y-half, sx-half-radius, sy-half-radius) < 0 or sx+half+radius >= later.shape[1] or sy+half+radius >= later.shape[0]:
            raise ValueError("Background support outside image")
        template = first[y-half:y+half+1, x-half:x+half+1]
        search = later[sy-half-radius:sy+half+radius+1, sx-half-radius:sx+half+radius+1]
        response = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, (xx, yy) = cv2.minMaxLoc(response)
        inside = 0 < xx < response.shape[1]-1 and 0 < yy < response.shape[0]-1
        dx = seed_x+xx-radius
        dy = seed_y+yy-radius
        if inside:
            dx += parabola(*map(float, response[yy, xx-1:xx+2]))
            dy += parabola(*map(float, response[yy-1:yy+2, xx]))
        good = bool(inside and np.isfinite(score) and score >= config["correlation_min"])
        patches.append(dict(center=[x,y], dx=float(dx), dy=float(dy), correlation=float(score), valid=good))
    accepted = [p for p in patches if p["valid"]]
    valid = len(accepted) >= config["required_background_patches"]
    if not valid:
        return dict(valid=False, reason="insufficient_background_correspondence", patches=patches, dx=None, dy=None)
    dx, dy = np.median([[p["dx"],p["dy"]] for p in accepted],axis=0)
    residuals = [float(np.hypot(p["dx"]-dx,p["dy"]-dy)) for p in accepted]
    return dict(valid=True, reason="ok", patches=patches, dx=float(dx),dy=float(dy),search_seed_px=[seed_x,seed_y],
                patch_residuals_px=residuals, max_patch_residual_px=max(residuals))


def profile_at(image, geometry, registration):
    if not registration["valid"]:
        return dict(valid=False, reason=registration["reason"], fwhm_native_px=None), None
    H = np.array([[1,0,-registration["dx"]],[0,1,-registration["dy"]],[0,0,1]],float)
    profile = sample_profile(image,H,geometry["center"],geometry["normal"])
    result, deficit, background = measure(profile)
    return result, dict(profile=profile, deficit=deficit, background=background)


def prediction_from_history(widths):
    if len(widths) != 2 or any(w is None for w in widths):
        return dict(valid=False, reason="history_measurement_missing", persistence=None, secant=None, raw_secant=None)
    return dict(valid=True, reason="ok", persistence=float(forecast(widths,[27,28],29,"persistence")),
                secant=float(forecast(widths,[27,28],29,"secant")), raw_secant=float(2*widths[1]-widths[0]))


def receipt(out, phase, args):
    out.mkdir(parents=True,exist_ok=False)
    return dict(protocol=PROTOCOL, phase=phase, started_at_utc=now(),
                host=socket.gethostname(),pid=os.getpid(), runtime=os.sys.executable,
                commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
                command=os.sys.argv, inputs=vars(args)|{"source":str(args.source),"output":str(out),
                                                        "geometry":str(args.geometry),"history":str(args.history)})


def execute(args):
    start = time.monotonic()
    out = args.output
    r = receipt(out,args.phase,args)
    r["inputs"] = {k:str(v) if isinstance(v,Path) else v for k,v in r["inputs"].items()}
    records, arrays, identities = [], {}, []
    # Target access guard is checked before any image is read in this phase.
    if args.phase == "history" and (args.source/FILES[2]).exists():
        raise ValueError("Target must not have been acquired before history prediction save")
    if args.phase == "history":
        cfg = json.loads(args.geometry.read_text())
        for i in (0,1):
            identities.append(identity(args.source/FILES[i],i))
        first = native_gray(args.source/FILES[0])
        second = native_gray(args.source/FILES[1])
        if list(first.shape) != cfg["native_shape"] or first.shape != second.shape:
            raise ValueError("Native geometry mismatch")
        rough,_,_ = measure(sample_profile(first,np.eye(3),cfg["rough_center"],cfg["normal"]))
        geometry = dict(cfg, center=(np.asarray(cfg["rough_center"])+
                                    np.asarray(cfg["normal"])*rough["peak_offset_native_px"]).tolist(),
                        refinement_native_px=rough["peak_offset_native_px"])
        save(out/"geometry_saved_before_measurement.json", geometry)
        registrations = [dict(valid=True,reason="first_image",dx=0.,dy=0.,patches=[]),
                         match_background(first,second,cfg)]
        for i, image in enumerate((first,second)):
            found, data = profile_at(image,geometry,registrations[i])
            records.append(dict(stage=27+i,filename=FILES[i],measurement=found,registration=registrations[i]))
            if data is not None:
                arrays.update({f"s{27+i}_{key}":value for key,value in data.items()})
        widths = [rec["measurement"]["fwhm_native_px"] if rec["measurement"]["valid"] else None for rec in records]
        pred = prediction_from_history(widths)
        snapshot = dict(protocol=PROTOCOL,unit="native_first_image_px",origin_stage=28,target_stage=29,
                        geometry=geometry,history=records,predictions=pred,saved_at_utc=now(),
                        target_file_present_at_save=(args.source/FILES[2]).exists())
        save(out/"predictions_saved_before_target.json",snapshot)
        r.update(history_valid=sum(w is not None for w in widths),predictions_saved=pred["valid"])
    else:
        snapshot_path = args.history/"predictions_saved_before_target.json"
        snapshot = json.loads(snapshot_path.read_text())
        if snapshot["protocol"] != PROTOCOL or snapshot["target_file_present_at_save"]:
            raise ValueError("Invalid history-only snapshot")
        if (args.source/FILES[2]).stat().st_mtime_ns <= snapshot_path.stat().st_mtime_ns:
            raise ValueError("Target acquisition must follow closed prediction snapshot")
        for i in (0,2):
            identities.append(identity(args.source/FILES[i],i))
        first = native_gray(args.source/FILES[0])
        target = native_gray(args.source/FILES[2])
        geometry = snapshot["geometry"]
        previous = snapshot["history"][-1]["registration"]
        seed = (previous["dx"],previous["dy"]) if previous["valid"] else (0.,0.)
        registration = match_background(first,target,geometry,seed=seed)
        r["pretarget_amendment"] = "history-centered-background-search-v1.1"
        found,data = profile_at(target,geometry,registration)
        records.append(dict(stage=29,filename=FILES[2],measurement=found,registration=registration))
        if data is not None:
            arrays.update({f"s29_{key}":value for key,value in data.items()})
        scored = bool(snapshot["predictions"]["valid"] and found["valid"])
        w = found["fwhm_native_px"] if found["valid"] else None
        summary = dict(protocol=PROTOCOL,unit="native_first_image_px",target_width_px=w,
                       scored=scored,opportunities=1,coverage=int(scored),
                       valid_profiles=sum(rec["measurement"]["valid"] for rec in snapshot["history"]+records),
                       persistence_abs_error_px=None,secant_abs_error_px=None,delta_abs_error_px=None,
                       source_prediction_snapshot=str(snapshot_path),no_target_tuning=True)
        if scored:
            for arm in ("persistence","secant"):
                summary[arm+"_abs_error_px"] = abs(snapshot["predictions"][arm]-w)
            summary["delta_abs_error_px"] = summary["secant_abs_error_px"]-summary["persistence_abs_error_px"]
        save(out/"summary.json",summary)
        r.update(scored=scored)
    np.savez_compressed(out/"profiles.npz",offsets=S,**arrays)
    save(out/"measurements.json",records)
    r.update(source_identities=identities, ended_at_utc=now(),wall_seconds=time.monotonic()-start,
             execution="succeeded",retrieval="verified_local")
    if r["wall_seconds"]>120:
        r["budget_exceeded"] = True
    save(out/"run_receipt.json",r)
    print(json.dumps(records,indent=2))
    if args.phase == "history": print(json.dumps(snapshot["predictions"],indent=2))
    else: print(json.dumps(summary,indent=2))


def self_test():
    # Source photographs are never opened by the tests.
    from independent_d01_halfdepth import measure as independently_measure
    for sigma in (1.5,3.,8.):
        p=180+.02*S-100*np.exp(-S*S/(2*sigma*sigma))
        a,_,_=measure(p)
        b=independently_measure(S,p)
        assert a["valid"] and b["valid"] and abs(a["fwhm_native_px"]-b["width_px"])<1e-10
    assert not measure(np.full(S.shape,180.))[0]["valid"]
    assert prediction_from_history([10.,14.])["secant"] == 18.
    assert prediction_from_history([100.,119.])["secant"] == 120.
    assert not prediction_from_history([None,14.])["valid"]
    assert abs(parabola(.5,1.,.75)-1/6)<1e-12
    random=np.random.default_rng(16).normal(100,20,(260,300)).astype(np.float32)
    shifted=cv2.warpAffine(random,np.float32([[1,0,2],[0,1,-3]]),(300,260))
    config=dict(patch_size=31,translation_radius=10,background_centers=[[70,70],[200,70],[70,180],[200,180]],
                correlation_min=.6,required_background_patches=3)
    m=match_background(random,shifted,config)
    assert m["valid"] and abs(m["dx"]-2)<.02 and abs(m["dy"]+3)<.02
    assert not match_background(random,np.ones_like(random),config)["valid"]
    large_shift=cv2.warpAffine(random,np.float32([[1,0,2],[0,1,15]]),(300,260))
    m=match_background(random,large_shift,config,seed=(1.,10.))
    assert m["valid"] and abs(m["dx"]-2)<.02 and abs(m["dy"]-15)<.02
    print("Synthetic checks passed: independent half-depth, missingness, index prediction, clipping, translation direction/QC")


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("phase",choices=("history","target","self-test"))
    p.add_argument("--source",type=Path)
    p.add_argument("--geometry",type=Path)
    p.add_argument("--history",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.phase=="self-test": self_test()
    else: execute(a)
