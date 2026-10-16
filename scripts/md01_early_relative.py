"""E033: exact Step2/3 history first; Step4 only after closed eligible outputs."""
from __future__ import annotations
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
from md01_relative_stage_pilot import match_background, profile_at

PROTOCOL = "early-relative-halfdepth-v1"
FILES = ("IMG_0326.JPG", "IMG_0329.JPG", "IMG_0332.JPG")
IDS = ("071d903a-77b0-4027-ac15-021477abf8e3", "ae7e9c7e-1b50-486c-adc6-f1b46e26cc2a",
       "8e57e853-c3c3-4cbc-99a0-c6d6546947fe")
ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive")
METADATA = ROOT/"open_data/md01_tack_metadata_20261016/fixed_camera_file_metadata.json"
EXPERIMENT = ROOT/"experiments/S03-E033-MD01"
SOURCE = EXPERIMENT/"raw_images"


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def identities():
    rows = json.loads(METADATA.read_text())
    selected = []
    for name, fid in zip(FILES, IDS):
        matches = [r for r in rows if r["filename"] == name and r["id"] == fid]
        if len(matches) != 1:
            raise ValueError("Nonunique official file identity")
        selected.append(matches[0])
    return selected


def verified(index):
    row = identities()[index]
    path = SOURCE/FILES[index]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != row["content_details"]["sha256_hash"] or path.stat().st_size != row["size"]:
        raise ValueError("Official identity mismatch")
    return dict(filename=FILES[index], file_id=IDS[index], bytes=path.stat().st_size,
                sha256=digest)


def acquire(index):
    row = identities()[index]
    path = SOURCE/FILES[index]
    if path.exists():
        raise ValueError("Refuse to overwrite acquired source")
    url = f"https://data.mendeley.com/public-files/datasets/dns97tfdjn/files/{IDS[index]}/file_downloaded"
    if row["content_details"]["download_url"] != url:
        raise ValueError("Unexpected source URL")
    subprocess.run(["curl", "--fail", "--location", "--max-time", "60", "--silent",
                    "--show-error", "--output", str(path), url], check=True, timeout=65)
    return dict(**verified(index), acquired_at_utc=now())


def prediction(widths):
    valid = len(widths) == 2 and all(w is not None and np.isfinite(w) for w in widths)
    out = dict(E=bool(valid), raw={}, arms={})
    for arm in ("persistence", "stage_trend"):
        out["arms"][arm] = dict(attempted=bool(valid), success=False, prediction_px=None,
                                 reason="history_measurement_missing")
    if valid:
        out["raw"] = dict(persistence=float(widths[1]), stage_trend=float(2*widths[1]-widths[0]))
        for arm, value in out["raw"].items():
            mapped = float(np.clip(value, 0, 120))
            out["arms"][arm].update(success=True, prediction_px=mapped, reason="ok",
                                     clipped=bool(mapped != value))
    return out


def unavailable(reason):
    return dict(valid=False, reason=reason, fwhm_native_px=None)


def registration_safe(first, later, cfg, seed=(0., 0.)):
    try:
        return match_background(first, later, cfg, seed=seed)
    except ValueError as error:
        if str(error) != "Background support outside image":
            raise
        return dict(valid=False, reason="background_support_outside_image", dx=None, dy=None, patches=[])


def profile_safe(image, geometry, registration):
    if list(image.shape) != geometry["native_shape"]:
        return unavailable("native_geometry_mismatch"), None
    try:
        return profile_at(image, geometry, registration)
    except ValueError as error:
        if str(error) != "profile support leaves source image":
            raise
        return unavailable("profile_support_outside_image"), None


def historical_summary(snapshot):
    return dict(protocol=PROTOCOL, E=snapshot["E"], E_reasons=snapshot["E_reasons"],
                opportunities=1, target_attempted=False, R=None, common_scored=0,
                coverage=0, conditional_common_coverage=None, target_width_px=None,
                delta_abs_error_px=None, unit=snapshot["unit"],
                status="awaiting_target" if snapshot["E"] else "stopped_history_ineligible",
                methods={arm: dict(value, scored=False, abs_error_px=None)
                         for arm, value in snapshot["predictions"]["arms"].items()})


