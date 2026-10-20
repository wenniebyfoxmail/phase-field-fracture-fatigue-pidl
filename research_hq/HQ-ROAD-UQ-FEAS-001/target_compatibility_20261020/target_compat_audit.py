"""Frozen local D4 target-compatibility audit. No model inference and no Road420 input."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import PIL
from PIL import Image, ImageDraw
import scipy
from scipy.io import loadmat
from scipy.ndimage import distance_transform_edt
import skimage
from skimage.measure import label
from skimage.morphology import skeletonize

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / "target_compat_protocol.json").read_text())
LOCK = json.loads((HERE / "target_compat_data_lock.json").read_text())
RADII = [int(x) for x in PROTOCOL["radius_grid_px"]]
SHORT_SIDE = int(PROTOCOL["normalization_short_side_px"])
ZIP_CACHE: dict[str, zipfile.ZipFile] = {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archive(path: str) -> zipfile.ZipFile:
    if path not in ZIP_CACHE:
        ZIP_CACHE[path] = zipfile.ZipFile(path)
        if ZIP_CACHE[path].testzip() is not None:
            raise ValueError(f"Corrupt zip: {path}")
    return ZIP_CACHE[path]


def decode(data: bytes, mode: str) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as im:
        return np.asarray(im.convert(mode))


def parent_id(stem: str) -> str:
    bits = stem.split("_")
    if len(bits) < 3:
        raise ValueError(f"Unparseable CRACK500 crop: {stem}")
    return "_".join(bits[:-2])


def zip_inventory(zip_path: Path, split: str, excluded: set[str]) -> list[dict]:
    z = archive(str(zip_path))
    images = {Path(n).stem: n for n in z.namelist() if n.lower().endswith(".jpg")}
    masks = {Path(n).stem: n for n in z.namelist() if n.lower().endswith(".png")}
    rows = []
    if split == "testdata":
        for stem in sorted(images):
            mask_stem = stem + "_mask"
            if mask_stem in masks:
                rows.append({"source": "CRACK500", "subset": "test", "id": stem, "group": stem,
                             "image_kind": "zip", "image": images[stem], "mask_kind": "zip",
                             "mask": masks[mask_stem], "archive": str(zip_path)})
    else:
        for stem in sorted(images):
            group = parent_id(stem)
            if group not in excluded and stem in masks:
                    rows.append({"source": "CRACK500", "subset": split.removesuffix("crop"), "id": stem,
                                 "group": group, "image_kind": "zip", "image": images[stem],
                                 "mask_kind": "zip", "mask": masks[stem], "archive": str(zip_path)})
    return rows


def cfd_inventory(root: Path) -> list[dict]:
    images = {p.stem: p for p in (root / "image").glob("*.jpg")}
    mats = {p.stem: p for p in (root / "groundTruth").glob("*.mat")}
    return [{"source": "CFD", "subset": "all", "id": s, "group": s,
             "image_kind": "file", "image": str(images[s]), "mask_kind": "mat",
             "mask": str(mats[s])} for s in sorted(images.keys() & mats.keys())]


def gaps_inventory(zip_path: Path) -> list[dict]:
    z = archive(str(zip_path))
    images = {Path(n).stem: n for n in z.namelist() if n.startswith("img/") and n.lower().endswith(".jpg")}
    masks = {Path(n).stem.removesuffix("_mask"): n for n in z.namelist()
             if n.startswith("gt/") and n.lower().endswith("_mask.png")}
    return [{"source": "GAPS384", "subset": "all", "id": s, "group": s,
             "image_kind": "zip", "image": images[s], "mask_kind": "zip",
             "mask": masks[s], "archive": str(zip_path)} for s in sorted(images.keys() & masks.keys())]


def load_mask(row: dict) -> np.ndarray:
    if row["mask_kind"] == "zip":
        a = decode(archive(row["archive"]).read(row["mask"]), "L")
        vals = set(np.unique(a).tolist())
        if not vals.issubset({0, 255}):
            raise ValueError(f"Nonbinary mask {row['source']}/{row['id']}: {sorted(vals)[:12]}")
        return a > 0
    obj = loadmat(row["mask"], squeeze_me=True, struct_as_record=False)["groundTruth"]
    a = np.asarray(obj.Boundaries)
    vals = set(np.unique(a).tolist())
    if not vals.issubset({0, 1}):
        raise ValueError(f"Nonbinary CFD MAT {row['id']}: {sorted(vals)[:12]}")
    return a > 0


def load_rgb(row: dict) -> np.ndarray:
    if row["image_kind"] == "zip":
        return decode(archive(row["archive"]).read(row["image"]), "RGB")
    with Image.open(row["image"]) as im:
        return np.asarray(im.convert("RGB"))


def normalise_mask(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    scale = SHORT_SIDE / min(h, w)
    nh, nw = max(1, round(h * scale)), max(1, round(w * scale))
    im = Image.fromarray((mask * 255).astype(np.uint8)).resize((nw, nh), Image.Resampling.NEAREST)
    return np.asarray(im) > 0


def split_for(source: str, group: str) -> str:
    value = int(hashlib.sha256(f"20261020|{source}|{group}".encode()).hexdigest(), 16)
    return "fit" if value % 2 == 0 else "eval"


def dice(a: np.ndarray, b: np.ndarray) -> float:
    den = int(a.sum() + b.sum())
    return 1.0 if den == 0 else float(2 * np.logical_and(a, b).sum() / den)


def analyse(row: dict) -> dict:
    native = load_mask(row)
    mask = normalise_mask(native)
    h, w = mask.shape
    empty = not bool(mask.any())
    result = {k: row[k] for k in ("source", "subset", "id", "group")}
    result.update({"split": split_for(row["source"], row["group"]), "native_h": native.shape[0],
                   "native_w": native.shape[1], "norm_h": h, "norm_w": w,
                   "empty": empty, "foreground_fraction": float(mask.mean()),
                   "native_2px_short_fraction": float(2 / min(native.shape)),
                   "native_4px_short_fraction": float(4 / min(native.shape))})
    if empty:
        result.update({"component_count": 0, "skeleton_pixels": 0, "skeleton_fraction": 0.0,
                       "width_median_px": math.nan, "width_p90_px": math.nan,
                       "border_fraction": 0.0, "oracle_radius_px": 0, "oracle_dice": 1.0})
        for radius in RADII:
            result[f"dice_r{radius}"] = 1.0
        return result
    skel = skeletonize(mask)
    dist_inside = distance_transform_edt(mask)
    widths = 2.0 * dist_inside[skel]
    dist_from_skel = distance_transform_edt(~skel)
    border_count = int(mask[0].sum() + mask[-1].sum() + mask[:, 0].sum() + mask[:, -1].sum())
    result.update({"component_count": int(label(mask, connectivity=2).max()),
                   "skeleton_pixels": int(skel.sum()), "skeleton_fraction": float(skel.mean()),
                   "width_median_px": float(np.median(widths)), "width_p90_px": float(np.quantile(widths, .9)),
                   "border_fraction": float(border_count / mask.sum())})
    scores = []
    for radius in RADII:
        score = dice(dist_from_skel <= radius, mask)
        result[f"dice_r{radius}"] = score
        scores.append(score)
    best = max(range(len(RADII)), key=lambda i: (scores[i], -RADII[i]))
    result["oracle_radius_px"] = RADII[best]
    result["oracle_dice"] = scores[best]
    return result


def group_mean(rows: list[dict], key: str) -> float:
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(float(row[key]))
    return float(np.mean([np.mean(values) for values in groups.values()]))


def choose_radius(rows: list[dict]) -> tuple[int, dict[int, float]]:
    scores = {radius: group_mean(rows, f"dice_r{radius}") for radius in RADII}
    return max(RADII, key=lambda radius: (scores[radius], -radius)), scores


def grouped_bootstrap(rows: list[dict], source_key: str, global_key: str, n: int = 4000) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(row)
    group_rows = list(groups.values())
    paired = np.array([[np.mean([r[source_key] for r in rs]), np.mean([r[global_key] for r in rs])]
                       for rs in group_rows], dtype=float)
    rng = np.random.default_rng(int(PROTOCOL["seed"]))
    deltas = np.empty(n)
    for i in range(n):
        sample = paired[rng.integers(0, len(paired), len(paired))]
        deltas[i] = np.mean(sample[:, 0] - sample[:, 1])
    return {"source_minus_global_mean": float(np.mean(paired[:, 0] - paired[:, 1])),
            "bootstrap_95_ci": [float(np.quantile(deltas, .025)), float(np.quantile(deltas, .975))],
            "bootstrap_replicates": n}


def fixed_selection(source_rows: list[dict], source_radius: int, global_radius: int, count: int) -> list[dict]:
    candidates = [r for r in source_rows if r["split"] == "eval" and not r["empty"]]
    chosen: list[dict] = []
    buckets = [sorted(candidates, key=lambda r: (r["oracle_dice"], r["id"]))[:2],
               sorted(candidates, key=lambda r: (-(r[f"dice_r{source_radius}"] - r[f"dice_r{global_radius}"]), r["id"]))[:2],
               sorted(candidates, key=lambda r: (r["width_median_px"], r["id"]))[:1],
               sorted(candidates, key=lambda r: (-r["width_median_px"], r["id"]))[:1]]
    seen = set()
    for bucket in buckets:
        for row in bucket:
            if row["id"] not in seen:
                seen.add(row["id"]); chosen.append(row)
    filler = sorted(candidates, key=lambda r: hashlib.sha256(f"visual|{r['source']}|{r['id']}".encode()).hexdigest())
    for row in filler:
        if len(chosen) >= count:
            break
        if row["id"] not in seen:
            seen.add(row["id"]); chosen.append(row)
    empties = [r for r in source_rows if r["split"] == "eval" and r["empty"]]
    if empties:
        chosen.append(sorted(empties, key=lambda r: r["id"])[0])
    return chosen


def make_panel(selected: list[dict], locator: dict[tuple[str, str], dict], radius: int, path: Path) -> None:
    cell_w, cell_h, cols = 420, 300, 2
    rows_n = math.ceil(len(selected) / cols)
    canvas = Image.new("RGB", (cell_w * cols, cell_h * rows_n), "white")
    draw = ImageDraw.Draw(canvas)
    for i, metric in enumerate(selected):
        row = locator[(metric["source"], metric["id"])]
        rgb, native_mask = load_rgb(row), load_mask(row)
        h, w = native_mask.shape
        if rgb.shape[:2] != (h, w):
            raise ValueError(f"Image-mask shape mismatch {row['source']}/{row['id']}")
        scale = SHORT_SIDE / min(h, w); nh, nw = round(h * scale), round(w * scale)
        rgb_n = np.asarray(Image.fromarray(rgb).resize((nw, nh), Image.Resampling.BILINEAR))
        mask = normalise_mask(native_mask); skel = skeletonize(mask) if mask.any() else mask
        rendered = distance_transform_edt(~skel) <= radius if mask.any() else mask
        show = rgb_n.astype(float)
        # published mask red, source-rendered mask green, skeleton blue
        overlay = np.zeros_like(show); overlay[..., 0] = mask * 255; overlay[..., 1] = rendered * 255; overlay[..., 2] = skel * 255
        active = np.logical_or(mask, rendered)
        show[active] = .55 * show[active] + .45 * overlay[active]
        thumb = Image.fromarray(np.clip(show, 0, 255).astype(np.uint8)); thumb.thumbnail((cell_w, cell_h - 44))
        x, y = (i % cols) * cell_w, (i // cols) * cell_h
        canvas.paste(thumb, (x, y))
        text = (f"{metric['id']}  eval  r={radius}  fg={metric['foreground_fraction']:.4f}\n"
                f"oracle={metric['oracle_dice']:.3f}  fixed={metric[f'dice_r{radius}']:.3f}  width50={metric['width_median_px']:.2f}")
        draw.text((x + 4, y + cell_h - 40), text, fill="black")
    canvas.save(path)


def plot_summary(rows: list[dict], summary: dict, path: Path) -> None:
    sources = ["CRACK500", "CFD", "GAPS384"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, metric, title in zip(axes, ["foreground_fraction", "width_median_px", "oracle_dice"],
                                 ["Foreground fraction", "Median width at skeleton (normalised px)", "Per-image oracle Dice"]):
        data = [[r[metric] for r in rows if r["source"] == s and not r["empty"] and math.isfinite(r[metric])]
                for s in sources]
        ax.boxplot(data, tick_labels=sources, showfliers=False)
        ax.set_title(title); ax.grid(alpha=.2, axis="y")
        if metric == "foreground_fraction": ax.set_yscale("log")
    fig.suptitle(f"D4 target geometry; global fitted radius = {summary['global_radius_px']} px at short side 512")
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def verify_lock(train: Path, val: Path, test: Path, gaps: Path, cfd: Path) -> dict:
    checks = {}
    for name, path, expected in [
        ("trainzip", train, LOCK["crack500"]["trainzip"]), ("valzip", val, LOCK["crack500"]["valzip"]),
        ("testzip", test, LOCK["crack500"]["testzip"]), ("gapszip", gaps, LOCK["gaps384"])]:
        observed = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        if observed["bytes"] != expected["bytes"] or observed["sha256"] != expected["sha256"]:
            raise ValueError(f"Identity mismatch {name}: {observed}")
        checks[name] = observed
    images = {p.stem: p for p in (cfd / "image").glob("*.jpg")}; mats = {p.stem: p for p in (cfd / "groundTruth").glob("*.mat")}
    file_rows = []
    for stem in sorted(images.keys() & mats.keys()):
        for p in (images[stem], mats[stem]):
            file_rows.append([p.relative_to(cfd).as_posix(), p.stat().st_size, sha256(p)])
    observed_cfd = {"labeled_pairs": len(images.keys() & mats.keys()), "files": len(file_rows),
                    "bytes": sum(r[1] for r in file_rows),
                    "aggregate_sha256": hashlib.sha256(json.dumps(file_rows, separators=(",", ":")).encode()).hexdigest()}
    for key in ("labeled_pairs", "files", "bytes", "aggregate_sha256"):
        if observed_cfd[key] != LOCK["cfd"][key]: raise ValueError(f"CFD lock mismatch {key}")
    checks["cfd"] = observed_cfd
    return checks


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trainzip", required=True); p.add_argument("--valzip", required=True); p.add_argument("--testzip", required=True)
    p.add_argument("--cfd", required=True); p.add_argument("--gapszip", required=True); p.add_argument("--out", required=True)
    a = p.parse_args(); started = time.time(); out = Path(a.out)
    if out.exists(): raise FileExistsError(f"Output collision: {out}")
    out.mkdir(parents=True)
    train, val, test, cfd, gaps = map(Path, [a.trainzip, a.valzip, a.testzip, a.cfd, a.gapszip])
    identities = verify_lock(train, val, test, gaps, cfd)
    rows_raw = []
    rows_raw += zip_inventory(train, "traincrop", set(PROTOCOL["crack500_excluded_train_parents"]))
    rows_raw += zip_inventory(val, "valcrop", set(PROTOCOL["crack500_excluded_val_parents"]))
    rows_raw += zip_inventory(test, "testdata", set())
    rows_raw += cfd_inventory(cfd); rows_raw += gaps_inventory(gaps)
    counts = {s: sum(r["source"] == s for r in rows_raw) for s in PROTOCOL["expected"] if not s.endswith("_empty")}
    for source, count in counts.items():
        if count != PROTOCOL["expected"][source]: raise ValueError(f"Cohort mismatch {source}: {count}")
    metrics = []
    for i, row in enumerate(rows_raw, 1):
        metrics.append(analyse(row))
        if i % 100 == 0: print(f"analysed {i}/{len(rows_raw)}", flush=True)
        if time.time() - started > PROTOCOL["wall_clock_cap_hours"] * 3600: raise TimeoutError("D4 wall-clock cap")
    empty_gaps = sum(r["source"] == "GAPS384" and r["empty"] for r in metrics)
    if empty_gaps != PROTOCOL["expected"]["GAPS384_empty"]: raise ValueError(f"GAPS empty mismatch: {empty_gaps}")
    for source in ("CRACK500", "CFD", "GAPS384"):
        group_splits = defaultdict(set)
        for r in metrics:
            if r["source"] == source: group_splits[r["group"]].add(r["split"])
        if any(len(v) != 1 for v in group_splits.values()): raise ValueError(f"Group leakage: {source}")
    source_radii, source_fit_scores = {}, {}
    for source in ("CRACK500", "CFD", "GAPS384"):
        fit = [r for r in metrics if r["source"] == source and r["split"] == "fit" and not r["empty"]]
        source_radii[source], source_fit_scores[source] = choose_radius(fit)
    global_fit = {radius: float(np.mean([source_fit_scores[s][radius] for s in source_radii])) for radius in RADII}
    global_radius = max(RADII, key=lambda radius: (global_fit[radius], -radius))
    summary = {"run_id": PROTOCOL["run_id"], "geometry_decision": None, "global_radius_px": global_radius,
               "global_fit_scores": global_fit, "sources": {}}
    all_source_adequate, all_global_adequate = True, True
    for source, radius in source_radii.items():
        eval_rows = [r for r in metrics if r["source"] == source and r["split"] == "eval" and not r["empty"]]
        oracle = group_mean(eval_rows, "oracle_dice"); src = group_mean(eval_rows, f"dice_r{radius}"); glob = group_mean(eval_rows, f"dice_r{global_radius}")
        src_ret = src / oracle; global_ret = glob / src
        src_ok = oracle >= PROTOCOL["decision"]["oracle_mean_dice_floor"] and src_ret >= PROTOCOL["decision"]["source_renderer_oracle_retention"]
        glob_ok = global_ret >= PROTOCOL["decision"]["global_renderer_source_retention"]
        all_source_adequate &= src_ok; all_global_adequate &= glob_ok
        source_all = [r for r in metrics if r["source"] == source]
        width_values = [r["width_median_px"] for r in source_all if not r["empty"]]
        summary["sources"][source] = {
            "masks": len(source_all), "nonempty": sum(not r["empty"] for r in source_all), "empty": sum(r["empty"] for r in source_all),
            "groups": len({r["group"] for r in source_all}), "fit_groups": len({r["group"] for r in source_all if r["split"] == "fit"}),
            "eval_groups": len({r["group"] for r in source_all if r["split"] == "eval"}), "source_radius_px": radius,
            "oracle_eval_mean_dice": oracle, "source_eval_mean_dice": src, "global_eval_mean_dice": glob,
            "source_oracle_retention": src_ret, "global_source_retention": global_ret,
            "source_renderer_adequate": bool(src_ok), "global_renderer_adequate": bool(glob_ok),
            "foreground_fraction_median": float(np.median([r["foreground_fraction"] for r in source_all])),
            "width_median_of_image_medians_px": float(np.median(width_values)),
            "width_p10_p90_of_image_medians_px": [float(np.quantile(width_values, .1)), float(np.quantile(width_values, .9))],
            "native_2px_short_fraction_median": float(np.median([r["native_2px_short_fraction"] for r in source_all])),
            "paired_source_vs_global": grouped_bootstrap(eval_rows, f"dice_r{radius}", f"dice_r{global_radius}")
        }
    summary["geometry_decision"] = ("ROUTE_A_COMMON_RENDERER_NUMERICALLY_SUPPORTED" if all_source_adequate and all_global_adequate
                                    else "ROUTE_B_SOURCE_SPECIFIC_RENDERERS_NUMERICALLY_SUPPORTED" if all_source_adequate
                                    else "STOP_CENTRELINE_WIDTH_RENDERER_NOT_ADEQUATE")
    summary["visual_audit_status"] = "PENDING_FIXED_PANEL_REVIEW_CAN_ONLY_DOWNGRADE"
    locator = {(r["source"], r["id"]): r for r in rows_raw}
    selections = {}
    for source, radius in source_radii.items():
        selected = fixed_selection([r for r in metrics if r["source"] == source], radius, global_radius,
                                   int(PROTOCOL["visual_items_per_source"]))
        selections[source] = [{k: (None if isinstance(r[k], float) and not math.isfinite(r[k]) else r[k])
                                for k in ("id", "group", "split", "empty", "oracle_dice", "oracle_radius_px",
                                          "foreground_fraction", "width_median_px")}
                              | {"source_radius_px": radius, "source_radius_dice": r[f"dice_r{radius}"],
                                 "global_radius_px": global_radius, "global_radius_dice": r[f"dice_r{global_radius}"]}
                              for r in selected]
        make_panel(selected, locator, radius, out / f"visual_panel_{source}.png")
    fields = list(metrics[0].keys())
    with (out / "per_mask_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(metrics)
    (out / "source_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    (out / "visual_selection.json").write_text(json.dumps(selections, indent=2, allow_nan=False))
    plot_summary(metrics, summary, out / "target_geometry_summary.png")
    receipt = {"run_id": PROTOCOL["run_id"], "status": "COMPLETED", "started_unix": started,
               "finished_unix": time.time(), "duration_seconds": time.time() - started,
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "pillow": PIL.__version__,
                               "scipy": scipy.__version__, "skimage": skimage.__version__, "matplotlib": matplotlib.__version__},
               "identity_checks": identities, "cohort_counts": counts, "gaps_empty": empty_gaps,
               "road420_accessed": False, "training": False, "gpu": False, "remote_compute": False}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(summary, indent=2))
    for z in ZIP_CACHE.values(): z.close()


if __name__ == "__main__":
    main()
