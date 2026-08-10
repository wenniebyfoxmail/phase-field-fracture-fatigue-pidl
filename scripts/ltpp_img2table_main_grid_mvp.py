#!/usr/bin/env python3
"""Frozen no-OCR complete-lattice tooling MVP for the LTPP road-grid frame."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import sys
from collections import deque
from pathlib import Path
from typing import Any

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
STATUS = "EXPLORATORY_MAIN_GRID_TOOLING_MVP__NOT_QUALIFIED"
IMG2TABLE_VERSION = "2.0.0"
IMG2TABLE_WHEEL_SHA256 = "d1fa566deda469e88363bbcee5bdc5c81b7414691bd803d72170a0fe53f85848"
LINE_SOURCE_SHA256 = "6e191089435a4032909d5ad4f2ab84c867afd23a5b5cbfcd9979d9ed7e4237c4"
EXPECTED_VERTICAL = 11
EXPECTED_HORIZONTAL = 6
EXPECTED_INTERSECTIONS = EXPECTED_VERTICAL * EXPECTED_HORIZONTAL
INTERSECTION_TOLERANCE_PX = 3
MIN_SPAN_COVERAGE = 0.96
MAX_REGULARITY_DEVIATION = 0.20
TARGET_ASPECT = 15.24 / 5.0
ASPECT_RANGE = (TARGET_ASPECT * 0.80, TARGET_ASPECT * 1.20)
CHAR_LENGTH = 11
ADAPTIVE_BLOCK_SIZE = 51
ADAPTIVE_C = 9
QUANTIZATION = 1_000_000
PURPLE = (190, 0, 190)
RED = (30, 30, 220)
GREEN = (0, 165, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8"
    )


def dependency_receipt() -> dict[str, str]:
    return {
        "img2table_version": importlib.metadata.version("img2table"),
        "img2table_wheel_sha256": IMG2TABLE_WHEEL_SHA256,
        "img2table_lines_py_sha256": LINE_SOURCE_SHA256,
        "opencv_distribution": importlib.metadata.version("opencv-contrib-python-headless"),
        "cv2_version": cv2.__version__,
        "numpy_version": importlib.metadata.version("numpy"),
        "python_version": sys.version,
    }


def line_detector():
    """Import exactly the approved geometry-only img2table entrypoint."""
    from img2table.tables.bordered.lines import identify_straight_lines

    return identify_straight_lines


def threshold_from_bgr(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_BLOCK_SIZE,
        ADAPTIVE_C,
    )


def min_line_length(shape: tuple[int, ...]) -> int:
    return max(64, round(0.08 * min(shape[:2])))


def detect_lines(image: np.ndarray) -> tuple[list[Any], list[Any]]:
    identify = line_detector()
    binary = threshold_from_bgr(image)
    minimum = min_line_length(image.shape)
    vertical = identify(binary, min_line_length=minimum, char_length=CHAR_LENGTH, vertical=True)
    horizontal = identify(binary, min_line_length=minimum, char_length=CHAR_LENGTH, vertical=False)
    return horizontal, vertical


def intersects(horizontal: Any, vertical: Any) -> bool:
    return (
        int(horizontal.x1) - INTERSECTION_TOLERANCE_PX <= int(vertical.x1) <= int(horizontal.x2) + INTERSECTION_TOLERANCE_PX
        and int(vertical.y1) - INTERSECTION_TOLERANCE_PX <= int(horizontal.y1) <= int(vertical.y2) + INTERSECTION_TOLERANCE_PX
    )


def components(horizontal: list[Any], vertical: list[Any]) -> list[dict[str, Any]]:
    """Return whole connected separator components; never select a subset."""
    adjacency: dict[tuple[str, int], set[tuple[str, int]]] = {
        **{("h", index): set() for index in range(len(horizontal))},
        **{("v", index): set() for index in range(len(vertical))},
    }
    edges: dict[tuple[int, int], tuple[int, int]] = {}
    for h_index, h_line in enumerate(horizontal):
        for v_index, v_line in enumerate(vertical):
            if intersects(h_line, v_line):
                adjacency[("h", h_index)].add(("v", v_index))
                adjacency[("v", v_index)].add(("h", h_index))
                edges[(h_index, v_index)] = (int(v_line.x1), int(h_line.y1))
    pending = set(node for node, neighbours in adjacency.items() if neighbours)
    output: list[dict[str, Any]] = []
    while pending:
        start = min(pending)
        queue, seen = deque([start]), {start}
        pending.remove(start)
        while queue:
            node = queue.popleft()
            for neighbour in adjacency[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    pending.discard(neighbour)
                    queue.append(neighbour)
        h_indices = sorted(index for kind, index in seen if kind == "h")
        v_indices = sorted(index for kind, index in seen if kind == "v")
        points = [edges[(h, v)] for h in h_indices for v in v_indices if (h, v) in edges]
        output.append({"horizontal": [horizontal[index] for index in h_indices], "vertical": [vertical[index] for index in v_indices], "points": points})
    return output


def span_coverage(lines: list[Any], vertical: bool, lower: int, upper: int) -> float:
    span = max(1, upper - lower)
    coverages = []
    for line in lines:
        start, end = (int(line.y1), int(line.y2)) if vertical else (int(line.x1), int(line.x2))
        coverages.append(max(0, min(end, upper) - max(start, lower)) / span)
    return min(coverages, default=0.0)


def regularity(positions: list[int]) -> float:
    gaps = np.diff(np.array(sorted(positions), dtype=float))
    if len(gaps) == 0 or np.any(gaps <= 0):
        return math.inf
    return float(np.max(np.abs(gaps / np.median(gaps) - 1.0)))


def evaluate_component(component: dict[str, Any]) -> dict[str, Any]:
    vertical, horizontal = component["vertical"], component["horizontal"]
    xs, ys = sorted(int(line.x1) for line in vertical), sorted(int(line.y1) for line in horizontal)
    if not xs or not ys:
        return {"eligible": False, "reason": "empty component"}
    left, right, top, bottom = xs[0], xs[-1], ys[0], ys[-1]
    width, height = right - left, bottom - top
    aspect = width / max(1, height)
    x_regularity, y_regularity = regularity(xs), regularity(ys)
    v_coverage = span_coverage(vertical, True, top, bottom)
    h_coverage = span_coverage(horizontal, False, left, right)
    record = {
        "Nv": len(vertical),
        "Nh": len(horizontal),
        "I": len(component["points"]),
        "left_px": left,
        "top_px": top,
        "right_px": right,
        "bottom_px": bottom,
        "area_px": width * height,
        "aspect": aspect,
        "vertical_span_coverage": v_coverage,
        "horizontal_span_coverage": h_coverage,
        "x_regularity_deviation": x_regularity,
        "y_regularity_deviation": y_regularity,
        "corners_px": {"top_left": [left, top], "top_right": [right, top], "bottom_right": [right, bottom], "bottom_left": [left, bottom]},
    }
    failures = []
    if (record["Nv"], record["Nh"], record["I"]) != (EXPECTED_VERTICAL, EXPECTED_HORIZONTAL, EXPECTED_INTERSECTIONS):
        failures.append("topology")
    if min(v_coverage, h_coverage) < MIN_SPAN_COVERAGE:
        failures.append("span_coverage")
    if max(x_regularity, y_regularity) > MAX_REGULARITY_DEVIATION:
        failures.append("regularity")
    if not ASPECT_RANGE[0] <= aspect <= ASPECT_RANGE[1]:
        failures.append("aspect")
    record["eligible"] = not failures
    record["reason"] = "" if not failures else ";".join(failures)
    aspect_deviation = 10**18 if aspect <= 0 else round(abs(math.log(aspect / TARGET_ASPECT)) * QUANTIZATION)
    record["rank"] = (
        -record["I"],
        -(record["Nv"] + record["Nh"]),
        -record["area_px"],
        aspect_deviation,
    )
    return record


def select_candidate(image: np.ndarray) -> dict[str, Any]:
    horizontal, vertical = detect_lines(image)
    all_components = [evaluate_component(component) for component in components(horizontal, vertical)]
    eligible = [record for record in all_components if record["eligible"]]
    result: dict[str, Any] = {
        "detected_horizontal_lines": len(horizontal),
        "detected_vertical_lines": len(vertical),
        "components": all_components,
    }
    if not eligible:
        result.update(status="NO_CANDIDATE__FAIL_CLOSED", reason="no eligible complete lattice")
        return result
    eligible.sort(key=lambda record: record["rank"])
    if len(eligible) > 1 and eligible[0]["rank"] == eligible[1]["rank"]:
        result.update(status="NO_CANDIDATE__FAIL_CLOSED", reason="exact eligible ranking tie")
        return result
    result.update(status="CANDIDATE_SELECTED__REQUIRES_HUMAN_REVIEW", candidate=eligible[0])
    return result


def render_review(title: str, image: np.ndarray, result: dict[str, Any]) -> np.ndarray:
    view = image.copy()
    header = np.full((108, view.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, title, (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, result["status"], (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "purple = selected complete printed lattice only; no crop, controls, cracks, or transform", (18, 91), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 20, 20), 1, cv2.LINE_AA)
    if result["status"] == "CANDIDATE_SELECTED__REQUIRES_HUMAN_REVIEW":
        candidate = result["candidate"]
        points = candidate["corners_px"]
        cv2.rectangle(view, tuple(points["top_left"]), tuple(points["bottom_right"]), PURPLE, 7, cv2.LINE_AA)
        for label, point in points.items():
            cv2.circle(view, tuple(point), 16, PURPLE, -1, cv2.LINE_AA)
            cv2.putText(view, label, (point[0] + 16, point[1] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.52, PURPLE, 2, cv2.LINE_AA)
    else:
        cv2.putText(view, result["reason"], (18, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.72, RED, 2, cv2.LINE_AA)
    return np.vstack((header, view))


def draw_lattice(image: np.ndarray, origin: tuple[int, int], x_gap: int, y_gap: int, *, break_vertical: int | None = None) -> None:
    x0, y0 = origin
    for index in range(EXPECTED_VERTICAL):
        x = x0 + index * x_gap
        if index == break_vertical:
            cv2.line(image, (x, y0), (x, y0 + 2 * y_gap), (0, 0, 0), 3)
            cv2.line(image, (x, y0 + 3 * y_gap), (x, y0 + 5 * y_gap), (0, 0, 0), 3)
        else:
            cv2.line(image, (x, y0), (x, y0 + 5 * y_gap), (0, 0, 0), 3)
    for index in range(EXPECTED_HORIZONTAL):
        cv2.line(image, (x0, y0 + index * y_gap), (x0 + 10 * x_gap, y0 + index * y_gap), (0, 0, 0), 3)


def blank() -> np.ndarray:
    return np.full((940, 1700, 3), 255, dtype=np.uint8)


def synthetic_fixtures() -> list[tuple[str, np.ndarray, str]]:
    fixtures: list[tuple[str, np.ndarray, str]] = []
    canonical = blank(); draw_lattice(canonical, (160, 220), 120, 80); fixtures.append(("canonical", canonical, "selected"))
    translated = blank(); draw_lattice(translated, (250, 150), 96, 64); fixtures.append(("translated_scaled", translated, "selected"))
    large_summary = blank(); draw_lattice(large_summary, (120, 180), 96, 64)
    for x in range(1100, 1560, 80): cv2.line(large_summary, (x, 80), (x, 800), (0, 0, 0), 3)
    for y in range(80, 801, 60): cv2.line(large_summary, (1100, y), (1500, y), (0, 0, 0), 3)
    fixtures.append(("large_summary", large_summary, "selected"))
    dense_summary = blank(); draw_lattice(dense_summary, (120, 180), 96, 64)
    for x in range(1100, 1580, 40): cv2.line(dense_summary, (x, 120), (x, 760), (0, 0, 0), 3)
    for y in range(120, 761, 40): cv2.line(dense_summary, (1100, y), (1540, y), (0, 0, 0), 3)
    fixtures.append(("dense_summary", dense_summary, "selected"))
    repair = blank()
    for x0, y0 in ((180, 180), (520, 180), (180, 500), (520, 500)):
        cv2.rectangle(repair, (x0, y0), (x0 + 160, y0 + 100), (0, 0, 0), 3)
    fixtures.append(("repair_rectangles", repair, "no_candidate"))
    missing_outer = blank(); draw_lattice(missing_outer, (160, 220), 120, 80); cv2.line(missing_outer, (160, 220), (520, 220), (255, 255, 255), 8); fixtures.append(("missing_outer", missing_outer, "no_candidate"))
    broken_internal = blank(); draw_lattice(broken_internal, (160, 220), 120, 80, break_vertical=5); fixtures.append(("broken_internal", broken_internal, "no_candidate"))
    nested = blank(); cv2.rectangle(nested, (120, 100), (1500, 820), (0, 0, 0), 3); cv2.rectangle(nested, (180, 160), (1440, 760), (0, 0, 0), 3); fixtures.append(("nested_borders", nested, "no_candidate"))
    tie = blank(); draw_lattice(tie, (80, 180), 65, 43); draw_lattice(tie, (920, 180), 65, 43); fixtures.append(("exact_tie", tie, "no_candidate"))
    wrong_ratio = blank(); draw_lattice(wrong_ratio, (220, 220), 80, 80); fixtures.append(("wrong_ratio", wrong_ratio, "no_candidate"))
    fixtures.append(("no_grid", blank(), "no_candidate"))
    return fixtures


def contact_sheet(panels: list[tuple[str, np.ndarray]]) -> np.ndarray:
    width, height = 900, 480
    sheet = np.full((height * math.ceil(len(panels) / 2), width * 2, 3), 235, dtype=np.uint8)
    for index, (name, panel) in enumerate(panels):
        scale = min(width / panel.shape[1], height / panel.shape[0])
        shown = cv2.resize(panel, (round(panel.shape[1] * scale), round(panel.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        row, column = divmod(index, 2)
        x, y = column * width + (width - shown.shape[1]) // 2, row * height + (height - shown.shape[0]) // 2
        sheet[y:y + shown.shape[0], x:x + shown.shape[1]] = shown
        cv2.putText(sheet, name, (column * width + 16, row * height + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, GREEN, 2, cv2.LINE_AA)
    return sheet


def run_synthetic(output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    output.mkdir(parents=True)
    records, panels = [], []
    for name, image, expected in synthetic_fixtures():
        result = select_candidate(image)
        observed = "selected" if result["status"].startswith("CANDIDATE_SELECTED") else "no_candidate"
        record = {"fixture": name, "expected": expected, "observed": observed, "passed": observed == expected, "status": result["status"], "reason": result.get("reason", "")}
        records.append(record)
        review = render_review(f"Synthetic fixture: {name}", image, result)
        cv2.imwrite(str(output / f"{name}.png"), review)
        panels.append((name, review))
    passed = all(record["passed"] for record in records)
    cv2.imwrite(str(output / "synthetic_suite_overview.png"), contact_sheet(panels))
    with (output / "synthetic_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    result = {"status": "SYNTHETIC_SUITE_PASSED" if passed else "SYNTHETIC_SUITE_FAILED", "records": records, "frozen_recipe": {"img2table": IMG2TABLE_VERSION, "wheel_sha256": IMG2TABLE_WHEEL_SHA256, "line_source_sha256": LINE_SOURCE_SHA256, "opencv": cv2.__version__}}
    (output / "synthetic_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "dependency_receipt.json").write_text(json.dumps(dependency_receipt(), indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(f"# LTPP no-OCR main-grid synthetic suite\n\n`{result['status']}`\n\nThe suite exercises only synthetic ruled drawings. It is not a real-data registration result.\n", encoding="utf-8")
    write_manifest(output)
    return result


def run_real(input_root: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    output.mkdir(parents=True)
    records, panels, receipts = [], [], [f"{sha256(Path(__file__).resolve())}  script/{Path(__file__).name}\n"]
    for date in DATES:
        source = input_root / date / "segment_0_50_white.png"
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read {source}")
        result = select_candidate(image)
        candidate = result.get("candidate", {})
        record = {"date": date, "status": result["status"], "reason": result.get("reason", ""), "detected_horizontal_lines": result["detected_horizontal_lines"], "detected_vertical_lines": result["detected_vertical_lines"], **{key: candidate.get(key, "") for key in ("Nv", "Nh", "I", "left_px", "top_px", "right_px", "bottom_px", "area_px", "aspect", "vertical_span_coverage", "horizontal_span_coverage", "x_regularity_deviation", "y_regularity_deviation")}}
        records.append(record)
        review = render_review(f"{date} main-grid tooling review", image, result)
        cv2.imwrite(str(output / f"{date}_main_grid_review.png"), review)
        panels.append((date, review))
        receipts.append(f"{sha256(source)}  input/{date}/segment_0_50_white.png\n")
    cv2.imwrite(str(output / "eight_date_main_grid_overview.png"), contact_sheet(panels))
    with (output / "per_date_main_grid_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    result = {"status": STATUS, "records": records, "prohibited_claims": ["crop_authorization", "control_extraction", "registration_transform", "v2_final_gate", "2d_model_authorization"]}
    (output / "main_grid_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "dependency_receipt.json").write_text(json.dumps(dependency_receipt(), indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(f"# LTPP no-OCR main-grid tooling MVP\n\n`{STATUS}`\n\nOne frozen recipe was run once on eight seen development pages. Purple indicates a candidate requiring human review; it is not a crop, control set, registration, or qualification.\n", encoding="utf-8")
    (output / "input_and_code_receipt.sha256").write_text("".join(receipts), encoding="utf-8")
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic-output", type=Path)
    mode.add_argument("--input-root", type=Path)
    parser.add_argument("--output", type=Path, help="required with --input-root")
    args = parser.parse_args()
    if args.synthetic_output:
        result = run_synthetic(args.synthetic_output.resolve())
    else:
        if args.output is None:
            parser.error("--output is required with --input-root")
        result = run_real(args.input_root.resolve(), args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "SYNTHETIC_SUITE_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
