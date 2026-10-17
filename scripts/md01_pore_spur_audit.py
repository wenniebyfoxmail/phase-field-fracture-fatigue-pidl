"""E039: one-pass protected terminal-spur filtering of existing E038 masks.

This is a geometric candidate filter, not a trained pore/crack classifier.
No source extraction, forecasts, scoring, or parameter search is performed.
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize

import md01_frame_geometry as v1
from md01_geometry_stability import ARCHIVE, ARMS, STAGES, path_bitmap, receipt
from md01_early_relative import now, save

PROTOCOL = "protected-terminal-spur-v1"
INPUT = ARCHIVE / "S03-E038-MD01/runs/S03-E038-MD01-R001"
PARAMETERS = dict(max_branch_length_px=60, max_length_thickness_ratio=3,
                  passes=1, protect_full_and_common_paths=True)


def graph(skeleton):
    """v1's orthogonal/diagonal convention, independently represented as lists."""
    coords = np.argwhere(skeleton)
    lookup = np.full(skeleton.shape, -1, np.int32)
    lookup[tuple(coords.T)] = np.arange(len(coords))
    adj = [[] for _ in coords]
    h, w = skeleton.shape
    for i, (y, x) in enumerate(coords):
        for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
            yy, xx = y + dy, x + dx
            if not (0 <= yy < h and 0 <= xx < w):
                continue
            j = int(lookup[yy, xx])
            if j < 0 or (dy and dx and (skeleton[y, xx] or skeleton[yy, x])):
                continue
            weight = float(np.hypot(dy, dx))
            adj[i].append((j, weight))
            adj[j].append((i, weight))
    return coords, adj


def filter_mask(mask, skeleton, protected_points):
    if not np.array_equal(skeletonize(mask), skeleton):
        raise ValueError("Input skeleton differs from saved mask skeleton")
    if np.any(protected_points & ~skeleton):
        # Common-band skeleton can differ from full skeleton at a crop boundary.
        # Protection is allowed at any in-mask point, but never outside the mask.
        if np.any(protected_points & ~mask):
            raise ValueError("Protected path outside original mask")
    edt = distance_transform_edt(mask)
    coords, adj = graph(skeleton)
    eligible = np.zeros(mask.shape, bool)
    ledger = []
    for start, neighbours in enumerate(adj):
        if len(neighbours) != 1:
            continue
        chain, length, previous, current = [start], 0., -1, start
        while True:
            onward = [(j, weight) for j, weight in adj[current] if j != previous]
            if not onward:
                break
            nxt, weight = onward[0]
            length += weight
            chain.append(nxt)
            previous, current = current, nxt
            if len(adj[current]) != 2:
                break
        if len(adj[current]) < 3:
            continue
        branch = coords[chain[:-1]]  # retain the junction
        widths = 2 * edt[tuple(branch.T)]
        median = float(np.median(widths))
        intersects = bool(np.any(protected_points[tuple(branch.T)]))
        ratio = length / median
        selected = (not intersects and length <= PARAMETERS["max_branch_length_px"]
                    and ratio <= PARAMETERS["max_length_thickness_ratio"])
        if selected:
            eligible[tuple(branch.T)] = True
        ledger.append(dict(branch_id=len(ledger), endpoint_yx=coords[start].tolist(),
                           junction_yx=coords[current].tolist(), length_px=length,
                           median_thickness_px=median, length_thickness_ratio=ratio,
                           intersects_protected_path=intersects, eligible=bool(selected),
                           skeleton_yx=branch.tolist()))
    tube = np.zeros(mask.shape, np.uint8)
    for y, x in np.argwhere(protected_points):
        cv2.circle(tube, (int(x), int(y)), int(np.ceil(edt[y, x])), 1, -1)
    tube = tube.astype(bool) & mask
    if skeleton.any():
        nearest = distance_transform_edt(~skeleton, return_distances=False, return_indices=True)
        owned = eligible[tuple(nearest)] & mask
    else:
        owned = np.zeros(mask.shape, bool)
    removed = owned & ~tube
    cleaned = mask & ~removed
    new_edt = distance_transform_edt(cleaned)
    if not np.array_equal(new_edt[protected_points], edt[protected_points]):
        raise ValueError("Protected-path thickness changed")
    assert not np.any(cleaned & ~mask) and not np.any(protected_points & ~cleaned)
    return cleaned, removed, eligible, tube, ledger


def selftest():
    mask = np.zeros((160, 160), np.uint8)
    cv2.line(mask, (80, 10), (80, 150), 1, 5)
    cv2.line(mask, (80, 50), (100, 50), 1, 11)  # short, broad side branch
    cv2.line(mask, (80, 110), (145, 110), 1, 3)  # long, slender side branch
    mask = mask.astype(bool)
    skel = skeletonize(mask)
    protected = np.zeros_like(mask)
    protected[10:151, 80] = mask[10:151, 80]
    clean, removed, _, _, ledger = filter_mask(mask, skel, protected)
    assert removed.any() and any(b["eligible"] for b in ledger)
    assert clean[110, 140] and clean[15, 80] and not clean[50, 98]
    assert not filter_mask(mask, skel, mask)[1].any()
    ring = np.zeros((80, 80), np.uint8)
    cv2.circle(ring, (40, 40), 20, 1, 3)
    assert not filter_mask(ring.astype(bool), skeletonize(ring), np.zeros_like(ring, bool))[1].any()
    empty = np.zeros((10, 10), bool)
    assert not filter_mask(empty, empty, empty)[0].any()
    assert v1.metrics(empty, ~empty, [0, 0, 10, 10])[0]["area_px2"] is None
    print("Synthetic tests: short broad spur removed; long thin/protected/loop retained; empty is null.")


