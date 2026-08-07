#!/usr/bin/env python3
"""One fixed Tier-C grid-registration MVP; never a v2 qualification audit.

The script re-detects the printed grid in the page-frame MVP images, uses a
fixed non-v2-reserved fit/development split, and evaluates a simple model
ladder.  It deliberately reports development residuals as non-independent
Tier-C diagnostics, never as an audit pass.
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


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
WIDTH, HEIGHT, PX_PER_M = 1524, 500, 100
WINDOW_FRACTION = 0.18
STATUS = "EXPLORATORY_TIER_C_GRID_REGISTRATION_MVP__NOT_QUALIFIED"
V2_RESERVED = {(0, 0), (10, 0), (0, 5), (10, 5), (2, 2), (8, 2), (2, 3), (8, 3), (5, 0), (5, 5), (0, 2), (0, 3), (10, 2), (10, 3), (3, 1), (7, 4)}
DEVELOPMENT = {(1, 1), (4, 1), (6, 1), (9, 1), (1, 4), (4, 4), (6, 4), (9, 4)}
GATE_M = (0.05, 0.10, 0.20)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def grid_axis_positions(image: np.ndarray, axis: str) -> list[float]:
    """Select one dark-profile maximum around every expected grid coordinate."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    dark = np.minimum(255 - gray.astype(np.float32), 96.0)
    if axis == "x":
        profile, count = np.mean(dark[10:-10, :], axis=0), 11
    elif axis == "y":
        profile, count = np.mean(dark[:, 10:-10], axis=1), 6
    else:
        raise ValueError("axis must be x or y")
    spacing = (len(profile) - 1) / (count - 1)
    radius = max(1, int(round(WINDOW_FRACTION * spacing)))
    positions = []
    for index in range(count):
        nominal = int(round(index * spacing))
        lo, hi = max(0, nominal - radius), min(len(profile), nominal + radius + 1)
        candidates = np.flatnonzero(profile[lo:hi] == np.max(profile[lo:hi])) + lo
        selected = int(candidates[np.argmin(np.abs(candidates - nominal))])
        positions.append(float(selected))
    if any(right <= left for left, right in zip(positions, positions[1:])):
        raise ValueError(f"non-monotone {axis}-grid extraction")
    return positions


def controls(image: np.ndarray) -> list[dict]:
    xs, ys = grid_axis_positions(image, "x"), grid_axis_positions(image, "y")
    result = []
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            point = (i, j)
            role = "reserved_v2_excluded" if point in V2_RESERVED else ("development" if point in DEVELOPMENT else "fit")
            result.append({
                "id": f"G[{i},{j}]", "i": i, "j": j, "role": role,
                "source_px": [x, y], "target_px": [i * (WIDTH - 1) / 10, j * (HEIGHT - 1) / 5],
            })
    return result


