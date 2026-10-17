#!/usr/bin/env python3
"""Audit whether deterministic document-line removal preserves frozen crack gold.

This is a no-fit qualification step.  It evaluates an already-existing static-line
mask against adjudicated current-map crack geometry before that mask can be used as
training preprocessing.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


PREVIEW_MAPS = ("P020", "P008", "P002", "P009")
POOLED_RETENTION_MIN = 0.98
PER_MAP_RETENTION_MIN = 0.95


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def overlay(gray: np.ndarray, mask: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    result[mask > 0] = colour
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maps", nargs="+", default=list(PREVIEW_MAPS))
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    mask_dir = output / "masks"
    mask_dir.mkdir(exist_ok=True)

    packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"
    candidate_path = repo / "upload code/scripts/ltpp_extract_crack_candidates.py"
    b0_path = repo / "upload code/scripts/ltpp_run_crack_recognition_b0.py"
    candidate = load_module("ltpp_candidate_rules_preprocessing_audit", candidate_path)
    b0 = load_module("ltpp_b0_gold_preprocessing_audit", b0_path)

    manifest_path = packet / "adjudicated/adjudicated_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    adjudicated_by_blind: dict[str, Path] = {}
    for entry in manifest["files"]:
        label_path = packet / "adjudicated" / entry["file"]
        label = json.loads(label_path.read_text())
        adjudicated_by_blind[label["properties"]["primary_blind_id"]] = label_path

    rows = []
    pooled_gold = 0
    pooled_removed = 0
    for image_path in sorted((packet / "primary/images").glob("P*.png")):
        blind_id = image_path.stem
        gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise RuntimeError(f"cannot read {image_path}")
        _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        static = candidate.static_line_mask(ink)
        preprocessed = gray.copy()
        preprocessed[static > 0] = 255

        label_path = adjudicated_by_blind[blind_id]
        line, polygon, _families, _gold_lines = b0.gold_masks(label_path, gray.shape)
        gold = cv2.bitwise_or(line, polygon)
        removed = ((gold > 0) & (static > 0)).astype(np.uint8) * 255
        retained = ((gold > 0) & (static == 0)).astype(np.uint8) * 255
        gold_pixels = int((gold > 0).sum())
        removed_pixels = int((removed > 0).sum())
        retention = 1.0 if gold_pixels == 0 else 1.0 - removed_pixels / gold_pixels
        ink_pixels = int((ink > 0).sum())
        static_ink_pixels = int(((ink > 0) & (static > 0)).sum())
        label = json.loads(label_path.read_text())
        row = {
            "blind_id": blind_id,
            "section": label["properties"]["section"],
            "source_image_sha256": sha256(image_path),
            "adjudicated_label_sha256": sha256(label_path),
            "gold_crack_pixels": gold_pixels,
            "gold_crack_pixels_removed": removed_pixels,
            "gold_crack_retention": retention,
            "ink_pixels": ink_pixels,
            "ink_pixels_removed": static_ink_pixels,
            "ink_removal_fraction": static_ink_pixels / max(ink_pixels, 1),
            "map_gate": "NOT_APPLICABLE_ZERO_CRACK" if gold_pixels == 0 else ("PASS" if retention >= PER_MAP_RETENTION_MIN else "FAIL"),
        }
        rows.append(row)
        pooled_gold += gold_pixels
        pooled_removed += removed_pixels

        cv2.imwrite(str(mask_dir / f"{blind_id}__static_line_mask.png"), static)
        cv2.imwrite(str(mask_dir / f"{blind_id}__gold_crack.png"), gold)
        cv2.imwrite(str(mask_dir / f"{blind_id}__gold_removed.png"), removed)
        cv2.imwrite(str(mask_dir / f"{blind_id}__preprocessed.png"), preprocessed)

    pooled_retention = 1.0 - pooled_removed / max(pooled_gold, 1)
    failing_maps = [row["blind_id"] for row in rows if row["map_gate"] == "FAIL"]
    passed = pooled_retention >= POOLED_RETENTION_MIN and not failing_maps
    status = "PREPROCESSING_PRESERVATION_PASS__NO_FIT" if passed else "PREPROCESSING_PRESERVATION_FAIL__NO_TRAINING"

    by_id = {row["blind_id"]: row for row in rows}
    figure, axes = plt.subplots(len(args.maps), 4, figsize=(15.5, 1.78 * len(args.maps)), constrained_layout=True)
    if len(args.maps) == 1:
        axes = axes[None, :]
    titles = (
        "Original scan",
        "Static document mask (cyan)",
        "Gold retained (green) / erased (red)",
        "Hard-removal preprocessing",
    )
    for column, title in enumerate(titles):
        axes[0, column].set_title(title, fontsize=11, fontweight="bold")
    for row_index, blind_id in enumerate(args.maps):
        gray = cv2.imread(str(packet / "primary/images" / f"{blind_id}.png"), cv2.IMREAD_GRAYSCALE)
        static = cv2.imread(str(mask_dir / f"{blind_id}__static_line_mask.png"), cv2.IMREAD_GRAYSCALE)
        gold = cv2.imread(str(mask_dir / f"{blind_id}__gold_crack.png"), cv2.IMREAD_GRAYSCALE)
        removed = cv2.imread(str(mask_dir / f"{blind_id}__gold_removed.png"), cv2.IMREAD_GRAYSCALE)
        preprocessed = cv2.imread(str(mask_dir / f"{blind_id}__preprocessed.png"), cv2.IMREAD_GRAYSCALE)
        preservation = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        preservation[gold > 0] = (0, 170, 75)
        preservation[removed > 0] = (225, 45, 45)
        panels = (gray, overlay(gray, static, (0, 175, 215)), preservation, preprocessed)
        for column, panel in enumerate(panels):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None, aspect="auto")
            axes[row_index, column].axis("off")
        record = by_id[blind_id]
        retention_text = "zero-crack control" if record["gold_crack_pixels"] == 0 else f"gold retained={record['gold_crack_retention']:.1%} | {record['map_gate']}"
        axes[row_index, 0].text(
            0.012,
            0.95,
            f"{blind_id} | {record['section']} | {retention_text}",
            transform=axes[row_index, 0].transAxes,
            fontsize=7.4,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.9, "pad": 2.5},
        )
    figure_path = output / "document_preprocessing_preservation_audit.png"
    figure.savefig(figure_path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    receipt = {
        "status": status,
        "created_at": "2026-08-10",
        "fit_performed": False,
        "method": "existing B0 static_line_mask followed by hard white removal",
        "predeclared_gate": {
            "pooled_gold_crack_retention_min": POOLED_RETENTION_MIN,
            "each_nonzero_crack_map_retention_min": PER_MAP_RETENTION_MIN,
            "rationale": "Document preprocessing must not trade away the high-recall recognition objective before learning begins.",
        },
        "pooled_gold_crack_pixels": pooled_gold,
        "pooled_gold_crack_pixels_removed": pooled_removed,
        "pooled_gold_crack_retention": pooled_retention,
        "failing_maps": failing_maps,
        "rows": rows,
        "source_manifest_sha256": sha256(manifest_path),
        "method_source_sha256": sha256(candidate_path),
        "gold_rasterizer_source_sha256": sha256(b0_path),
        "figure": str(figure_path),
        "claim_boundary": "No-fit preprocessing audit on the frozen current-map carrier. Failure prohibits hard-removal preprocessing and does not evaluate a recognizer or forecasting method.",
    }
    (output / "preprocessing_preservation_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "status": status,
        "pooled_gold_crack_retention": pooled_retention,
        "failing_maps": failing_maps,
        "figure": str(figure_path),
    }, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