def protect(m):
    bad = [p for p, h in m["protected_files"].items() if v1.sha(p) != h]
    if bad:
        raise ValueError(f"Protected input changed: {bad}")


def prepare(a):
    oldmanifest = ARCHIVE / "S03-E038-MD01/runs/S03-E038-MD01-R000/input_manifest.json"
    old = json.loads(oldmanifest.read_text())
    hashes = dict(old["protected_files"])
    for stage in STAGES:
        for arm in ARMS:
            for name in ("geometry_arrays.npz", "paths.json", "metrics.json"):
                p = INPUT / f"step{stage}" / arm["id"] / name
                hashes[str(p)] = v1.sha(p)
    for p in (oldmanifest, Path(__file__).resolve(), a.protocol.resolve()):
        hashes[str(p)] = v1.sha(p)
    manifest = dict(protocol=PROTOCOL, parameters=PARAMETERS, input_root=str(INPUT),
                    stages=list(STAGES), arms=ARMS, roi=old["roi"], common_roi=old["common_roi"],
                    frames=old["frames"], protected_files=hashes,
                    no_forecast_files_parsed=True, no_new_source_images=True)
    protect(manifest)
    a.output.mkdir(parents=True, exist_ok=False)
    save(a.output / "input_manifest.json", manifest)
    rec = receipt("E039_hashes_only")
    rec.update(protocol=PROTOCOL, ended_at_utc=now(), execution="succeeded", no_image_decode=True)
    save(a.output / "run_receipt.json", rec)


def run(a):
    start, cpu = time.monotonic(), time.process_time()
    m = json.loads(a.manifest.read_text())
    assert m["protocol"] == PROTOCOL and m["parameters"] == PARAMETERS
    assert m["stages"] == list(STAGES) and m["arms"] == ARMS
    protect(m)
    a.output.mkdir(parents=True, exist_ok=False)
    rec = receipt("E039_existing_mask_postprocess")
    rec.update(protocol=PROTOCOL, manifest_path=str(a.manifest.resolve()),
               manifest_sha256=v1.sha(a.manifest), execution="running")
    save(a.output / "run_receipt.json", rec)
    rows = []
    try:
        for stage in STAGES:
            for arm in ARMS:
                if max(time.monotonic()-start, time.process_time()-cpu) > 180:
                    raise TimeoutError("180s numeric budget")
                src = Path(m["input_root"]) / f"step{stage}" / arm["id"]
                with np.load(src / "geometry_arrays.npz") as data:
                    old = {k: data[k] for k in data.files}
                paths = json.loads((src / "paths.json").read_text())
                before = json.loads((src / "metrics.json").read_text())
                points = path_bitmap(paths["full"] + paths["common"], old["mask"].shape, m["roi"])
                clean, removed, eligible, tube, ledger = filter_mask(old["mask"], old["skeleton"], points)
                full, fullpaths, skel = v1.metrics(clean, old["safe"], m["roi"])
                common, cpaths, cskel = v1.metrics(clean, old["safe"], m["roi"], m["common_roi"])
                out = a.output / f"step{stage}" / arm["id"]
                out.mkdir(parents=True)
                np.savez_compressed(out / "geometry_arrays.npz", mask=clean, removed=removed,
                                    eligible_skeleton=eligible, protected_tube=tube,
                                    protected_points=points, skeleton=skel, common_skeleton=cskel)
                save(out / "branches.json", ledger)
                save(out / "paths.json", dict(full=fullpaths, common=cpaths))
                row = dict(stage=stage, arm=arm["id"], removed_px=int(removed.sum()),
                           removed_fraction=float(removed.sum()/old["mask"].sum()) if old["mask"].any() else None,
                           eligible_branches=sum(b["eligible"] for b in ledger), terminal_branches=len(ledger),
                           protected_points=int(points.sum()), protected_thickness_max_abs_delta_px=0.,
                           before_full=before["full"], before_common=before["common"], full=full, common=common)
                rows.append(row)
                save(out / "metrics.json", row)
        protect(m)
        summary = []
        for stage in STAGES:
            subset = [r for r in rows if r["stage"] == stage]
            base = next(r for r in subset if r["arm"] == "v1")
            s = dict(stage=stage, removed_px=base["removed_px"], removed_fraction=base["removed_fraction"],
                     eligible_branches=base["eligible_branches"], protected_points=base["protected_points"])
            for band in ("full", "common"):
                for period, key in (("before", "before_"+band), ("after", band)):
                    b = base[key]["area_px2"]
                    s[f"{band}_{period}_max_abs_relative_area_change"] = max(abs(r[key]["area_px2"]/b-1) for r in subset) if b else None
            summary.append(s)
        save(a.output / "all_metrics.json", rows)
        save(a.output / "summary.json", summary)
        rec.update(execution="succeeded", retrieval="verified_local", protected_files_unchanged=len(m["protected_files"]),
                   cases=len(rows), no_forecast_files_parsed=True)
    except Exception as exc:
        rec.update(execution="failed", error=repr(exc))
        raise
    finally:
        rec.update(ended_at_utc=now(), elapsed_wall_s=time.monotonic()-start, elapsed_cpu_s=time.process_time()-cpu)
        save(a.output / "run_receipt.json", rec)
    print(json.dumps(summary, indent=2))


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("phase", choices=("selftest", "prepare", "run"))
    p.add_argument("--output", type=Path)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--protocol", type=Path)
    a = p.parse_args()
    {"selftest": selftest, "prepare": lambda: prepare(a), "run": lambda: run(a)}[a.phase]()


if __name__ == "__main__":
    main()
