"""E038 finite one-at-a-time geometry sensitivity; no forecasts or fitting."""
import argparse
import copy
import csv
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

import md01_frame_geometry as v1
from md01_early_relative import now, save

PROTOCOL = "geometry-oat-stability-v1"
STAGES = (18, 19, 21, 22, 23)
ARCHIVE = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments")
V1_RUNS = ARCHIVE / "S03-E037-MD01/runs"
ARMS = [dict(id=name, gray_max=g, contrast_min=c, dx=x, dy=y) for name, g, c, x, y in (
    ("v1", 100, 20, 0, 0),
    ("gray_minus5", 95, 20, 0, 0), ("gray_plus5", 105, 20, 0, 0),
    ("contrast_minus5", 100, 15, 0, 0), ("contrast_plus5", 100, 25, 0, 0),
    ("guide_x_minus5", 100, 20, -5, 0), ("guide_x_plus5", 100, 20, 5, 0),
    ("guide_y_minus5", 100, 20, 0, -5), ("guide_y_plus5", 100, 20, 0, 5))]


def old_step(stage):
    run = "S03-E037-MD01-R002" if stage == 23 else "S03-E037-MD01-R001"
    return V1_RUNS / run / f"step{stage}"


def receipt(phase):
    return dict(protocol=PROTOCOL, phase=phase, started_at_utc=now(), host=socket.gethostname(),
                pid=os.getpid(), runtime=sys.executable, command=sys.argv,
                commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                dirty=subprocess.check_output(["git", "status", "--porcelain"], text=True).splitlines())


def prepare(a):
    a.output.mkdir(parents=True, exist_ok=False)
    lock = json.loads(a.lock.read_text())
    protected = dict(lock["protected_old_hashes"])
    for root in (V1_RUNS / "S03-E037-MD01-R001", V1_RUNS / "S03-E037-MD01-R002"):
        for p in sorted(root.rglob("*")):
            if p.is_file():
                protected[str(p)] = v1.sha(p)
    for p in (a.lock, a.support, Path(v1.__file__), Path(__file__), Path("scripts/d01_crack_profile_diagnostic.py")):
        p = p.resolve()
        protected[str(p)] = v1.sha(p)
    manifest = dict(protocol=PROTOCOL, stages=list(STAGES), arms=ARMS,
                    roi=lock["roi_xyxy"], common_roi=lock["forecast_roi_xyxy"],
                    frames=[f for f in lock["frames"] if f["stage"] in STAGES],
                    support_path=str(a.support.resolve()), protected_files=protected,
                    baseline_steps={str(s): str(old_step(s)) for s in STAGES},
                    no_forecast_files_parsed=True)
    assert len(manifest["frames"]) == 5
    save(a.output / "input_manifest.json", manifest)
    rec = receipt("prepare_hashes_only")
    rec.update(execution="succeeded", retrieval="verified_local", ended_at_utc=now(), no_image_decode=True)
    save(a.output / "run_receipt.json", rec)
    print("Prepared five-source manifest; old forecasts hashed only, not parsed.")