def execute(args):
    start, cpu = time.monotonic(), time.process_time()
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(protocol=PROTOCOL, phase=args.phase, started_at_utc=now(),
                   host=socket.gethostname(), pid=os.getpid(), runtime=sys.executable,
                   commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                   dirty=subprocess.check_output(["git", "status", "--porcelain"], text=True).splitlines(),
                   command=sys.argv, source=str(SOURCE))
    SOURCE.mkdir(parents=True, exist_ok=True)
    if args.phase == "acquire-history":
        if (SOURCE/FILES[2]).exists():
            raise ValueError("Target already in experiment")
        records = []
        for i in (0, 1):
            path = SOURCE/FILES[i]
            records.append(acquire(i))
            with Image.open(path) as source:
                preview = ImageOps.exif_transpose(source).convert("RGB")
                preview.thumbnail((1600, 1200))
                preview.save(out/f"history_step{i+2}_preview.png")
        save(out/"source_identities.json", records)
        receipt["target_acquired"] = False
    elif args.phase == "history":
        if (SOURCE/FILES[2]).exists():
            raise ValueError("Target cannot precede historical save")
        cfg = json.loads(args.geometry.read_text())
        receipt["source_identities"] = [verified(i) for i in (0, 1)]
        receipt["geometry_input"] = str(args.geometry)
        if cfg.get("no_identifiable_trace"):
            missing_history = [dict(step=i+2, filename=FILES[i], attempted=False,
                                    measurement=unavailable("no_identifiable_historical_crack_trace"),
                                    registration=dict(attempted=False, valid=None, reason="profile_not_defined"))
                               for i in (0, 1)]
            snapshot = dict(protocol=PROTOCOL, E=False, geometry=cfg, history=missing_history,
                            predictions=prediction([None, None]),
                            E_reasons=["no_identifiable_historical_crack_trace"],
                            origin_step=3, target_step=4, unit="native_step2_reference_px",
                            target_file_present_at_save=False, saved_at_utc=now())
            save(out/"predictions_saved_before_target.json", snapshot)
        else:
            first, second = (native_gray(SOURCE/FILES[i]) for i in (0, 1))
            if not np.isclose(np.linalg.norm(cfg["normal"]), 1, atol=1e-9):
                raise ValueError("Normal must be unit length")
            if list(first.shape) == cfg["native_shape"]:
                try:
                    rough, _, _ = measure(sample_profile(first, np.eye(3), cfg["rough_center"], cfg["normal"]))
                except ValueError as error:
                    if str(error) != "profile support leaves source image":
                        raise
                    rough = dict(peak_offset_native_px=0.)
            else:
                rough = dict(peak_offset_native_px=0.)
            geometry = dict(cfg, center=(np.asarray(cfg["rough_center"])+
                            np.asarray(cfg["normal"])*rough["peak_offset_native_px"]).tolist(),
                            refinement_native_px=rough["peak_offset_native_px"])
            save(out/"geometry_saved_before_formal_measurement.json", geometry)
            regs = [dict(valid=True, reason="first_image", dx=0., dy=0., patches=[]),
                    registration_safe(first, second, cfg)]
            records, arrays = [], {}
            for i, image in enumerate((first, second)):
                result, data = profile_safe(image, geometry, regs[i])
                records.append(dict(step=i+2, filename=FILES[i], measurement=result, registration=regs[i]))
                if data is not None:
                    arrays.update({f"s{i+2}_{key}": value for key, value in data.items()})
            widths = [r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else None for r in records]
            pred = prediction(widths)
            snapshot = dict(protocol=PROTOCOL, E=pred["E"], geometry=geometry, history=records,
                            predictions=pred, E_reasons=[r["measurement"]["reason"] for r in records
                                                       if not r["measurement"]["valid"]],
                            origin_step=3, target_step=4, unit="native_step2_reference_px",
                            target_file_present_at_save=False, saved_at_utc=now())
            np.savez_compressed(out/"profiles.npz", offsets=S, **arrays)
        save(out/"history_snapshot.json", snapshot)
        # Final save point is closed before later target acquisition.
        if not (out/"predictions_saved_before_target.json").exists():
            save(out/"predictions_saved_before_target.json", snapshot)
        if json.loads((out/"predictions_saved_before_target.json").read_text()) != snapshot:
            raise ValueError("Saved prediction mismatch")
        save(out/"summary.json", historical_summary(snapshot))
        receipt["E"] = snapshot["E"]
        print(json.dumps(snapshot, indent=2))
    else:
        snapshot_path = args.history/"predictions_saved_before_target.json"
        before = snapshot_path.read_bytes()
        snapshot = json.loads(before)
        if (snapshot["protocol"] != PROTOCOL or not snapshot["E"] or
            snapshot["target_file_present_at_save"] or
            not all(v["success"] for v in snapshot["predictions"]["arms"].values())):
            raise ValueError("No eligible saved historical prediction")
        path = SOURCE/FILES[2]
        if path.exists():
            raise ValueError("Target must not be acquired before this evaluation phase")
        receipt["history_closed_saved_at_utc"] = snapshot["saved_at_utc"]
        acquire(2)
        receipt["target_acquired_at_utc"] = now()
        receipt["source_identities"] = [verified(i) for i in (0, 2)]
        first, target = native_gray(SOURCE/FILES[0]), native_gray(path)
        prev = snapshot["history"][-1]["registration"]
        reg = registration_safe(first, target, snapshot["geometry"], seed=(prev["dx"], prev["dy"]))
        found, data = profile_safe(target, snapshot["geometry"], reg)
        reference = dict(step=4, filename=FILES[2], measurement=found, registration=reg)
        save(out/"target_measurement.json", reference)
        if data is not None:
            np.savez_compressed(out/"profiles.npz", offsets=S, **{f"s4_{k}": v for k, v in data.items()})
        valid = bool(found["valid"])
        summary = dict(protocol=PROTOCOL, E=True, target_attempted=True, R=valid, opportunities=1,
                       common_scored=int(valid), coverage=int(valid), unit=snapshot["unit"],
                       conditional_common_coverage=int(valid),
                       target_width_px=found["fwhm_native_px"] if valid else None,
                       delta_abs_error_px=None, methods={})
        for arm, value in snapshot["predictions"]["arms"].items():
            summary["methods"][arm] = dict(value, scored=valid, abs_error_px=(
                abs(value["prediction_px"]-found["fwhm_native_px"]) if valid else None))
        if valid:
            summary["delta_abs_error_px"] = (summary["methods"]["stage_trend"]["abs_error_px"]-
                                             summary["methods"]["persistence"]["abs_error_px"])
        save(out/"summary.json", summary)
        if snapshot_path.read_bytes() != before:
            raise ValueError("Historical snapshot altered")
        receipt["history_snapshot_unchanged"] = True
        print(json.dumps(summary, indent=2))
    receipt.update(ended_at_utc=now(), wall_seconds=time.monotonic()-start,
                   cpu_seconds=time.process_time()-cpu, execution="succeeded", retrieval="verified_local")
    save(out/"run_receipt.json", receipt)


