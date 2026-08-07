#!/usr/bin/env python3
"""Detect printed dashed-grid intersections without using crack geometry.

This is an exploratory tooling diagnostic.  It rejects a candidate horizontal
or vertical line unless its sampled ink has a repeated short-dash pattern.
Long continuous ink is deliberately treated as a non-grid confounder (for
example a crack, a pavement boundary, or handwritten annotation).  It never
estimates a registration transform and cannot qualify v2 controls.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


STATUS = "EXPLORATORY_DASHED_GRID_INTERSECTION_DIAGNOSTIC__NOT_QUALIFIED"
INK_THRESHOLD = 128
EDGE_MARGIN_PX = 20
BAND_RADIUS_PX = 2
LOCAL_PEAK_RADIUS_PX = 4
MIN_CANDIDATE_SEPARATION_PX = 12
ACTIVE_FRACTION_MIN, ACTIVE_FRACTION_MAX = 0.08, 0.45
MIN_DASH_RUNS = 10
MAX_LONG_RUN_PX = 18
GAP_MEDIAN_RANGE_PX = (4.0, 16.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def binary_ink(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return (gray < INK_THRESHOLD).astype(np.uint8)


def _runs(active: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    changes = np.diff(np.r_[False, active, False].astype(np.int8))
    starts, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    return ends - starts, starts[1:] - ends[:-1]


def candidate_positions(ink: np.ndarray, axis: str) -> list[int]:
    """Return profile peaks before dashed-pattern acceptance."""
    profile = np.mean(ink[EDGE_MARGIN_PX:-EDGE_MARGIN_PX, :], axis=0) if axis == "x" else np.mean(ink[:, EDGE_MARGIN_PX:-EDGE_MARGIN_PX], axis=1)
    if len(profile) < 2 * EDGE_MARGIN_PX:
        raise ValueError("image too small for fixed edge margin")
    local = np.ones_like(profile, dtype=bool)
    for shift in range(1, LOCAL_PEAK_RADIUS_PX + 1):
        local[shift:] &= profile[shift:] >= profile[:-shift]
        local[:-shift] &= profile[:-shift] >= profile[shift:]
    ranked = sorted(np.flatnonzero(local & (profile > 0)).tolist(), key=lambda index: (-float(profile[index]), index))
    selected: list[int] = []
    for index in ranked:
        if index < EDGE_MARGIN_PX or index >= len(profile) - EDGE_MARGIN_PX:
            continue
        if all(abs(index - existing) >= MIN_CANDIDATE_SEPARATION_PX for existing in selected):
            selected.append(int(index))
    return sorted(selected)


def line_evidence(ink: np.ndarray, axis: str, position: int) -> dict:
    """Score one full candidate line by its dash / gap structure only."""
    if axis == "x":
        strip = ink[EDGE_MARGIN_PX:-EDGE_MARGIN_PX, max(0, position - BAND_RADIUS_PX):position + BAND_RADIUS_PX + 1]
    elif axis == "y":
        strip = ink[max(0, position - BAND_RADIUS_PX):position + BAND_RADIUS_PX + 1, EDGE_MARGIN_PX:-EDGE_MARGIN_PX]
    else:
        raise ValueError("axis must be x or y")
    active = np.mean(strip, axis=1 if axis == "x" else 0) >= 0.20
    runs, gaps = _runs(active)
    active_fraction = float(np.mean(active))
    median_gap = float(np.median(gaps)) if len(gaps) else None
    reasons = []
    if not ACTIVE_FRACTION_MIN <= active_fraction <= ACTIVE_FRACTION_MAX:
        reasons.append("ink_fraction_out_of_range")
    if len(runs) < MIN_DASH_RUNS:
        reasons.append("too_few_dash_runs")
    if len(runs) and int(np.max(runs)) > MAX_LONG_RUN_PX:
        reasons.append("continuous_ink_run")
    if median_gap is None or not GAP_MEDIAN_RANGE_PX[0] <= median_gap <= GAP_MEDIAN_RANGE_PX[1]:
        reasons.append("non_grid_gap_spacing")
    return {
        "axis": axis,
        "position_px": int(position),
        "accepted_dashed_grid_line": not reasons,
        "rejection_reasons": reasons,
        "active_fraction": active_fraction,
        "dash_run_count": int(len(runs)),
        "maximum_run_px": int(np.max(runs)) if len(runs) else 0,
        "median_gap_px": median_gap,
    }


def detect_dashed_grid(image: np.ndarray) -> dict:
    ink = binary_ink(image)
    candidates = {axis: [line_evidence(ink, axis, point) for point in candidate_positions(ink, axis)] for axis in ("x", "y")}
    accepted_x = [row["position_px"] for row in candidates["x"] if row["accepted_dashed_grid_line"]]
    accepted_y = [row["position_px"] for row in candidates["y"] if row["accepted_dashed_grid_line"]]
    return {"x_lines": candidates["x"], "y_lines": candidates["y"], "intersections_px": [[x, y] for y in accepted_y for x in accepted_x]}


def render_review(image: np.ndarray, detected: dict, title: str) -> np.ndarray:
    canvas = image.copy()
    for axis, colour in (("x", (255, 210, 0)), ("y", (255, 210, 0))):
        for row in detected[f"{axis}_lines"]:
            position = row["position_px"]
            if row["accepted_dashed_grid_line"]:
                if axis == "x":
                    cv2.line(canvas, (position, 0), (position, canvas.shape[0] - 1), colour, 1, cv2.LINE_AA)
                else:
                    cv2.line(canvas, (0, position), (canvas.shape[1] - 1, position), colour, 1, cv2.LINE_AA)
            elif "continuous_ink_run" in row["rejection_reasons"]:
                if axis == "x":
                    cv2.line(canvas, (position, 0), (position, canvas.shape[0] - 1), (0, 0, 255), 1, cv2.LINE_AA)
                else:
                    cv2.line(canvas, (0, position), (canvas.shape[1] - 1, position), (0, 0, 255), 1, cv2.LINE_AA)
    for x, y in detected["intersections_px"]:
        cv2.circle(canvas, (x, y), 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(canvas, (x, y), 3, (0, 220, 0), -1, cv2.LINE_AA)
    header = np.full((78, canvas.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, title, (18, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "cyan = accepted dashed grid line; green = accepted line intersection", (18, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "red = rejected because of continuous ink (crack/boundary/handwriting)", (18, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, canvas))


def write_manifest(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in paths), encoding="utf-8")


def run(input_image: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite diagnostic output: {output}")
    image = cv2.imread(str(input_image), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read input image: {input_image}")
    output.mkdir(parents=True)
    detected = detect_dashed_grid(image)
    review_path = output / "dashed_grid_intersection_review.png"
    if not cv2.imwrite(str(review_path), render_review(image, detected, "1995 dashed-grid evidence: only dashed/dashed crossings become candidate controls")):
        raise ValueError("cannot write review image")
    rows = []
    for axis in ("x", "y"):
        rows.extend(detected[f"{axis}_lines"])
    with (output / "line_evidence.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([{**row, "rejection_reasons": ";".join(row["rejection_reasons"])} for row in rows])
    (output / "dashed_grid_detection.json").write_text(json.dumps(detected, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_image": str(input_image.resolve()),
        "input_image_sha256": sha256(input_image),
        "script_sha256": sha256(Path(__file__).resolve()),
        "accepted_vertical_dashed_lines": sum(row["accepted_dashed_grid_line"] for row in detected["x_lines"]),
        "accepted_horizontal_dashed_lines": sum(row["accepted_dashed_grid_line"] for row in detected["y_lines"]),
        "candidate_intersection_count": len(detected["intersections_px"]),
        "prohibited_claims": ["v2_control_extraction", "registration_transform", "v2_final_gate", "2d_model_authorization"],
    }
    (output / "diagnostic_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# Dashed-grid intersection diagnostic\n\n"
        f"## Status\n\n`{STATUS}`\n\n"
        "## Rule\n\nA candidate control must be an intersection between one accepted horizontal and one accepted vertical printed dashed-grid line. A line with a continuous ink run longer than the frozen limit is rejected; it is not repaired, extrapolated, or replaced.\n\n"
        "## Boundary\n\nThis checks a source-image confounder only. It estimates no image transform and cannot alter v1, v2 availability, or 2-D eligibility.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.input_image.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
