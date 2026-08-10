#!/usr/bin/env python3
"""One-shot exploratory road-frame candidates from regular printed-grid envelopes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
STATUS = "EXPLORATORY_LATTICE_ENVELOPE_FRAME_RANGE_MVP__NOT_QUALIFIED"
PHASE_TOLERANCE_FRACTION = 0.18
RUN_GAP_MAX_FRACTION = 1.65
ONE_MISSING_GAP_RANGE = (1.65, 2.35)
SNAP_WINDOW_FRACTION = 1.10
MIN_RUN_POSITIONS = 6
ASPECT_RANGE = (2.5, 4.0)
INK_THRESHOLD = 128
BAND_RADIUS_PX = 2

LATTICE_PATH = Path(__file__).with_name("ltpp_detect_native_lattice_grid_mvp.py")
SPEC = importlib.util.spec_from_file_location("ltpp_native_lattice", LATTICE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load lattice helper: {LATTICE_PATH}")
LATTICE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LATTICE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def circular_distance(value: int, phase: int, pitch: int) -> float:
    return abs(((value - phase + pitch / 2.0) % pitch) - pitch / 2.0)


def main_lattice_run(positions: list[int], pitch: int) -> list[int]:
    """Choose the largest phase-compatible dense run, with one fixed missing-line bridge."""
    if pitch <= 0:
        raise ValueError("pitch must be positive")
    winner: tuple[tuple[int, float], list[int]] | None = None
    for phase in range(pitch):
        compatible = sorted(value for value in positions if circular_distance(value, phase, pitch) <= PHASE_TOLERANCE_FRACTION * pitch)
        chunks: list[list[int]] = []
        current: list[int] = []
        for value in compatible:
            if current and value - current[-1] > RUN_GAP_MAX_FRACTION * pitch:
                chunks.append(current); current = []
            current.append(value)
        if current:
            chunks.append(current)
        for index, chunk in enumerate(chunks):
            bridged = list(chunk)
            if index and ONE_MISSING_GAP_RANGE[0] * pitch <= chunk[0] - chunks[index - 1][-1] <= ONE_MISSING_GAP_RANGE[1] * pitch:
                bridged.insert(0, chunks[index - 1][-1])
            key = (len(bridged), (bridged[-1] - bridged[0]) / pitch)
            if winner is None or key > winner[0]:
                winner = (key, bridged)
    if winner is None:
        return []
    return winner[1]


def longest_run(active: np.ndarray) -> int:
    changes = np.diff(np.r_[False, active, False].astype(np.int8))
    starts, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    return int(np.max(ends - starts)) if len(starts) else 0


def continuous_support_profiles(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ink = gray < INK_THRESHOLD
    vertical = np.array([longest_run(np.mean(ink[:, max(0, x - BAND_RADIUS_PX):x + BAND_RADIUS_PX + 1], axis=1) >= 0.20) for x in range(gray.shape[1])])
    horizontal = np.array([longest_run(np.mean(ink[max(0, y - BAND_RADIUS_PX):y + BAND_RADIUS_PX + 1, :], axis=0) >= 0.20) for y in range(gray.shape[0])])
    return vertical, horizontal


def snap(profile: np.ndarray, anchor: int, pitch: int) -> tuple[int, int]:
    radius = int(round(SNAP_WINDOW_FRACTION * pitch))
    left, right = max(0, anchor - radius), min(len(profile), anchor + radius + 1)
    if left >= right:
        raise ValueError("empty snap window")
    index = int(left + np.argmax(profile[left:right]))
    return index, int(profile[index])


def candidate(gray: np.ndarray) -> dict:
    evidence = LATTICE.detect(gray)
    vertical = evidence["vertical_lattice"]
    horizontal = evidence["horizontal_lattice"]
    x_run = main_lattice_run(vertical["positions_px"], vertical["pitch_px"])
    y_run = main_lattice_run(horizontal["positions_px"], horizontal["pitch_px"])
    result = {"deskew_angle_deg": evidence["deskew_angle_deg"], "vertical_pitch_px": vertical["pitch_px"], "horizontal_pitch_px": horizontal["pitch_px"], "vertical_run_positions_px": x_run, "horizontal_run_positions_px": y_run}
    if len(x_run) < MIN_RUN_POSITIONS or len(y_run) < MIN_RUN_POSITIONS:
        result |= {"status": "NO_CANDIDATE__FAIL_CLOSED", "error": "insufficient dominant lattice-run positions"}
        return result
    deskewed = LATTICE.rotate_bound(gray, evidence["deskew_angle_deg"])
    vertical_support, horizontal_support = continuous_support_profiles(deskewed)
    left, left_support = snap(vertical_support, x_run[0], vertical["pitch_px"])
    right, right_support = snap(vertical_support, x_run[-1], vertical["pitch_px"])
    top, top_support = snap(horizontal_support, y_run[0], horizontal["pitch_px"])
    bottom, bottom_support = snap(horizontal_support, y_run[-1], horizontal["pitch_px"])
    aspect = (right - left) / max(1, bottom - top)
    result |= {"rectangle_deskewed_px": {"left": left, "top": top, "right": right, "bottom": bottom}, "support_px": {"left": left_support, "right": right_support, "top": top_support, "bottom": bottom_support}, "aspect": aspect}
    if left >= right or top >= bottom or not ASPECT_RANGE[0] <= aspect <= ASPECT_RANGE[1]:
        result |= {"status": "NO_CANDIDATE__FAIL_CLOSED", "error": "unordered sides or aspect outside frozen range"}
    else:
        result["status"] = "REQUIRES_HUMAN_RANGE_REVIEW"
    return result


def render_review(date: str, gray: np.ndarray, result: dict) -> np.ndarray:
    deskewed = LATTICE.rotate_bound(gray, result["deskew_angle_deg"])
    view = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
    if result["status"] == "REQUIRES_HUMAN_RANGE_REVIEW":
        box = result["rectangle_deskewed_px"]
        left, top, right, bottom = box["left"], box["top"], box["right"], box["bottom"]
        cv2.rectangle(view, (left, top), (right, bottom), (190, 0, 190), 6, cv2.LINE_AA)
        for label, point in (("M1", (left, top)), ("M2", (right, top)), ("M3", (right, bottom)), ("M4", (left, bottom))):
            cv2.circle(view, point, 15, (190, 0, 190), -1, cv2.LINE_AA)
            cv2.putText(view, label, (point[0] + 13, point[1] - 13), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (190, 0, 190), 2, cv2.LINE_AA)
    header = np.full((96, view.shape[1], 3), 250, dtype=np.uint8)
    title = f"{date} lattice-envelope frame review: {result['status']}"
    cv2.putText(header, title, (18, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "purple M1-M4 = grid-envelope candidate; no crop, controls, cracks, or transform shown", (18, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "Review: include y=0 baseline and full coordinate grid; exclude page summaries.", (18, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, view))


def sidecar(date: str) -> str:
    return f"""# {date} lattice-envelope frame-range review\n\n## Question\n\nDoes the fixed lattice-envelope candidate identify the surrounding printed road-coordinate grid without selecting page summaries?\n\n## Data provenance\n\nInput is the official white composite `{date}/segment_0_50_white.png`. The candidate uses only deskewed printed-grid periodicity and continuous border-stroke support.\n\n## How to read\n\nPurple M1–M4 is an exploratory candidate only. Check that it includes the whole coordinate frame, specifically its `y=0` baseline, while excluding page-summary material.\n\n## Main takeaway\n\nThe figure exposes the deterministic candidate for human range review.\n\n## Limitation\n\nIt is not a crop, a control-point set, a registration transform, an independent audit, or a 2-D model qualification.\n"""


