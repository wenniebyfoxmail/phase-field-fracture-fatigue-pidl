#!/usr/bin/env python3
"""Render the decision figure and deterministic error montage for S01-E002."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image


PRIMARY_GATE = 0.10
ORACLE_GATE = 0.20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def box_iou(a: list[float], b: list[float]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def proposal_score(row: dict) -> float:
    return math.sqrt(row["proposer_confidence"] * row["reranker_crack_probability"])


def location_map(metric: dict) -> dict[str, dict]:
    return {str(row["location"]): row for row in metric["locations"]}


def render_decision_figure(data: dict, output: Path) -> None:
    selected = data["selected_score"]
    repaired = data["repaired_score_candidates"][selected]
    base_actual = location_map(data["baseline"])
    repair_actual = location_map(repaired)
    base_oracle = location_map(data["baseline_oracle_coverage"])
    repair_oracle = location_map(data["repaired_oracle_coverage"])
    locations = [k for k in sorted(base_actual, key=int) if base_actual[k]["recall"] is not None]
    labels = locations + ["macro"]
    actual_a = [base_actual[k]["recall"] for k in locations] + [data["baseline"]["macro_location_recall"]]
    actual_b = [repair_actual[k]["recall"] for k in locations] + [repaired["macro_location_recall"]]
    oracle_a = [base_oracle[k]["recall"] for k in locations] + [data["baseline_oracle_coverage"]["macro_location_recall"]]
    oracle_b = [repair_oracle[k]["recall"] for k in locations] + [data["repaired_oracle_coverage"]["macro_location_recall"]]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), gridspec_kw={"width_ratios": [1.2, 1.2, 0.9]})
    colors = ("#767676", "#1976D2")
    x = list(range(len(labels)))
    width = 0.36
    for ax, left, right, title in [
        (axes[0], actual_a, actual_b, "Operating recall at 1 FP/image"),
        (axes[1], oracle_a, oracle_b, "Candidate-set oracle recall"),
    ]:
        ax.bar([v - width / 2 for v in x], left, width, color=colors[0], label="Full-frame baseline")
        ax.bar([v + width / 2 for v in x], right, width, color=colors[1], label="Tiled repair")
        ax.set_xticks(x, labels)
        ax.set_ylim(0, 0.78)
        ax.set_ylabel("Recall")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, loc="upper left")

    deltas = [data["primary_delta_macro_location_R_at_1FP_per_image"], data["oracle_coverage_delta_macro_location_recall"]]
    gates = [PRIMARY_GATE, ORACLE_GATE]
    names = ["Primary", "Coverage"]
    gate_colors = ["#D55E00" if deltas[0] < gates[0] else "#009E73", "#009E73" if deltas[1] >= gates[1] else "#D55E00"]
    axes[2].bar(names, deltas, color=gate_colors, width=0.58)
    for i, (delta, gate) in enumerate(zip(deltas, gates)):
        axes[2].plot([i - 0.36, i + 0.36], [gate, gate], color="black", linestyle="--", linewidth=1.5)
        axes[2].text(i, delta + 0.012, f"{delta:+.3f}", ha="center", fontweight="bold")
        axes[2].text(i, gate + 0.008, f"gate {gate:+.2f}", ha="center", va="bottom", fontsize=9)
    axes[2].set_ylim(0, 0.40)
    axes[2].set_ylabel("Macro-recall improvement")
    axes[2].set_title("Frozen gates")
    axes[2].grid(axis="y", alpha=0.25)
    axes[2].text(0, 0.015, "FAIL", ha="center", color="#D55E00", fontweight="bold")
    axes[2].text(1, 0.015, "PASS", ha="center", color="#007A55", fontweight="bold")
    fig.suptitle("S01-E002: tiling repairs coverage, but ranking leaves recall outside the FP budget", fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def index_proposals(data: dict, key: str) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    for row in data[key]:
        result[row["image_id"]].append(row)
    return result


def select_montage_cases(data: dict) -> list[tuple[str, str]]:
    targets = data["targets"]
    repaired = index_proposals(data, "repaired_proposals")
    baseline = index_proposals(data, "baseline_proposals")
    selected = data["selected_score"]
    repair_threshold = data["repaired_score_candidates"][selected]["global_score_threshold"]
    baseline_threshold = data["baseline"]["global_score_threshold"]

    negative_best: dict[str, tuple[float, str]] = {}
    for image_id, boxes in targets.items():
        if boxes or not repaired[image_id]:
            continue
        location = image_id.split("__", 1)[0].replace("reid-", "")
        candidate = max((proposal_score(row), image_id) for row in repaired[image_id])
        negative_best[location] = max(negative_best.get(location, (-1.0, "")), candidate)

    recovered: list[tuple[float, str, str]] = []
    low_rank_best: dict[str, tuple[float, str]] = {}
    for image_id, boxes in targets.items():
        if not boxes:
            continue
        location = image_id.split("__", 1)[0].replace("reid-", "")
        repair_positive_scores = [
            proposal_score(row)
            for row in repaired[image_id]
            if max(box_iou(row["box_xyxy"], target) for target in boxes) >= 0.5
        ]
        baseline_selected_hit = any(
            row["proposer_confidence"] >= baseline_threshold
            and max(box_iou(row["box_xyxy"], target) for target in boxes) >= 0.5
            for row in baseline[image_id]
        )
        repair_selected_hit = any(score >= repair_threshold for score in repair_positive_scores)
        if repair_selected_hit and not baseline_selected_hit:
            recovered.append((max(repair_positive_scores), location, image_id))
        if repair_positive_scores and not repair_selected_hit:
            candidate = (max(repair_positive_scores), image_id)
            low_rank_best[location] = max(low_rank_best.get(location, (-1.0, "")), candidate)

    recovered_distinct: list[tuple[float, str, str]] = []
    used_locations: set[str] = set()
    for row in sorted(recovered, reverse=True):
        if row[1] not in used_locations:
            recovered_distinct.append(row)
            used_locations.add(row[1])
        if len(recovered_distinct) == 2:
            break

    return [
        (negative_best["75"][1], "High-score false positive (location 75)"),
        (negative_best["1139"][1], "High-score false positive (location 1139)"),
        (recovered_distinct[0][2], f"Recovered true positive (location {recovered_distinct[0][1]})"),
        (recovered_distinct[1][2], f"Recovered true positive (location {recovered_distinct[1][1]})"),
        (low_rank_best["577"][1], "Covered target ranked below budget (location 577)"),
        (low_rank_best["220"][1], "Covered target ranked below budget (location 220)"),
    ]


def render_montage(data: dict, images_dir: Path, output: Path) -> list[dict]:
    selected = data["selected_score"]
    threshold = data["repaired_score_candidates"][selected]["global_score_threshold"]
    proposals = index_proposals(data, "repaired_proposals")
    cases = select_montage_cases(data)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    receipt = []
    for ax, (image_id, label) in zip(axes.flat, cases):
        image_path = images_dir / image_id
        image = Image.open(image_path).convert("RGB")
        ax.imshow(image)
        targets = data["targets"][image_id]
        for target in targets:
            ax.add_patch(Rectangle((target[0], target[1]), target[2] - target[0], target[3] - target[1], fill=False, edgecolor="#E41A1C", linewidth=2.5))
        ranked = sorted(proposals[image_id], key=proposal_score, reverse=True)
        top = ranked[0]
        positive = [row for row in ranked if targets and max(box_iou(row["box_xyxy"], target) for target in targets) >= 0.5]
        focus = top
        if "Recovered" in label:
            focus = next(row for row in positive if proposal_score(row) >= threshold)
        elif "below budget" in label:
            focus = positive[0]
        box = focus["box_xyxy"]
        focus_score = proposal_score(focus)
        edge = "#00A6D6" if focus_score >= threshold else "#F5A623"
        ax.add_patch(Rectangle((box[0], box[1]), box[2] - box[0], box[3] - box[1], fill=False, edgecolor=edge, linewidth=2.5))
        ax.set_title(f"{label}\nscore={focus_score:.3f}; threshold={threshold:.3f}", fontsize=10)
        ax.axis("off")
        receipt.append({"image_id": image_id, "selection_role": label, "displayed_score": focus_score})
    fig.suptitle("S01-E002 deterministic error montage — red: target; cyan: admitted; orange: below threshold", fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return receipt


def write_summary(data: dict, output_dir: Path, montage_receipt: list[dict]) -> None:
    selected = data["selected_score"]
    repaired = data["repaired_score_candidates"][selected]
    rows = []
    actual_a, actual_b = location_map(data["baseline"]), location_map(repaired)
    oracle_a, oracle_b = location_map(data["baseline_oracle_coverage"]), location_map(data["repaired_oracle_coverage"])
    for location in sorted(actual_a, key=int):
        rows.append({
            "location": location,
            "targets": actual_a[location]["targets"],
            "baseline_operating_recall": actual_a[location]["recall"],
            "repaired_operating_recall": actual_b[location]["recall"],
            "baseline_oracle_recall": oracle_a[location]["recall"],
            "repaired_oracle_recall": oracle_b[location]["recall"],
        })
    with (output_dir / "location_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "protocol": data["protocol"],
        "split": data["split"],
        "selected_score": selected,
        "baseline_operating_macro_recall": data["baseline"]["macro_location_recall"],
        "repaired_operating_macro_recall": repaired["macro_location_recall"],
        "primary_delta": data["primary_delta_macro_location_R_at_1FP_per_image"],
        "primary_gate": PRIMARY_GATE,
        "primary_pass": data["primary_pass"],
        "baseline_oracle_macro_recall": data["baseline_oracle_coverage"]["macro_location_recall"],
        "repaired_oracle_macro_recall": data["repaired_oracle_coverage"]["macro_location_recall"],
        "oracle_delta": data["oracle_coverage_delta_macro_location_recall"],
        "oracle_gate": ORACLE_GATE,
        "oracle_pass": data["oracle_coverage_delta_macro_location_recall"] >= ORACLE_GATE,
        "baseline_budget_capture_ratio": data["baseline"]["macro_location_recall"] / data["baseline_oracle_coverage"]["macro_location_recall"],
        "repaired_budget_capture_ratio": repaired["macro_location_recall"] / data["repaired_oracle_coverage"]["macro_location_recall"],
        "montage_cases": montage_receipt,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.evaluation.read_text(encoding="utf-8-sig"))
    render_decision_figure(data, args.output_dir / "F01_decision.png")
    montage_receipt = render_montage(data, args.images_dir, args.output_dir / "F02_error_montage.png")
    write_summary(data, args.output_dir, montage_receipt)


if __name__ == "__main__":
    main()