def extract_variant(rgb, support, roi, arm):
    """Same v1 extraction with only the four explicitly allowed scalar inputs."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    excluded = np.zeros(gray.shape, np.uint8)
    for poly in support["exclude_polygons"]:
        points = np.rint(np.array(poly) - np.array(roi[:2])).astype(np.int32)
        cv2.fillPoly(excluded, [points], 1)
    seed = np.zeros(gray.shape, np.uint8)
    if support["visible_trace"]:
        points = np.rint(np.array(support["coarse_guide_xy"]) + np.array([arm["dx"], arm["dy"]]) - np.array(roi[:2])).astype(np.int32)
        cv2.polylines(seed, [points], False, 1, thickness=1)
    mask = np.zeros(gray.shape, bool)
    if np.any(seed):
        distance = distance_transform_edt(~seed.astype(bool))
        background = cv2.boxFilter(gray, -1, (101, 101), borderType=cv2.BORDER_REFLECT)
        candidate = ((gray <= arm["gray_max"]) & (background - gray >= arm["contrast_min"])
                     & (distance <= 60) & ~excluded.astype(bool))
        _, labels, stats, _ = cv2.connectedComponentsWithStats(candidate.astype(np.uint8), 8)
        near = np.unique(labels[(distance <= 12) & candidate])
        keep = [int(k) for k in near if k > 0 and stats[k, cv2.CC_STAT_HEIGHT] >= 30]
        mask = np.isin(labels, keep) if keep else mask
    safe = distance_transform_edt(~excluded.astype(bool)) > 60
    safe[:60] = False
    safe[-60:] = False
    safe[:, :60] = False
    safe[:, -60:] = False
    return mask, excluded.astype(bool), safe


def path_bitmap(paths, shape, roi):
    mask = np.zeros(shape, bool)
    for p in paths:
        xy = (np.array(p["xy_native"]) - np.array(roi[:2])).astype(int)
        mask[xy[:, 1], xy[:, 0]] = True
    return mask


def comparison(mask, refmask, paths, refpaths, values, refvalues, roi):
    union = np.count_nonzero(mask | refmask)
    p = path_bitmap(paths, mask.shape, roi)
    q = path_bitmap(refpaths, mask.shape, roi)
    distances = np.r_[distance_transform_edt(~p)[q], distance_transform_edt(~q)[p]] if p.any() and q.any() else np.array([])
    out = dict(mask_iou=float(np.count_nonzero(mask & refmask) / union) if union else None,
               path_distance_mean_px=float(np.mean(distances)) if distances.size else None,
               path_distance_p90_px=float(np.percentile(distances, 90)) if distances.size else None)
    for key in v1.METRICS:
        base, value = refvalues[key], values[key]
        out[key + "_delta"] = value - base if value is not None and base is not None else None
        out[key + "_relative_delta"] = (value / base - 1) if value is not None and base not in (None, 0) else None
    return out


def protect(manifest):
    bad = [p for p, h in manifest["protected_files"].items() if v1.sha(p) != h]
    if bad:
        raise ValueError(f"Protected file changed: {bad}")


def run(a):
    start, cpu = time.monotonic(), time.process_time()
    manifest = json.loads(a.manifest.read_text())
    assert manifest["protocol"] == PROTOCOL and manifest["stages"] == list(STAGES) and manifest["arms"] == ARMS
    protect(manifest)
    support = json.loads(Path(manifest["support_path"]).read_text())
    a.output.mkdir(parents=True, exist_ok=False)
    rec = receipt("geometry_stability")
    rec.update(manifest_sha256=v1.sha(a.manifest), manifest_path=str(a.manifest.resolve()), execution="running")
    rows, summaries = [], []

    def budget():
        if max(time.monotonic() - start, time.process_time() - cpu) > 180:
            raise TimeoutError("180s numerical phase cap")

    try:
        for f in manifest["frames"]:
            budget()
            stage, roi, common = f["stage"], manifest["roi"], manifest["common_roi"]
            rgb = v1.read_frame(f, roi)
            baseline = Path(manifest["baseline_steps"][str(stage)])
            with np.load(baseline / "geometry_arrays.npz") as data:
                old = {k: data[k].copy() for k in data.files}
            reference = json.loads((baseline / "metrics.json").read_text())
            refpaths = json.loads((baseline / "paths.json").read_text())
            xy = np.concatenate([np.array(p["xy_native"], int) for p in refpaths["full"]]) - np.array(roi[:2])
            refwidth = np.array([np.nan if x is None else x for p in refpaths["full"] for x in p["local_mask_thickness_px"]])
            widthgrid, counts = [], np.zeros(old["mask"].shape, np.uint8)
            for arm in ARMS:
                budget()
                mask, excluded, safe = extract_variant(rgb, support["frames"][str(stage)], roi, arm)
                full, paths, skel = v1.metrics(mask, safe, roi)
                common_values, cpaths, cskel = v1.metrics(mask, safe, roi, common)
                if not np.array_equal(excluded, old["excluded"]) or not np.array_equal(safe, old["safe"]):
                    raise ValueError("Fixed visibility support changed")
                if arm["id"] == "v1":
                    if not (np.array_equal(mask, old["mask"]) and np.array_equal(skel, old["skeleton"])
                            and np.array_equal(cskel, old["common_skeleton"]) and full == reference["full"]
                            and common_values == reference["common"] and paths == refpaths["full"] and cpaths == refpaths["common"]):
                        raise ValueError("v1 reconstruction mismatch")
                out = a.output / f"step{stage}" / arm["id"]
                out.mkdir(parents=True)
                np.savez_compressed(out / "geometry_arrays.npz", mask=mask, excluded=excluded, safe=safe, skeleton=skel, common_skeleton=cskel)
                save(out / "paths.json", dict(full=paths, common=cpaths))
                thickness = 2 * distance_transform_edt(mask)
                valid = mask[xy[:, 1], xy[:, 0]] & safe[xy[:, 1], xy[:, 0]]
                sampled = np.where(valid, thickness[xy[:, 1], xy[:, 0]], np.nan)
                widthgrid.append(sampled)
                counts += mask.astype(np.uint8)
                fixed_good = np.isfinite(refwidth)
                joint = fixed_good & valid
                fixed_diff = np.abs(sampled[joint] - refwidth[joint])
                row = dict(stage=stage, arm=arm["id"], parameters=arm,
                           full=full, common=common_values,
                           full_change=comparison(mask, old["mask"], paths, refpaths["full"], full, reference["full"], roi),
                           fixed_v1_path_available_fraction=float(joint.sum() / fixed_good.sum()) if fixed_good.any() else None,
                           fixed_v1_path_thickness_abs_delta_median_px=float(np.median(fixed_diff)) if fixed_diff.size else None,
                           fixed_v1_path_thickness_abs_delta_p90_px=float(np.percentile(fixed_diff, 90)) if fixed_diff.size else None)
                x0, y0, x1, y1 = np.array(common) - np.array([roi[0], roi[1], roi[0], roi[1]])
                band = np.zeros(mask.shape, bool)
                band[y0:y1, x0:x1] = True
                row["common_change"] = comparison(mask & band, old["mask"] & band, cpaths, refpaths["common"], common_values, reference["common"], roi)
                save(out / "metrics.json", row)
                rows.append(row)
                print(stage, arm["id"], "area", full["area_px2"], "L", full["length_px"], flush=True)
            np.savez_compressed(a.output / f"step{stage}/fixed_path_stability.npz", xy_native=xy + np.array(roi[:2]),
                                thickness_grid=np.array(widthgrid), baseline_thickness=refwidth, mask_setting_count=counts)
            stage_rows = rows[-len(ARMS):]
            summary = dict(stage=stage, available_full=sum(r["full"]["valid"] for r in stage_rows),
                           available_common=sum(r["common"]["valid"] for r in stage_rows))
            for scope in ("full", "common"):
                for key in ("area_px2", "length_px", "thickness_p50_px"):
                    vals = [abs(r[scope + "_change"][key + "_relative_delta"]) for r in stage_rows[1:]
                            if r[scope + "_change"][key + "_relative_delta"] is not None]
                    summary[scope + "_" + key + "_max_abs_relative_change"] = max(vals) if vals else None
            summary["min_mask_iou"] = min(r["full_change"]["mask_iou"] for r in stage_rows[1:])
            summary["min_fixed_path_available_fraction"] = min(r["fixed_v1_path_available_fraction"] for r in stage_rows[1:])
            summaries.append(summary)
        save(a.output / "all_metrics.json", rows)
        save(a.output / "summary.json", summaries)
        flat = [dict(stage=r["stage"], arm=r["arm"], **{scope + "_" + key: value for scope in ("full", "common", "full_change", "common_change") for key, value in r[scope].items()},
                     **{k: v for k, v in r.items() if k.startswith("fixed_")}) for r in rows]
        with (a.output / "metrics.csv").open("x", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(flat[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(flat)
        protect(manifest)
        budget()
        rec.update(execution="succeeded", retrieval="verified_local", settings_per_frame=9, frame_count=5,
                   v1_reconstruction_exact=True, protected_files_unchanged=True, no_forecast_computation=True)
    except Exception as error:
        rec.update(execution="failed", error=repr(error))
        raise
    finally:
        rec.update(ended_at_utc=now(), wall_seconds=time.monotonic() - start, cpu_seconds=time.process_time() - cpu)
        save(a.output / "run_receipt.json", rec)


def tests():
    rgb = np.full((350,280,3), 180, np.uint8)
    rgb[40:310,100:111] = 25
    support = dict(visible_trace=True, coarse_guide_xy=[[105,40],[105,310]], exclude_polygons=[[[0,170],[280,170],[280,180],[0,180]]])
    roi = [0,0,280,350]
    a = extract_variant(rgb, support, roi, ARMS[0])
    b = v1.extract(rgb, support, roi)
    assert all(np.array_equal(x,y) for x,y in zip(a,b))
    assert not (a[0] & a[1]).any() and not a[0][175].any()
    original = copy.deepcopy(support)
    for arm in ARMS:
        extract_variant(rgb, support, roi, arm)
    assert support == original
    assert len(ARMS) == 9 and len({a["id"] for a in ARMS}) == 9
    for arm in ARMS[1:]:
        assert sum(arm[k] != ARMS[0][k] for k in ("gray_max","contrast_min","dx","dy")) == 1
    values, paths, _ = v1.metrics(a[0], a[2], roi)
    c = comparison(a[0], a[0], paths, paths, values, values, roi)
    assert c["mask_iou"] == 1 and c["path_distance_p90_px"] == 0 and c["area_px2_delta"] == 0
    empty = dict(visible_trace=False, coarse_guide_xy=[], exclude_polygons=[])
    m, _, safe = extract_variant(rgb, empty, roi, ARMS[0])
    assert v1.metrics(m,safe,roi)[0]["area_px2"] is None
    print("Synthetic default equivalence, exclusions, nonmutation, OAT grid, identity metrics and nulls passed.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=("self-test", "prepare", "run"))
    for key in ("lock", "support", "manifest", "output"):
        p.add_argument("--" + key, type=Path)
    args = p.parse_args()
    if args.phase == "self-test":
        tests()
    elif args.phase == "prepare":
        prepare(args)
    else:
        run(args)
