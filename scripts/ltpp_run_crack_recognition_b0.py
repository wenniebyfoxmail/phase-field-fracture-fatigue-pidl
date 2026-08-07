#!/usr/bin/env python3
"""Run preregistered deterministic B0 on the frozen LTPP map packet."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from dataclasses import asdict

import cv2
import numpy as np
from skimage.morphology import skeletonize


def load_candidate_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("ltpp_candidate_rules", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load candidate rules: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def coords(geometry):
    def rec(x):
        if isinstance(x, list) and len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
            yield x
        elif isinstance(x, list):
            for y in x:
                yield from rec(y)
    yield from rec(geometry.get("coordinates", []))


def gold_masks(label_path: pathlib.Path, shape: tuple[int, int]):
    data = json.loads(label_path.read_text())
    line = np.zeros(shape, np.uint8)
    polygon = np.zeros(shape, np.uint8)
    family_masks = collections.defaultdict(lambda: np.zeros(shape, np.uint8))
    gold_lines = []
    for feature in data.get("features", []):
        prop = feature.get("properties") or {}
        family = prop.get("distress_family", "uncertain")
        if family == "uncertain":
            continue
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "LineString" and family.endswith("crack"):
            pts = []
            for x, y in geometry.get("coordinates", []):
                px = int(round(float(x) * 100.0))
                py = int(round((5.0 - float(y)) * 100.0))
                pts.append((px, py))
            if len(pts) >= 2:
                cv2.polylines(line, [np.asarray(pts, np.int32)], False, 255, 1)
                family_masks[family][line > 0] = 255
                gold_lines.append(pts)
        elif geometry.get("type") == "Polygon" and family.endswith("crack"):
            rings = []
            for ring in geometry.get("coordinates", []):
                pts = [(int(round(float(x) * 100.0)), int(round((5.0 - float(y)) * 100.0))) for x, y in ring]
                if len(pts) >= 3:
                    rings.append(np.asarray(pts, np.int32))
            if rings:
                cv2.fillPoly(polygon, rings, 255)
                family_masks[family][polygon > 0] = 255
    return line, polygon, family_masks, gold_lines


def distance_metrics(pred: np.ndarray, gold: np.ndarray, tolerance_px: int):
    pred_bin = pred > 0
    gold_bin = gold > 0
    if not pred_bin.any() and not gold_bin.any():
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "mean_matched_distance_m": 0.0, "pred_pixels": 0, "gold_pixels": 0}
    if not pred_bin.any() or not gold_bin.any():
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "mean_matched_distance_m": None, "pred_pixels": int(pred_bin.sum()), "gold_pixels": int(gold_bin.sum())}
    dt_gold = cv2.distanceTransform((~gold_bin).astype(np.uint8), cv2.DIST_L2, 3)
    dt_pred = cv2.distanceTransform((~pred_bin).astype(np.uint8), cv2.DIST_L2, 3)
    pred_d = dt_gold[pred_bin]
    gold_d = dt_pred[gold_bin]
    precision = float(np.mean(pred_d <= tolerance_px))
    recall = float(np.mean(gold_d <= tolerance_px))
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    matched = pred_d[pred_d <= tolerance_px]
    return {"precision": precision, "recall": recall, "f1": float(f1), "mean_matched_distance_m": float(np.mean(matched) / 100.0) if matched.size else None, "pred_pixels": int(pred_bin.sum()), "gold_pixels": int(gold_bin.sum())}


def endpoint_distance(gold_lines, pred: np.ndarray):
    ys, xs = np.nonzero(pred > 0)
    if len(xs) == 0 or not gold_lines:
        return None
    points = np.column_stack([xs, ys]).astype(float)
    distances = []
    for pts in gold_lines:
        for x, y in (pts[0], pts[-1]):
            distances.append(float(np.min(np.sqrt(((points - np.array([x, y])) ** 2).sum(axis=1))) / 100.0))
    return float(np.mean(distances)) if distances else None


def make_panel(original, gold, prediction, output, title):
    h, w = original.shape
    panel = np.full((h * 2, w * 2, 3), 255, np.uint8)
    panel[:h, :w] = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
    gold_img = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
    gold_img[gold > 0] = (0, 180, 0)
    panel[:h, w:] = gold_img
    pred_img = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
    pred_img[prediction > 0] = (0, 0, 220)
    panel[h:, :w] = pred_img
    overlay = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
    tp = (gold > 0) & (prediction > 0)
    fp = (gold == 0) & (prediction > 0)
    fn = (gold > 0) & (prediction == 0)
    overlay[tp] = (0, 180, 0)
    overlay[fp] = (0, 0, 220)
    overlay[fn] = (220, 80, 0)
    panel[h:, w:] = overlay
    labels = ["original", "gold", "B0 prediction", "green=TP red=FP blue=FN"]
    for i, label in enumerate(labels):
        x = (i % 2) * w + 12
        y = (i // 2) * h + 24
        cv2.putText(panel, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.imwrite(str(output), panel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    repo = args.repo_root.resolve()
    packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"
    image_dir = packet / "primary/images"
    label_dir = packet / "adjudicated/geojson"
    candidate_path = repo / "upload code/scripts/ltpp_extract_crack_candidates.py"
    candidate = load_candidate_module(candidate_path)
    args.output.mkdir(parents=True, exist_ok=True)
    visual_dir = args.output / "visual_audit"
    visual_dir.mkdir(exist_ok=True)
    manifest = json.loads((packet / "adjudicated/adjudicated_manifest.json").read_text())
    label_by_blind = {}
    for entry in manifest["files"]:
        data = json.loads((packet / "adjudicated" / entry["file"]).read_text())
        label_by_blind[data["properties"]["primary_blind_id"]] = packet / "adjudicated" / entry["file"]
    rows = []
    for image_path in sorted(image_dir.glob("P*.png")):
        blind = image_path.stem
        original = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        _, ink = cv2.threshold(original, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        static = candidate.static_line_mask(ink)
        residual = cv2.bitwise_and(ink, cv2.bitwise_not(static))
        residual[:5, :] = residual[-5:, :] = 0
        residual[:, :5] = residual[:, -5:] = 0
        high, uncertain, components = candidate.classify_components(residual)
        prediction = (skeletonize(high > 0).astype(np.uint8) * 255)
        gold_line, gold_polygon, family_masks, gold_lines = gold_masks(label_by_blind[blind], original.shape)
        gold = cv2.bitwise_or(gold_line, gold_polygon)
        center = distance_metrics(prediction, gold_line, 10)
        buffered = distance_metrics(high, gold, 10)
        section = json.loads(label_by_blind[blind].read_text())["properties"]["section"]
        stem = f"{blind}__{section}"
        cv2.imwrite(str(args.output / f"{stem}__prediction_mask.png"), prediction)
        cv2.imwrite(str(args.output / f"{stem}__gold_mask.png"), gold)
        panel = visual_dir / f"{stem}__four_panel.png"
        make_panel(original, gold, prediction, panel, stem)
        panel.with_suffix(".md").write_text(
            "# B0 four-panel audit\n\n"
            f"## Figure question\nDoes deterministic B0 recover current-map crack geometry for `{blind}`?\n\n"
            f"## Data provenance\nSource: `{image_path}` SHA-256 `{sha256(image_path)}`. Gold: `{label_by_blind[blind].name}`.\n\n"
            "## How to read\nPanels are original, adjudicated gold, B0 prediction, and TP/FP/FN overlay; green is TP, red is FP, blue is FN.\n\n"
            f"- Section: `{section}`. Centerline F1: `{center['f1']:.6f}`.\n"
            "- Limitation: B0 is a deterministic candidate baseline, not a trained recognizer; this figure does not support future-map or road-photo claims.\n"
        )
        rows.append({"blind_id": blind, "section": section, "source_sha256": sha256(image_path), "centerline": center, "buffered_mask": buffered, "endpoint_distance_m": endpoint_distance(gold_lines, prediction), "high_components": int(sum(x.high_confidence for x in components)), "uncertain_components": int(sum(not x.high_confidence for x in components))})
    by_section = collections.defaultdict(list)
    for row in rows:
        by_section[row["section"]].append(row)
    def mean(key, group):
        vals = [r[key] for r in group if r[key] is not None]
        return float(np.mean(vals)) if vals else None
    pooled_center = {k: mean(f"centerline", rows) for k in []}
    pooled_pred = np.concatenate([np.zeros(1)])
    # Pool pixels by summing counts, preserving the preregistered pixel tolerance.
    p = sum(r["centerline"]["pred_pixels"] for r in rows)
    g = sum(r["centerline"]["gold_pixels"] for r in rows)
    # Recompute pooled precision/recall from per-map counts is not valid for distance hits;
    # use the weighted mean of per-map rates and label it explicitly.
    pooled_center = {"precision_weighted": float(sum(r["centerline"]["precision"] * r["centerline"]["pred_pixels"] for r in rows) / max(p, 1)), "recall_weighted": float(sum(r["centerline"]["recall"] * r["centerline"]["gold_pixels"] for r in rows) / max(g, 1)), "f1_unweighted_map_mean": float(np.mean([r["centerline"]["f1"] for r in rows]))}
    section_summary = {}
    for section, group in sorted(by_section.items()):
        section_summary[section] = {"map_count": len(group), "centerline_f1_mean": float(np.mean([r["centerline"]["f1"] for r in group])), "centerline_recall_mean": float(np.mean([r["centerline"]["recall"] for r in group])), "mean_matched_distance_m": mean("endpoint_distance_m", group), "endpoint_distance_m_mean": mean("endpoint_distance_m", group)}
    result = {"status": "B0_EVALUATED_NO_QUALIFICATION_DECISION", "method": "B0", "method_source_sha256": sha256(candidate_path), "input_manifest_sha256": sha256(packet / "adjudicated/adjudicated_manifest.json"), "rows": rows, "pooled_centerline": pooled_center, "section_summary": section_summary, "claim_boundary": "Current frozen scanned-map carrier only; B0 output is not ground truth and does not authorize forecast or deployment claims."}
    (args.output / "b0_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "b0_metrics.md").write_text("# B0 deterministic crack-recognition result\n\nStatus: `B0_EVALUATED_NO_QUALIFICATION_DECISION`\n\n" + json.dumps({"pooled_centerline": pooled_center, "section_summary": section_summary}, indent=2) + "\n\nB0 is a deterministic baseline. The recognition gate requires comparison against B0 and endpoint/family/confounder audit; this result alone is not a qualification claim.\n")
    print(json.dumps({"maps": len(rows), "pooled_centerline": pooled_center, "sections": section_summary}))


if __name__ == "__main__":
    main()
