#!/usr/bin/env python3
"""1991-only strict grid-control preview, excluding crack/boundary-contaminated crossings.

This replaces neither v1 nor v2.  It starts from the printed page-frame
quadrilateral, clips candidates to that frame, and accepts a lattice crossing
only when both local axes show short repeated dash runs with no long continuous
ink run.  It does not read crack labels or use crack geometry to align pages.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np


PREVIEW_PATH = Path(__file__).with_name("ltpp_preview_1991_projective_rectification.py")
SPEC = importlib.util.spec_from_file_location("ltpp_1991_twist", PREVIEW_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load frame preview code: {PREVIEW_PATH}")
TWIST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TWIST)

LATTICE = TWIST.LATTICE
STATUS = "EXPLORATORY_STRICT_GRID_CONTROL_PREVIEW__NOT_QUALIFIED"
INK_THRESHOLD = 128
BAND_RADIUS_PX = 2
ARM_START_PITCH_FRACTION = 0.08
ARM_END_PITCH_FRACTION = 0.40
MIN_DASH_RUNS_PER_ARM = 2
MAX_CONTINUOUS_RUN_PITCH_FRACTION = 0.14


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _runs(active: np.ndarray) -> np.ndarray:
    changes = np.diff(np.r_[False, active, False].astype(np.int8))
    return np.flatnonzero(changes == -1) - np.flatnonzero(changes == 1)


def axis_dash_evidence(gray: np.ndarray, x: int, y: int, axis: str, pitch: int) -> dict:
    """Assess two arms of one axis without treating the central pixel as proof."""
    start, end = int(round(ARM_START_PITCH_FRACTION * pitch)), int(round(ARM_END_PITCH_FRACTION * pitch))
    if axis == "x":
        strip = (gray[max(0, y - BAND_RADIUS_PX):y + BAND_RADIUS_PX + 1, :x + end + 1] < INK_THRESHOLD)
        profile = np.mean(strip, axis=0) >= 0.20
        arms = (profile[max(0, x - end):max(0, x - start)], profile[x + start:min(len(profile), x + end)])
    elif axis == "y":
        strip = (gray[:y + end + 1, max(0, x - BAND_RADIUS_PX):x + BAND_RADIUS_PX + 1] < INK_THRESHOLD)
        profile = np.mean(strip, axis=1) >= 0.20
        arms = (profile[max(0, y - end):max(0, y - start)], profile[y + start:min(len(profile), y + end)])
    else:
        raise ValueError("axis must be x or y")
    run_sets = [_runs(arm) for arm in arms]
    max_run = max((int(np.max(runs)) if len(runs) else 0) for runs in run_sets)
    accepted = all(len(runs) >= MIN_DASH_RUNS_PER_ARM for runs in run_sets) and max_run <= int(round(MAX_CONTINUOUS_RUN_PITCH_FRACTION * pitch))
    return {"axis": axis, "accepted": accepted, "runs_per_arm": [int(len(runs)) for runs in run_sets], "max_run_px": max_run}


def strict_controls(warped: np.ndarray, evidence: dict) -> tuple[list[dict], list[dict]]:
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) if warped.ndim == 3 else warped
    x_pitch, y_pitch = evidence["vertical_lattice"]["pitch_px"], evidence["horizontal_lattice"]["pitch_px"]
    accepted, rejected = [], []
    for y in evidence["horizontal_lattice"]["positions_px"]:
        for x in evidence["vertical_lattice"]["positions_px"]:
            # The perspective warp produces a road-grid-only rectangle. Edges
            # are excluded because page borders are continuous, not dashed.
            if x < x_pitch or y < y_pitch or x > gray.shape[1] - x_pitch or y > gray.shape[0] - y_pitch:
                continue
            x_evidence = axis_dash_evidence(gray, x, y, "x", x_pitch)
            y_evidence = axis_dash_evidence(gray, x, y, "y", y_pitch)
            row = {"source_px": [int(x), int(y)], "horizontal": x_evidence, "vertical": y_evidence}
            (accepted if x_evidence["accepted"] and y_evidence["accepted"] else rejected).append(row)
    return accepted, rejected


def draw_review(source: np.ndarray, corners: np.ndarray, warped: np.ndarray, evidence: dict, accepted: list[dict], rejected: list[dict]) -> np.ndarray:
    left = cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
    cv2.polylines(left, [corners.astype(int)], True, (255, 0, 255), 5, cv2.LINE_AA)
    for index, point in enumerate(corners.astype(int), 1):
        cv2.circle(left, tuple(point), 14, (255, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(left, str(index), tuple(point + (12, -12)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2, cv2.LINE_AA)
    right = cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(right, (0, 0), (right.shape[1] - 1, right.shape[0] - 1), (255, 0, 255), 5, cv2.LINE_AA)
    for x in evidence["vertical_lattice"]["positions_px"]:
        cv2.line(right, (x, 0), (x, right.shape[0] - 1), (255, 210, 0), 1, cv2.LINE_AA)
    for y in evidence["horizontal_lattice"]["positions_px"]:
        cv2.line(right, (0, y), (right.shape[1] - 1, y), (255, 210, 0), 1, cv2.LINE_AA)
    for row in rejected:
        x, y = row["source_px"]
        cv2.drawMarker(right, (x, y), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 8, 1, cv2.LINE_AA)
    for index, row in enumerate(accepted, 1):
        x, y = row["source_px"]
        cv2.circle(right, (x, y), 12, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(right, (x, y), 10, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(right, (x, y), 7, (0, 220, 0), -1, cv2.LINE_AA)
        if index <= 12:
            cv2.putText(right, f"P{index}", (x + 12, y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 0), 1, cv2.LINE_AA)
    left_header = np.full((88, left.shape[1], 3), 250, dtype=np.uint8)
    right_header = np.full((88, right.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(left_header, "1. Original page: magenta polygon = road-grid frame only", (18, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(left_header, "Check: all 4 corners belong to the printed road grid, not side tables", (18, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(right_header, "2. Frame-clipped strict controls: cyan grid; green accepted; red rejected", (18, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(right_header, "Green requires short dashed support on both axes; red has continuous/insufficient ink", (18, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 20, 20), 1, cv2.LINE_AA)
    left, right = np.vstack((left_header, left)), np.vstack((right_header, right))
    height = max(left.shape[0], right.shape[0])
    if left.shape[0] < height:
        left = cv2.copyMakeBorder(left, 0, height - left.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    if right.shape[0] < height:
        right = cv2.copyMakeBorder(right, 0, height - right.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    return np.hstack((left, right))


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(input_image: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    source = cv2.imread(str(input_image), cv2.IMREAD_GRAYSCALE)
    if source is None:
        raise ValueError(f"cannot read {input_image}")
    corners = TWIST.frame_corners(source)
    top, right, bottom, left = (np.linalg.norm(corners[1] - corners[0]), np.linalg.norm(corners[2] - corners[1]), np.linalg.norm(corners[2] - corners[3]), np.linalg.norm(corners[3] - corners[0]))
    destination = np.array([[0, 0], [round((top + bottom) / 2), 0], [round((top + bottom) / 2), round((left + right) / 2)], [0, round((left + right) / 2)]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(corners, destination)
    warped = cv2.warpPerspective(source, matrix, (int(destination[2, 0]) + 1, int(destination[2, 1]) + 1), flags=cv2.INTER_CUBIC, borderValue=255)
    evidence = LATTICE.detect(warped)
    accepted, rejected = strict_controls(warped, evidence)
    output.mkdir(parents=True)
    review = draw_review(source, corners, warped, evidence, accepted, rejected)
    if not cv2.imwrite(str(output / "1991_strict_grid_control_review.png"), review):
        raise ValueError("cannot write review")
    result = {"status": STATUS, "input_sha256": sha256(input_image), "script_sha256": sha256(Path(__file__).resolve()), "frame_corners_px": corners.tolist(), "accepted_control_count": len(accepted), "rejected_lattice_intersection_count": len(rejected), "prohibited_claims": ["registration_transform", "v2_control_extraction", "v2_final_gate", "2d_model_authorization"]}
    (output / "strict_control_evidence.json").write_text(json.dumps({"result": result, "accepted": accepted, "rejected": rejected}, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text("# 1991 strict grid-control preview\n\n`EXPLORATORY_STRICT_GRID_CONTROL_PREVIEW__NOT_QUALIFIED`\n\nGreen points are clipped to the printed road-grid frame and require local short-dash evidence on both axes. Red crosses are deliberately excluded. This visual diagnostic does not fit or validate registration.\n", encoding="utf-8")
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input_image.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
