#!/usr/bin/env python3
"""Build read-only document-aware target previews; never fit a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


CRACK_FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
}
NEGATIVE_FAMILIES = {
    "handwritten_code_or_calculation",
    "lane_or_reference_boundary",
    "other_noncrack_distress",
}
PREVIEW_MAPS = ("P020", "P008", "P002", "P009")
WIDTH_PX = 1524
HEIGHT_PX = 500
BUFFER_PX = 7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_point(point: list[float]) -> tuple[int, int]:
    x_m, y_m = point
    return round(x_m * 100), round(HEIGHT_PX - y_m * 100)


def rasterize_feature(mask: np.ndarray, feature: dict, thickness: int) -> None:
    geometry = feature["geometry"]
    if geometry["type"] == "LineString":
        points = np.asarray([pixel_point(point) for point in geometry["coordinates"]], np.int32)
        cv2.polylines(mask, [points], False, 255, thickness=thickness, lineType=cv2.LINE_8)
        return
    if geometry["type"] == "Polygon":
        points = np.asarray([pixel_point(point) for point in geometry["coordinates"][0]], np.int32)
        cv2.fillPoly(mask, [points], 255, lineType=cv2.LINE_8)
        return
    raise ValueError(f"unsupported geometry: {geometry['type']}")


def masks_from_labels(adjudicated: dict, primary: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    crack = np.zeros((HEIGHT_PX, WIDTH_PX), np.uint8)
    negative = np.zeros_like(crack)
    wim = np.zeros_like(crack)
    counts = {"crack_features": 0, "weak_negative_features": 0, "wim_exclusion_features": 0}

    for feature in adjudicated.get("features", []):
        family = feature.get("properties", {}).get("distress_family")
        if family in CRACK_FAMILIES:
            rasterize_feature(crack, feature, thickness=3)
            counts["crack_features"] += 1

    for feature in primary.get("features", []):
        properties = feature.get("properties", {})
        family = properties.get("distress_family")
        note = str(properties.get("evidence_note", "")).lower()
        if "wim" in note:
            rasterize_feature(wim, feature, thickness=BUFFER_PX)
            counts["wim_exclusion_features"] += 1
        elif family in NEGATIVE_FAMILIES:
            rasterize_feature(negative, feature, thickness=BUFFER_PX)
            counts["weak_negative_features"] += 1

    crack_guard = cv2.dilate((crack > 0).astype(np.uint8), np.ones((21, 21), np.uint8)) > 0
    negative_conflict = ((negative > 0) & crack_guard).astype(np.uint8) * 255
    wim_conflict = ((wim > 0) & crack_guard).astype(np.uint8) * 255
    negative[crack_guard] = 0
    wim[crack_guard] = 0
    counts["weak_negative_conflict_pixels"] = int((negative_conflict > 0).sum())
    counts["wim_conflict_pixels"] = int((wim_conflict > 0).sum())
    return crack, negative, wim, negative_conflict, wim_conflict, counts


def colour_overlay(gray: np.ndarray, mask: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    image[mask > 0] = colour
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maps", nargs="+", default=list(PREVIEW_MAPS))
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"
    output = args.output.resolve()
    mask_root = output / "masks"
    mask_root.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((packet / "adjudicated/adjudicated_manifest.json").read_text())
    adjudicated_by_blind: dict[str, Path] = {}
    for entry in manifest["files"]:
        path = packet / "adjudicated" / entry["file"]
        payload = json.loads(path.read_text())
        adjudicated_by_blind[payload["properties"]["primary_blind_id"]] = path

    rows = []
    for image_path in sorted((packet / "primary/images").glob("P*.png")):
        blind_id = image_path.stem
        primary_path = packet / "primary/geojson" / f"{blind_id}.geojson"
        adjudicated_path = adjudicated_by_blind[blind_id]
        primary = json.loads(primary_path.read_text())
        adjudicated = json.loads(adjudicated_path.read_text())
        crack, negative, wim, negative_conflict, wim_conflict, counts = masks_from_labels(adjudicated, primary)
        for name, mask in (
            ("crack_target", crack),
            ("weak_negative_support", negative),
            ("wim_exclusion", wim),
            ("weak_negative_conflict", negative_conflict),
            ("wim_conflict", wim_conflict),
        ):
            cv2.imwrite(str(mask_root / f"{blind_id}__{name}.png"), mask)
        rows.append(
            {
                "blind_id": blind_id,
                "section": adjudicated["properties"]["section"],
                "source_image_sha256": sha256(image_path),
                "primary_label_sha256": sha256(primary_path),
                "adjudicated_label_sha256": sha256(adjudicated_path),
                **counts,
                "crack_target_pixels": int((crack > 0).sum()),
                "weak_negative_pixels": int((negative > 0).sum()),
                "wim_exclusion_pixels": int((wim > 0).sum()),
            }
        )

    by_id = {row["blind_id"]: row for row in rows}
    figure, axes = plt.subplots(len(args.maps), 4, figsize=(15.4, 1.72 * len(args.maps)), constrained_layout=True)
    if len(args.maps) == 1:
        axes = axes[None, :]
    titles = ("Original scan", "Adjudicated crack target", "Weak-negative: accepted / conflict", "WIM exclusion (not a target)")
    for index, title in enumerate(titles):
        axes[0, index].set_title(title, fontsize=11, fontweight="bold")

    for row_index, blind_id in enumerate(args.maps):
        gray = cv2.imread(str(packet / "primary/images" / f"{blind_id}.png"), cv2.IMREAD_GRAYSCALE)
        crack = cv2.imread(str(mask_root / f"{blind_id}__crack_target.png"), cv2.IMREAD_GRAYSCALE)
        negative = cv2.imread(str(mask_root / f"{blind_id}__weak_negative_support.png"), cv2.IMREAD_GRAYSCALE)
        wim = cv2.imread(str(mask_root / f"{blind_id}__wim_exclusion.png"), cv2.IMREAD_GRAYSCALE)
        negative_conflict = cv2.imread(str(mask_root / f"{blind_id}__weak_negative_conflict.png"), cv2.IMREAD_GRAYSCALE)
        wim_conflict = cv2.imread(str(mask_root / f"{blind_id}__wim_conflict.png"), cv2.IMREAD_GRAYSCALE)
        negative_panel = colour_overlay(gray, negative, (230, 145, 25))
        negative_panel[negative_conflict > 0] = (210, 55, 170)
        wim_panel = colour_overlay(gray, wim, (135, 85, 190))
        wim_panel[wim_conflict > 0] = (220, 45, 45)
        panels = (
            gray,
            colour_overlay(gray, crack, (0, 165, 80)),
            negative_panel,
            wim_panel,
        )
        for column, panel in enumerate(panels):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None, aspect="auto")
            axes[row_index, column].axis("off")
        record = by_id[blind_id]
        axes[row_index, 0].text(
            0.012,
            0.95,
            f"{blind_id} | {record['section']}   crack={record['crack_features']}   "
            f"weak-negative={record['weak_negative_features']}   WIM={record['wim_exclusion_features']}",
            transform=axes[row_index, 0].transAxes,
            fontsize=7.3,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.88, "pad": 2.5},
        )

    figure_path = output / "document_aware_target_preview.png"
    figure.savefig(figure_path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    receipt = {
        "status": "TARGET_PREVIEW_BUILT__DIRECT_WEAK_NEGATIVE_REUSE_NOT_QUALIFIED__NO_FIT",
        "created_at": "2026-08-10",
        "fit_performed": False,
        "heldout_scores_read_for_this_step": False,
        "source_manifest_sha256": sha256(packet / "adjudicated/adjudicated_manifest.json"),
        "rules": {
            "crack_target": "adjudicated crack families only; 3 px preview rasterization",
            "weak_negative_support": "existing primary handwriting, lane/reference boundary, and other noncrack features excluding evidence_note containing WIM; 7 px preview buffer; any pixel within 10 px of adjudicated crack target is quarantined",
            "wim_exclusion": "existing primary features whose evidence_note contains WIM; 7 px preview buffer; carrier exclusion only, never a recognition output class; any pixel within 10 px of adjudicated crack target is quarantined",
            "conflict_colour": "magenta in weak-negative panel; red in WIM panel; conflict pixels are excluded from usable support",
            "unlabeled_background": "not promoted to a semantic class by this preview",
        },
        "preview_maps": args.maps,
        "rows": rows,
        "figure": str(figure_path),
        "claim_boundary": "Target and carrier-mask preview only. This package does not authorize training, threshold selection, held-out evaluation, registration, or forecasting.",
    }
    receipt_path = output / "target_preview_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "maps": len(rows), "figure": str(figure_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