def fit_diagonal(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    matrix = np.eye(3, dtype=float)
    for axis in range(2):
        a = np.column_stack((source[:, axis], np.ones(len(source))))
        slope, intercept = np.linalg.lstsq(a, target[:, axis], rcond=None)[0]
        matrix[axis, axis], matrix[axis, 2] = slope, intercept
    return matrix


def fit_affine(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    a = np.column_stack((source[:, 0], source[:, 1], np.ones(len(source))))
    coeff = np.linalg.lstsq(a, target, rcond=None)[0]
    return np.vstack((coeff.T, (0.0, 0.0, 1.0)))


def fit_homography(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    matrix, _ = cv2.findHomography(source.astype(np.float32), target.astype(np.float32), method=0)
    if matrix is None:
        raise ValueError("homography fit failed")
    return matrix.astype(float)


def apply(matrix: np.ndarray, source: np.ndarray) -> np.ndarray:
    homogeneous = np.column_stack((source, np.ones(len(source)))) @ matrix.T
    return homogeneous[:, :2] / homogeneous[:, 2:3]


def residual_metrics(matrix: np.ndarray, controls_for_role: list[dict]) -> dict:
    source = np.array([row["source_px"] for row in controls_for_role], dtype=float)
    target = np.array([row["target_px"] for row in controls_for_role], dtype=float)
    errors_m = np.linalg.norm(apply(matrix, source) - target, axis=1) / PX_PER_M
    return {"median_m": float(np.median(errors_m)), "p95_m": float(np.quantile(errors_m, 0.95, method="linear")), "maximum_m": float(np.max(errors_m))}


def model_ladder(rows: list[dict]) -> tuple[str | None, dict[str, dict]]:
    fit_rows = [row for row in rows if row["role"] == "fit"]
    dev_rows = [row for row in rows if row["role"] == "development"]
    source = np.array([row["source_px"] for row in fit_rows], dtype=float)
    target = np.array([row["target_px"] for row in fit_rows], dtype=float)
    candidates = (("diagonal_affine", fit_diagonal), ("full_affine", fit_affine), ("homography", fit_homography))
    results, selected = {}, None
    for name, fitter in candidates:
        matrix = fitter(source, target)
        metrics = residual_metrics(matrix, dev_rows)
        metrics["matrix"] = matrix.tolist()
        metrics["within_diagnostic_gate"] = all(metrics[key] <= limit for key, limit in zip(("median_m", "p95_m", "maximum_m"), GATE_M))
        results[name] = metrics
        if selected is None and metrics["within_diagnostic_gate"]:
            selected = name
            break
    return selected, results


def grid_overlay(image: np.ndarray, rows: list[dict], colour: tuple[int, int, int] = (20, 150, 20)) -> np.ndarray:
    view = image.copy()
    for row in rows:
        if row["role"] == "reserved_v2_excluded":
            continue
        x, y = (int(round(value)) for value in row["source_px"])
        cv2.circle(view, (x, y), 3, colour if row["role"] == "fit" else (0, 160, 230), -1, cv2.LINE_AA)
    return view


def contact_sheet(images: list[tuple[str, np.ndarray]]) -> np.ndarray:
    panels = []
    for date, image in images:
        panel = cv2.resize(image, (762, 250), interpolation=cv2.INTER_AREA)
        bar = np.full((32, 762, 3), 250, dtype=np.uint8)
        cv2.putText(bar, date, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack((bar, panel)))
    if len(panels) % 2:
        panels.append(np.full_like(panels[-1], 255))
    return np.vstack(tuple(np.hstack((panels[index], panels[index + 1])) for index in range(0, len(panels), 2)))


def write_manifest(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in paths), encoding="utf-8")


def run(mvp_root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite exploratory output: {output}")
    mvp_receipt = mvp_root / "mvp_result.json"
    upstream = json.loads(mvp_receipt.read_text(encoding="utf-8"))
    if upstream.get("status") != "EXPLORATORY_REGISTRATION_MVP_COMPLETED__NOT_QUALIFIED":
        raise ValueError("unexpected upstream MVP state")
    output.mkdir(parents=True)
    overlay_dir, registered_dir = output / "control_overlay", output / "registered_by_selected_model"
    overlay_dir.mkdir(); registered_dir.mkdir()
    all_controls, metric_rows, views = {}, [], []
    for date in DATES:
        path = mvp_root / "registered" / f"{date}.png"
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None or image.shape[:2] != (HEIGHT, WIDTH):
            raise ValueError(f"invalid upstream image for {date}")
        rows = controls(image)
        selected, models = model_ladder(rows)
        all_controls[date] = rows
        cv2.imwrite(str(overlay_dir / f"{date}.png"), grid_overlay(image, rows))
        for model, values in models.items():
            metric_rows.append({"survey_date": date, "model": model, "selected": model == selected, **{key: values[key] for key in ("median_m", "p95_m", "maximum_m", "within_diagnostic_gate")}})
        if selected is not None:
            matrix = np.array(models[selected]["matrix"], dtype=float)
            corrected = cv2.warpPerspective(image, matrix, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))
            cv2.imwrite(str(registered_dir / f"{date}.png"), corrected)
            views.append((date, corrected))
    with (output / "control_points_tier_c.json").open("w", encoding="utf-8") as handle:
        json.dump(all_controls, handle, indent=2); handle.write("\n")
    with (output / "development_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metric_rows[0])); writer.writeheader(); writer.writerows(metric_rows)
    if views:
        cv2.imwrite(str(output / "selected_model_contact_sheet.png"), contact_sheet(views))
    result = {
        "status": STATUS, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_mvp_receipt": str(mvp_receipt.resolve()), "upstream_mvp_receipt_sha256": sha256(mvp_receipt),
        "script_sha256": sha256(Path(__file__).resolve()), "grid_candidate_count_per_date": 66,
        "roles_per_date": {"v2_reserved_excluded": len(V2_RESERVED), "development": len(DEVELOPMENT), "fit": 66 - len(V2_RESERVED) - len(DEVELOPMENT)},
        "selection_rule": "first model in fixed ladder satisfying the displayed Tier-C diagnostic thresholds; diagnostic only",
        "selected_models": {date: next((row["model"] for row in metric_rows if row["survey_date"] == date and row["selected"]), None) for date in DATES},
        "prohibited_claims": ["independent_controls", "v2_final_gate", "physical_registration_qualification", "2d_model_authorization"],
    }
    (output / "exploratory_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# Exploratory Tier-C grid registration MVP\n\n"
        f"## Status\n\n`{STATUS}`\n\n"
        "## Scope\n\nThis one-shot engineering run uses automatically extracted printed-grid candidates already exposed by v1. All v2 reserved positions are excluded from fitting and development. Reported residuals are non-independent Tier-C development diagnostics, not final controls or a qualification result.\n\n"
        "## Consequence\n\nNo result from this package changes v1, v2 availability, or 2-D model eligibility.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mvp-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.mvp_root.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "selected_models": result["selected_models"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
