#!/usr/bin/env python3
"""Fail-closed audit of frozen LTPP printed-grid rectification receipts."""

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


EXPECTED_DATES = (
    "1991-06-10", "1995-10-24", "1997-02-28", "1998-04-07",
    "2001-09-13", "2003-05-14", "2007-11-06", "2012-04-17",
)
X_CALIBRATION = {0, 2, 4, 6, 8, 10}
X_HELDOUT = {1, 3, 5, 7, 9}
Y_CALIBRATION = {0, 2, 4}
Y_HELDOUT = {1, 3, 5}
WINDOW_FRACTION = 0.18
MEDIAN_GATE_M = 0.05
P95_GATE_M = 0.10
MAX_GATE_M = 0.20


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def survey_iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def extract_axis_lines(row: dict, axis: str) -> list[dict]:
    if axis == "x":
        start, end, count, extent = row["x0"], row["x1"], 11, 15.24
        positions = row["detected_vertical_positions"]
        calibration, heldout = X_CALIBRATION, X_HELDOUT
    elif axis == "y":
        start, end, count, extent = row["y0"], row["y1"], 6, 5.0
        positions = row["detected_horizontal_positions"]
        calibration, heldout = Y_CALIBRATION, Y_HELDOUT
    else:
        raise ValueError(f"unsupported axis: {axis}")
    spacing = (end - start) / (count - 1)
    tolerance = WINDOW_FRACTION * spacing
    records = []
    for index in range(count):
        nominal = start + index * spacing
        candidates = sorted(float(p) for p in positions if abs(float(p) - nominal) <= tolerance)
        selected = min(candidates, key=lambda p: (abs(p - nominal), p)) if candidates else None
        role = "calibration" if index in calibration else "heldout"
        records.append({
            "axis": axis, "index": index, "role": role,
            "physical_coordinate_m": index * extent / (count - 1),
            "nominal_pixel": nominal, "window_tolerance_pixel": tolerance,
            "candidate_count": len(candidates), "selected_pixel": selected,
            "missing": selected is None,
        })
    return records


def fit_affine(lines: list[dict]) -> tuple[float, float]:
    calibration = [line for line in lines if line["role"] == "calibration"]
    if any(line["missing"] for line in calibration):
        raise ValueError("missing calibration line")
    matrix = np.column_stack([
        np.array([line["selected_pixel"] for line in calibration], dtype=float),
        np.ones(len(calibration)),
    ])
    target = np.array([line["physical_coordinate_m"] for line in calibration], dtype=float)
    slope, intercept = np.linalg.lstsq(matrix, target, rcond=None)[0]
    return float(slope), float(intercept)


def audit_row(row: dict) -> dict:
    x_lines = extract_axis_lines(row, "x")
    y_lines = extract_axis_lines(row, "y")
    all_lines = [*x_lines, *y_lines]
    result = {
        "survey_date": survey_iso(row["survey_date"]),
        "qualification_mode": row["qualification_mode"],
        "lines": all_lines,
        "status": None,
    }
    if any(line["missing"] for line in all_lines):
        result.update({
            "status": "INSUFFICIENT_CONTROL_POINTS",
            "missing_line_count": sum(line["missing"] for line in all_lines),
            "x_slope_m_per_px": None, "x_intercept_m": None,
            "y_slope_m_per_px": None, "y_intercept_m": None,
            "intersection_median_m": None, "intersection_p95_m": None,
            "intersection_max_m": None, "axis_residuals": [],
        })
        return result

    x_slope, x_intercept = fit_affine(x_lines)
    y_slope, y_intercept = fit_affine(y_lines)
    residuals = []
    x_errors, y_errors = [], []
    for line in all_lines:
        if line["role"] != "heldout":
            continue
        slope, intercept = (x_slope, x_intercept) if line["axis"] == "x" else (y_slope, y_intercept)
        predicted = slope * line["selected_pixel"] + intercept
        signed = predicted - line["physical_coordinate_m"]
        record = {
            "axis": line["axis"], "index": line["index"],
            "observed_pixel": line["selected_pixel"],
            "expected_m": line["physical_coordinate_m"],
            "predicted_m": predicted, "signed_residual_m": signed,
            "absolute_residual_m": abs(signed),
        }
        residuals.append(record)
        (x_errors if line["axis"] == "x" else y_errors).append(signed)
    intersection_errors = np.array(
        [math.hypot(x_error, y_error) for x_error in x_errors for y_error in y_errors],
        dtype=float,
    )
    median = float(np.median(intersection_errors))
    p95 = float(np.quantile(intersection_errors, 0.95, method="linear"))
    maximum = float(np.max(intersection_errors))
    passed = median <= MEDIAN_GATE_M and p95 <= P95_GATE_M and maximum <= MAX_GATE_M
    result.update({
        "status": "SPATIAL_REGISTRATION_QUALIFIED" if passed else "SPATIAL_REGISTRATION_NOT_QUALIFIED",
        "missing_line_count": 0,
        "x_slope_m_per_px": x_slope, "x_intercept_m": x_intercept,
        "y_slope_m_per_px": y_slope, "y_intercept_m": y_intercept,
        "intersection_median_m": median, "intersection_p95_m": p95,
        "intersection_max_m": maximum, "axis_residuals": residuals,
    })
    return result