def self_test():
    from independent_d01_halfdepth import measure as independent
    for sigma in (1.5, 3., 8.):
        p = 180+.02*S-100*np.exp(-S*S/(2*sigma*sigma))
        actual = measure(p)[0]
        expected = independent(S, p)
        assert actual["valid"] and expected["valid"]
        assert abs(actual["fwhm_native_px"]-expected["width_px"]) < 1e-10
    assert prediction([10., 14.])["arms"]["stage_trend"]["prediction_px"] == 18.
    assert prediction([100., 119.])["arms"]["stage_trend"]["prediction_px"] == 120.
    assert prediction([10., 2.])["arms"]["stage_trend"]["prediction_px"] == 0.
    assert not prediction([None, 2.])["E"]
    assert not prediction([np.nan, 2.])["E"]
    assert not measure(np.full(S.shape, 180.))[0]["valid"]
    fake = dict(E=False, E_reasons=["no_trace"], unit="native_step2_reference_px",
                predictions=prediction([None, None]))
    absent = historical_summary(fake)
    assert absent["R"] is None and not absent["target_attempted"] and absent["common_scored"] == 0
    assert absent["conditional_common_coverage"] is None
    image = np.full((100, 100), 180, dtype=np.float32)
    cfg = dict(native_shape=[100,100], center=[1,1], normal=[1,0])
    assert profile_safe(image, cfg, dict(valid=True, dx=0., dy=0.))[0]["reason"] == "profile_support_outside_image"
    assert profile_safe(image[:90], cfg, dict(valid=True, dx=0., dy=0.))[0]["reason"] == "native_geometry_mismatch"
    print("Synthetic unchanged half-depth, missingness, stage formula and common clipping: passed")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=("acquire-history", "history", "target", "self-test"))
    p.add_argument("--output", type=Path)
    p.add_argument("--geometry", type=Path)
    p.add_argument("--history", type=Path)
    args = p.parse_args()
    if args.phase == "self-test":
        self_test()
    else:
        try:
            execute(args)
        except Exception as error:
            if args.output.is_dir() and not (args.output/"failed_receipt.json").exists():
                save(args.output/"failed_receipt.json", dict(protocol=PROTOCOL, phase=args.phase,
                     execution="failed", error=f"{type(error).__name__}: {error}", ended_at_utc=now(),
                     command=sys.argv, commit=subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()))
            raise
