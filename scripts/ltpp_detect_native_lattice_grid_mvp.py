#!/usr/bin/env python3
"""One-shot high-resolution, direction-aware printed-grid evidence MVP.

This exploratory detector works only on the original white-composited page
images.  It corrects the page's dominant horizontal orientation, recovers two
regularly spaced *printed-grid* line families from projection periodicity, and
renders their intersections.  It fits no inter-date transform and consumes no
crack labels or crack geometry.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
STATUS = "EXPLORATORY_NATIVE_LATTICE_GRID_MVP__NOT_QUALIFIED"
# Fixed after the preceding high-resolution source inventory, before this run.
CROP_FRACTIONS = (0.04, 0.05, 0.88, 0.95)  # x0, y0, x1, y1
PITCH_RANGE_PX = (40, 120)
SMOOTH_RADIUS_PX = 3
PHASE_REFINEMENT_FRACTION = 0.30
PITCH_NEAR_BEST_FRACTION = 0.98
MIN_LINE_COUNT_PER_FAMILY = 4


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def estimate_deskew(gray: np.ndarray) -> float:
    """Use only long, near-horizontal non-semantic ink strokes for orientation."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 1800.0,
        threshold=max(80, gray.shape[1] // 18),
        minLineLength=max(120, gray.shape[1] // 5),
        maxLineGap=max(10, gray.shape[1] // 80),
    )
    angles: list[float] = []
    if lines is not None:
        for x0, y0, x1, y1 in lines[:, 0, :]:
            angle = math.degrees(math.atan2(float(y1 - y0), float(x1 - x0)))
            while angle <= -90.0:
                angle += 180.0
            while angle > 90.0:
                angle -= 180.0
            if abs(angle) <= 12.0:
                angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def rotate_bound(image: np.ndarray, angle_deg: float) -> np.ndarray:
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    cosine, sine = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_width, new_height = int(math.ceil(height * sine + width * cosine)), int(math.ceil(height * cosine + width * sine))
    matrix[0, 2] += new_width / 2.0 - center[0]
    matrix[1, 2] += new_height / 2.0 - center[1]
    return cv2.warpAffine(image, matrix, (new_width, new_height), flags=cv2.INTER_CUBIC, borderValue=255)


def crop_bounds(shape: tuple[int, int]) -> tuple[int, int, int, int]:
    height, width = shape
    x0, y0, x1, y1 = CROP_FRACTIONS
    return int(round(width * x0)), int(round(height * y0)), int(round(width * x1)), int(round(height * y1))


def smoothed_profile(gray: np.ndarray, axis: str) -> tuple[np.ndarray, int]:
    """Ink-density profile across one grid direction, using a fixed interior crop."""
    x0, y0, x1, y1 = crop_bounds(gray.shape)
    dark = np.maximum(0.0, 255.0 - gray.astype(np.float32))
    if axis == "x":
        profile, offset = np.mean(dark[y0:y1, x0:x1], axis=0), x0
    elif axis == "y":
        profile, offset = np.mean(dark[y0:y1, x0:x1], axis=1), y0
    else:
        raise ValueError("axis must be x or y")
    kernel = np.ones(2 * SMOOTH_RADIUS_PX + 1, dtype=float) / (2 * SMOOTH_RADIUS_PX + 1)
    return np.convolve(profile, kernel, mode="same"), offset


def lattice_from_profile(profile: np.ndarray, offset: int) -> dict:
    """Recover the smallest near-optimal pitch and its phase without labels."""
    lo, hi = PITCH_RANGE_PX
    max_pitch = min(hi, len(profile) // 3)
    if max_pitch < lo:
        raise ValueError("crop too short for fixed lattice-pitch range")
    scores: list[tuple[float, int]] = []
    for pitch in range(lo, max_pitch + 1):
        # The lower quartile requires support at many repeated locations: one
        # unusually dark crack/annotation peak cannot make a period win.
        phase_support = []
        for phase in range(pitch):
            indexes = np.arange(phase, len(profile), pitch, dtype=int)
            phase_support.append(float(np.quantile(profile[indexes], 0.25)))
        scores.append((max(phase_support), pitch))
    best_score = max(score for score, _ in scores)
    pitch = min(candidate for score, candidate in scores if score >= best_score * PITCH_NEAR_BEST_FRACTION)
    phase_scores = []
    for phase in range(pitch):
        indexes = np.arange(phase, len(profile), pitch, dtype=int)
        phase_scores.append((float(np.quantile(profile[indexes], 0.25)), phase))
    _, phase = max(phase_scores)
    radius = max(1, int(round(pitch * PHASE_REFINEMENT_FRACTION)))
    positions = []
    for nominal in range(phase, len(profile), pitch):
        left, right = max(0, nominal - radius), min(len(profile), nominal + radius + 1)
        local = profile[left:right]
        positions.append(int(offset + left + int(np.argmax(local))))
    # Line membership comes from the periodic lattice, not a local crack peak.
    return {"pitch_px": int(pitch), "phase_px": int(offset + phase), "positions_px": positions, "periodicity_score": best_score}


def detect(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    angle = estimate_deskew(gray)
    deskewed = rotate_bound(gray, angle)
    x_profile, x_offset = smoothed_profile(deskewed, "x")
    y_profile, y_offset = smoothed_profile(deskewed, "y")
    vertical = lattice_from_profile(x_profile, x_offset)
    horizontal = lattice_from_profile(y_profile, y_offset)
    intersections = [[x, y] for y in horizontal["positions_px"] for x in vertical["positions_px"]]
    return {
        "deskew_angle_deg": angle,
        "deskewed_shape": list(deskewed.shape),
        "vertical_lattice": vertical,
        "horizontal_lattice": horizontal,
        "intersections_px": intersections,
    }


def render_review(source: np.ndarray, evidence: dict, title: str) -> np.ndarray:
    gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if source.ndim == 3 else source
    view = cv2.cvtColor(rotate_bound(gray, evidence["deskew_angle_deg"]), cv2.COLOR_GRAY2BGR)
    for x in evidence["vertical_lattice"]["positions_px"]:
        cv2.line(view, (x, 0), (x, view.shape[0] - 1), (255, 210, 0), 1, cv2.LINE_AA)
    for y in evidence["horizontal_lattice"]["positions_px"]:
        cv2.line(view, (0, y), (view.shape[1] - 1, y), (255, 210, 0), 1, cv2.LINE_AA)
    for x, y in evidence["intersections_px"]:
        cv2.circle(view, (x, y), 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(view, (x, y), 3, (0, 220, 0), -1, cv2.LINE_AA)
    header = np.full((78, view.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, title, (18, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "cyan = high-resolution periodic printed-grid family; green = lattice intersection", (18, 53), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "no crack labels or crack geometry used; evidence only, no registration transform", (18, 71), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, view))


def contact_sheet(panels: list[tuple[str, np.ndarray]]) -> np.ndarray:
    displayed = []
    for date, image in panels:
        panel = cv2.resize(image, (762, 289), interpolation=cv2.INTER_AREA)
        bar = np.full((26, 762, 3), 250, dtype=np.uint8)
        cv2.putText(bar, date, (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (20, 20, 20), 1, cv2.LINE_AA)
        displayed.append(np.vstack((bar, panel)))
    return np.vstack([np.hstack((displayed[index], displayed[index + 1])) for index in range(0, len(displayed), 2)])


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(source_root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite exploratory output: {output}")
    output.mkdir(parents=True)
    review_dir = output / "per_date_review"
    review_dir.mkdir()
    evidence_by_date, rows, panels = {}, [], []
    for date in DATES:
        image_path = source_root / date / "segment_0_50_white.png"
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read original white composite: {image_path}")
        evidence = detect(image)
        review = render_review(image, evidence, f"{date}: native-resolution, direction-aware printed-grid lattice")
        review_path = review_dir / f"{date}.png"
        if not cv2.imwrite(str(review_path), review):
            raise ValueError(f"cannot write review image: {review_path}")
        evidence_by_date[date] = evidence
        panels.append((date, review))
        rows.append({
            "survey_date": date,
            "source_shape": "x".join(map(str, image.shape[:2][::-1])),
            "deskew_angle_deg": evidence["deskew_angle_deg"],
            "vertical_pitch_px": evidence["vertical_lattice"]["pitch_px"],
            "horizontal_pitch_px": evidence["horizontal_lattice"]["pitch_px"],
            "vertical_lattice_lines": len(evidence["vertical_lattice"]["positions_px"]),
            "horizontal_lattice_lines": len(evidence["horizontal_lattice"]["positions_px"]),
            "candidate_intersection_count": len(evidence["intersections_px"]),
            "has_two_lattice_families": len(evidence["vertical_lattice"]["positions_px"]) >= MIN_LINE_COUNT_PER_FAMILY and len(evidence["horizontal_lattice"]["positions_px"]) >= MIN_LINE_COUNT_PER_FAMILY,
        })
    with (output / "native_lattice_evidence.json").open("w", encoding="utf-8") as handle:
        json.dump(evidence_by_date, handle, indent=2)
        handle.write("\n")
    with (output / "per_date_native_lattice_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    if not cv2.imwrite(str(output / "native_lattice_contact_sheet.png"), contact_sheet(panels)):
        raise ValueError("cannot write contact sheet")
    result = {
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root.resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "dates": rows,
        "prohibited_claims": ["independent_controls", "cross_date_correspondence", "registration_transform", "v2_final_gate", "2d_model_authorization"],
    }
    (output / "mvp_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# Native-resolution lattice-grid MVP\n\n"
        f"## Status\n\n`{STATUS}`\n\n"
        "## Frozen method\n\nOriginal `segment_0_50_white.png` pages are deskewed from their dominant long horizontal orientation. Fixed interior dark-ink projections determine each axis's periodic pitch and phase; the smallest pitch within 98% of the best autocorrelation score is used. Green points are Cartesian products of these two periodic families.\n\n"
        "## Boundary\n\nThis is visual grid evidence only. It performs no transform fit, no control-role split, no residual metric, and no v2 final audit. It cannot alter the v1 negative result or authorize a 2-D model.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source_root.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
