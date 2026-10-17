#!/usr/bin/env python3
"""Render corrected, read-only B1 visual evidence for amendment review.

This script does not train, tune, or overwrite frozen B0/B1 outputs. It fixes
only the presentation label in a new derived review figure: the frozen B1
four-panel images inherited the literal label "B0 prediction" from the B0
panel helper even though the supplied recognition output was B1.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_MAPS = ("P020", "P008", "P002", "P019")


def overlay(base: np.ndarray, mask: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    image = cv2.cvtColor(base, cv2.COLOR_GRAY2RGB)
    visible = cv2.dilate((mask > 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    image[visible] = colour
    return image


def tolerance_overlay(base: np.ndarray, gold: np.ndarray, pred: np.ndarray, tolerance: int = 10) -> np.ndarray:
    gold_bin = gold > 0
    pred_bin = pred > 0
    distance_to_gold = cv2.distanceTransform((~gold_bin).astype(np.uint8), cv2.DIST_L2, 3)
    distance_to_pred = cv2.distanceTransform((~pred_bin).astype(np.uint8), cv2.DIST_L2, 3)
    tp = pred_bin & (distance_to_gold <= tolerance)
    fp = pred_bin & (distance_to_gold > tolerance)
    fn = gold_bin & (distance_to_pred > tolerance)
    image = cv2.cvtColor(base, cv2.COLOR_GRAY2RGB)
    for mask, colour in ((tp, (0, 170, 80)), (fp, (220, 45, 45)), (fn, (45, 100, 220))):
        visible = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        image[visible] = colour
    return image


def find_prediction(b1_root: Path, blind_id: str) -> Path:
    matches = list(b1_root.glob(f"folds/*/{blind_id}__*__prediction_centerline.png"))
    if len(matches) != 1:
        raise ValueError(f"expected one B1 centerline for {blind_id}, found {len(matches)}")
    return matches[0]


def find_gold(b0_root: Path, blind_id: str, section: str) -> Path:
    path = b0_root / f"{blind_id}__{section}__gold_mask.png"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--maps", nargs="+", default=list(DEFAULT_MAPS))
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"
    b0_root = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b0_v1_20260806"
    b1_root = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_v1_20260807"
    audit_path = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/existing_noncrack_overlap_proxy.json"

    metrics = json.loads((b1_root / "b1_metrics.json").read_text())
    metric_by_map = {row["blind_id"]: row for row in metrics["rows"]}
    proxy = json.loads(audit_path.read_text())
    proxy_by_map = {row["blind_id"]: row for row in proxy["map_rows"]}

    figure, axes = plt.subplots(len(args.maps), 4, figsize=(15.4, 1.72 * len(args.maps)), constrained_layout=True)
    if len(args.maps) == 1:
        axes = axes[None, :]
    headings = ("Original scan", "Adjudicated gold", "Frozen B1 recognition output", "10 px: TP / FP / FN")
    for column, heading in enumerate(headings):
        axes[0, column].set_title(heading, fontsize=11, fontweight="bold")

    for row_index, blind_id in enumerate(args.maps):
        row = metric_by_map[blind_id]
        section = row["section"]
        original = cv2.imread(str(packet / "primary/images" / f"{blind_id}.png"), cv2.IMREAD_GRAYSCALE)
        gold = cv2.imread(str(find_gold(b0_root, blind_id, section)), cv2.IMREAD_GRAYSCALE)
        pred = cv2.imread(str(find_prediction(b1_root, blind_id)), cv2.IMREAD_GRAYSCALE)
        if original is None or gold is None or pred is None:
            raise ValueError(f"failed to read visual inputs for {blind_id}")
        p = proxy_by_map[blind_id]["categories"]
        boundary = p["lane_or_reference_boundary"]["pred_fraction_near"]
        handwriting = p["handwritten_code_or_calculation"]["pred_fraction_near"]
        center = row["centerline"]
        panels = (
            original,
            overlay(original, gold, (0, 170, 80)),
            overlay(original, pred, (210, 45, 65)),
            tolerance_overlay(original, gold, pred),
        )
        for column, panel in enumerate(panels):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None, aspect="auto")
            axes[row_index, column].axis("off")
        axes[row_index, 0].text(
            0.012,
            0.95,
            f"{blind_id} | {section}   F1={center['f1']:.3f}  P={center['precision']:.3f}  R={center['recall']:.3f}\n"
            f"boundary proxy={boundary:.1%}  handwriting proxy={handwriting:.1%}",
            transform=axes[row_index, 0].transAxes,
            fontsize=7.3,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.88, "pad": 2.5},
        )

    evidence_path = args.output_dir / "b1_visual_evidence_examples.png"
    figure.savefig(evidence_path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    sections = sorted(metrics["section_summary"])
    f1 = [metrics["section_summary"][section]["centerline_f1_mean"] for section in sections]
    recall = [metrics["section_summary"][section]["centerline_recall_mean"] for section in sections]
    boundary = [proxy["section_aggregate"][section]["categories"]["lane_or_reference_boundary"]["pred_fraction_near"] for section in sections]
    handwriting = [proxy["section_aggregate"][section]["categories"]["handwritten_code_or_calculation"]["pred_fraction_near"] for section in sections]
    x = np.arange(len(sections))
    summary, axis = plt.subplots(figsize=(11.5, 4.8), constrained_layout=True)
    width = 0.19
    axis.bar(x - 1.5 * width, f1, width, label="Mean centerline F1", color="#0072B2")
    axis.bar(x - 0.5 * width, recall, width, label="Mean centerline recall", color="#009E73")
    axis.bar(x + 0.5 * width, boundary, width, label="Boundary proxy overlap", color="#E69F00")
    axis.bar(x + 1.5 * width, handwriting, width, label="Handwriting proxy overlap", color="#CC79A7")
    axis.axhline(0.70, color="#666666", linewidth=1.2, linestyle="--", label="Recall floor 0.70")
    axis.set_xticks(x, sections)
    axis.set_ylim(0, 1.02)
    axis.set_ylabel("Fraction")
    axis.set_title("Frozen B1 performance and existing-label confounder proxies by held-out section")
    axis.grid(axis="y", color="#dddddd", linewidth=0.7)
    axis.legend(ncol=3, frameon=False, loc="upper center")
    summary_path = args.output_dir / "b1_section_failure_summary.png"
    summary.savefig(summary_path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(summary)

    receipt = {
        "status": "DERIVED_REVIEW_FIGURES_ONLY",
        "selected_maps": args.maps,
        "sources": {
            "original": str(packet / "primary/images"),
            "gold": str(b0_root),
            "b1_recognition_outputs": str(b1_root),
            "metrics": str(b1_root / "b1_metrics.json"),
            "proxy_audit": str(audit_path),
        },
        "outputs": [str(evidence_path), str(summary_path)],
        "claim_boundary": "Current-map recognition review only; no fit, tuning, registration, or forecast claim.",
        "known_issue": "Frozen B1 four-panel images inherit the literal B0 prediction label; these derived figures relabel it as recognition output without overwriting frozen assets.",
    }
    (args.output_dir / "review_figure_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