def adjudicated_dates(root: Path) -> tuple[str, ...]:
    dates = []
    for path in sorted(root.glob("*.geojson")):
        props = read_json(path).get("properties", {})
        if props.get("section") == "06-1253":
            if props.get("locked") is not True or props.get("adjudicated") is not True:
                raise ValueError(f"unfrozen adjudicated state: {path}")
            dates.append(props["survey_date"])
    return tuple(sorted(dates))


def render_overlay(gate_root: Path, gate_rows: dict[str, dict], audits: list[dict], output: Path) -> None:
    panels = []
    for audit in audits:
        compact = audit["survey_date"].replace("-", "")
        row = gate_rows[compact]
        image = cv2.imread(str(gate_root / row["overlay_path"]))
        if image is None:
            raise ValueError(f"cannot read overlay for {compact}")
        pad_x = max(40, int((row["x1"] - row["x0"]) * 0.05))
        pad_y = max(40, int((row["y1"] - row["y0"]) * 0.10))
        left, right = max(0, row["x0"] - pad_x), min(image.shape[1], row["x1"] + pad_x)
        top, bottom = max(0, row["y0"] - pad_y), min(image.shape[0], row["y1"] + pad_y)
        crop = image[top:bottom, left:right].copy()
        for line in audit["lines"]:
            selected = line["selected_pixel"]
            position = line["nominal_pixel"] if selected is None else selected
            color = (0, 0, 220) if selected is None else ((40, 155, 40) if line["role"] == "calibration" else (0, 145, 235))
            if line["axis"] == "x":
                x = int(round(position - left)); cv2.line(crop, (x, 0), (x, crop.shape[0] - 1), color, 3)
            else:
                y = int(round(position - top)); cv2.line(crop, (0, y), (crop.shape[1] - 1, y), color, 3)
        panel = cv2.resize(crop, (900, 275), interpolation=cv2.INTER_AREA)
        bar = np.full((55, 900, 3), 248, dtype=np.uint8)
        metrics = "control points incomplete" if audit["intersection_median_m"] is None else (
            f"median={audit['intersection_median_m']:.3f}m p95={audit['intersection_p95_m']:.3f}m max={audit['intersection_max_m']:.3f}m"
        )
        cv2.putText(bar, f"{audit['survey_date']}  {audit['status']}", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (20, 20, 20), 1, cv2.LINE_AA)
        cv2.putText(bar, metrics, (12, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack([bar, panel]))
    rows = []
    for index in range(0, len(panels), 2):
        rows.append(np.hstack(panels[index:index + 2]))
    sheet = np.vstack(rows)
    cv2.imwrite(str(output), sheet)


def write_outputs(output: Path, gate_path: Path, preregistration: Path, audits: list[dict], gate_rows: dict[str, dict]) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    if (output / "decision.md").exists():
        raise ValueError("audit output already exists; v1 permits one execution only")
    overall_pass = all(row["status"] == "SPATIAL_REGISTRATION_QUALIFIED" for row in audits)
    overall_status = "SPATIAL_REGISTRATION_QUALIFIED_FOR_2D_ALGORITHM_DECISION" if overall_pass else "SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL"
    receipt = {
        "status": overall_status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "section": "06-1253", "audit_kind": "conditional_frozen_internal_grid_v1",
        "gate_results": str(gate_path.resolve()), "gate_results_sha256": sha256(gate_path),
        "preregistration": str(preregistration.resolve()), "preregistration_sha256": sha256(preregistration),
        "script_sha256": sha256(Path(__file__).resolve()),
        "thresholds_m": {"median": MEDIAN_GATE_M, "p95_linear": P95_GATE_M, "max": MAX_GATE_M},
        "date_count": len(audits), "qualified_date_count": sum(row["status"] == "SPATIAL_REGISTRATION_QUALIFIED" for row in audits),
        "audits": audits,
        "prohibited": ["2d_model_training", "date_deletion", "transform_rescue", "posthoc_perturbation"],
    }
    (output / "audit_result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    with (output / "per_date_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["survey_date", "qualification_mode", "status", "missing_line_count", "intersection_median_m", "intersection_p95_m", "intersection_max_m"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in audits: writer.writerow({key: row.get(key) for key in fields})
    with (output / "axis_residuals.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["survey_date", "axis", "index", "observed_pixel", "expected_m", "predicted_m", "signed_residual_m", "absolute_residual_m"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in audits:
            for residual in row["axis_residuals"]:
                writer.writerow({"survey_date": row["survey_date"], **residual})
    control_points = {row["survey_date"]: row["lines"] for row in audits}
    (output / "control_points.json").write_text(json.dumps(control_points, indent=2) + "\n", encoding="utf-8")
    figure = output / "registration_control_overlay.png"
    render_overlay(gate_path.parent, gate_rows, audits, figure)
    failed = [row["survey_date"] for row in audits if row["status"] != "SPATIAL_REGISTRATION_QUALIFIED"]
    (output / "registration_control_overlay.md").write_text(
        "# Registration control overlay\n\n"
        "## Question\n\nCan the frozen printed-grid carrier pass the predeclared held-out error gate for all eight 06-1253 dates?\n\n"
        f"## Provenance\n\nFrozen receipt: `{gate_path}` (SHA-256 `{sha256(gate_path)}`). The figure is generated by `{Path(__file__).name}` from grid metadata and existing overlays only; crack geometry does not select control lines.\n\n"
        "## Reading the figure\n\nEach panel is one survey date. Green lines are fixed calibration controls, orange lines are fixed held-out controls, and red lines mark missing required controls. The printed metrics use metres; p95 uses NumPy linear quantile.\n\n"
        f"## Main takeaway\n\nOverall status: `{overall_status}`. Failed or incomplete dates: `{', '.join(failed) if failed else 'none'}`.\n\n"
        "## Limitations and claim boundary\n\nThe panels reuse a frozen detector and crop receipt, so this is a conditional internal-grid audit, not external ground-truth registration. Fifteen intersections share five x and three y residuals and are not independent samples. Passing would only authorize a separate 2-D algorithm decision; failure does not invalidate separately reviewed scalar-length work.\n",
        encoding="utf-8",
    )
    decision = (
        "# LTPP 06-1253 spatial-registration audit v1 decision\n\n"
        f"## Decision\n\n`{overall_status}`\n\n"
        f"Qualified dates: {receipt['qualified_date_count']}/8. Failed or incomplete dates: {', '.join(failed) if failed else 'none'}.\n\n"
        "## Interpretation\n\nThis one-shot conditional audit evaluates the already frozen printed-grid carrier. It does not identify same-crack trajectories and does not modify any label.\n\n"
        "## Consequence\n\n" + (
            "All eight dates pass the coordinate gate. This authorizes only a separately preregistered 2-D algorithm decision.\n"
            if overall_pass else
            "The current eight-date carrier is not qualified for 2-D crack-position or continuation-tip modelling. No date may be deleted and no transform rescue is authorized within v1. Scalar-length work remains a separate claim.\n"
        )
    )
    (output / "decision.md").write_text(decision, encoding="utf-8")
    generated = sorted(path for path in output.iterdir() if path.is_file() and path.name != "manifest.sha256")
    (output / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in generated), encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-results", type=Path, required=True)
    parser.add_argument("--adjudicated-root", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--expected-gate-sha256", required=True)
    parser.add_argument("--expected-preregistration-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gate_path, preregistration = args.gate_results.resolve(), args.preregistration.resolve()
    if sha256(gate_path) != args.expected_gate_sha256:
        raise ValueError("gate receipt hash mismatch")
    if sha256(preregistration) != args.expected_preregistration_sha256:
        raise ValueError("preregistration hash mismatch")
    dates = adjudicated_dates(args.adjudicated_root.resolve())
    if dates != EXPECTED_DATES:
        raise ValueError(f"expected frozen dates {EXPECTED_DATES}, found {dates}")
    gate = read_json(gate_path)
    gate_rows = {row["survey_date"]: row for row in gate["results"]}
    audits = [audit_row(gate_rows[date.replace("-", "")]) for date in EXPECTED_DATES]
    receipt = write_outputs(args.output.resolve(), gate_path, preregistration, audits, gate_rows)
    print(json.dumps({key: receipt[key] for key in ("status", "date_count", "qualified_date_count")}))
    return 0 if receipt["status"].startswith("SPATIAL_REGISTRATION_QUALIFIED") else 3


if __name__ == "__main__":
    raise SystemExit(main())