def contact_sheet(panels: list[tuple[str, np.ndarray]]) -> np.ndarray:
    cell_width, cell_height = 1100, 480
    sheet = np.full((cell_height * 4, cell_width * 2, 3), 235, dtype=np.uint8)
    for index, (date, panel) in enumerate(panels):
        scale = min(cell_width / panel.shape[1], cell_height / panel.shape[0])
        shown = cv2.resize(panel, (round(panel.shape[1] * scale), round(panel.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        row, column = divmod(index, 2)
        x, y = column * cell_width + (cell_width - shown.shape[1]) // 2, row * cell_height + (cell_height - shown.shape[0]) // 2
        sheet[y:y + shown.shape[0], x:x + shown.shape[1]] = shown
        cv2.putText(sheet, date, (column * cell_width + 14, row * cell_height + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.84, (20, 20, 20), 2, cv2.LINE_AA)
    return sheet


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(input_root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    output.mkdir(parents=True)
    records, panels = [], []
    receipts = [f"{sha256(Path(__file__).resolve())}  script/{Path(__file__).name}\n", f"{sha256(LATTICE_PATH)}  script/{LATTICE_PATH.name}\n"]
    for date in DATES:
        source_path = input_root / date / "segment_0_50_white.png"
        gray = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise ValueError(f"cannot read {source_path}")
        result = candidate(gray)
        review = render_review(date, gray, result)
        name = f"{date}_lattice_envelope_frame_review"
        if not cv2.imwrite(str(output / f"{name}.png"), review):
            raise ValueError(f"cannot write {date} review")
        (output / f"{name}.md").write_text(sidecar(date), encoding="utf-8")
        box = result.get("rectangle_deskewed_px", {})
        support = result.get("support_px", {})
        records.append({"date": date, "review_status": result["status"], "error": result.get("error", ""), "deskew_angle_deg": result["deskew_angle_deg"], "vertical_pitch_px": result["vertical_pitch_px"], "horizontal_pitch_px": result["horizontal_pitch_px"], "vertical_run_count": len(result["vertical_run_positions_px"]), "horizontal_run_count": len(result["horizontal_run_positions_px"]), "left_px": box.get("left", ""), "top_px": box.get("top", ""), "right_px": box.get("right", ""), "bottom_px": box.get("bottom", ""), "aspect": result.get("aspect", ""), "left_support_px": support.get("left", ""), "right_support_px": support.get("right", ""), "top_support_px": support.get("top", ""), "bottom_support_px": support.get("bottom", "")})
        receipts.append(f"{sha256(source_path)}  input/{date}/segment_0_50_white.png\n")
        panels.append((date, review))
    if not cv2.imwrite(str(output / "eight_date_lattice_envelope_overview.png"), contact_sheet(panels)):
        raise ValueError("cannot write overview")
    (output / "eight_date_lattice_envelope_overview.md").write_text("# Eight-date lattice-envelope overview\n\n## Question\n\nHow do fixed regular-grid-envelope frame candidates compare across all eight development pages?\n\n## Data provenance\n\nEach panel is a reduced copy of the corresponding full-resolution review generated from its official source page.\n\n## How to read\n\nPurple denotes a candidate, whereas a no-candidate panel contains no frame. Full-resolution date panels are the review authority.\n\n## Main takeaway\n\nThis is a cross-date navigation aid for the exact same frozen rule.\n\n## Limitation\n\nThe overview is exploratory and cannot support crop, registration, or qualification claims.\n", encoding="utf-8")
    with (output / "per_date_lattice_envelope_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    result = {"status": STATUS, "records": records, "prohibited_claims": ["crop_authorization", "control_extraction", "registration_transform", "v2_final_gate", "2d_model_authorization"]}
    (output / "lattice_envelope_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(f"# LTPP lattice-envelope frame-range MVP\n\n`{STATUS}`\n\nOne frozen exploratory candidate rule was run on all eight seen development pages. Owner review of purple frames is required. No crop, grid controls, transform, final audit, or 2-D model is authorized.\n", encoding="utf-8")
    (output / "input_and_code_receipt.sha256").write_text("".join(receipts), encoding="utf-8")
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input_root.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
