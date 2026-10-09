#!/usr/bin/env python3
"""Deterministic S03-E007 ruler-scale repeatability analysis.

Development mode is deliberately reference-1-only.  Formal mode refuses to
run without an independent PASS_CODE_READY receipt bound to the current commit,
protocol and selection manifest.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import platform
import socket
import subprocess
import sys
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks


PROTOCOL = "S03-E007-v3"
WORK_SCALE = 0.25
BOTTOM_FRACTION = 0.50
CANNY_LOW = 40
CANNY_HIGH = 120
HOUGH_THETA = np.pi / 720.0
HOUGH_THRESHOLD = 80
HOUGH_MIN_WIDTH_FRACTION = 0.25
HOUGH_MAX_GAP = 40
MAX_AXIS_ANGLE_DEG = 8.0
BAND_OFFSETS_NATIVE = (5, 90)
PERIOD_RANGE_NATIVE = (8, 30)
PEAK_DISTANCE_FRACTION = 0.55
PEAK_PROMINENCE_STD = 0.25
RANSAC_RESIDUAL_MM = 0.50
RANSAC_TRIALS = 600
MIN_TICKS = 50


@dataclass(frozen=True)
class Detection:
    beam: str
    reference: str
    saved_as: str
    sha256: str
    boundary_x1: float
    boundary_y1: float
    boundary_x2: float
    boundary_y2: float
    boundary_angle_deg: float
    nominal_period_px: float
    tick_count: int
    max_tick_step: int
    ransac_inlier_count: int
    lomo_count: int
    lomo_p95_mm: float
    lomo_median_mm: float
    spacing_cv: float
    monotone: bool
    finite: bool
    validity_pass: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def crc32_file(path: Path) -> str:
    value = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value = zlib.crc32(block, value)
    return f"{value & 0xFFFFFFFF:08x}"


def current_commit(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _fit_projective(x: np.ndarray, tick: np.ndarray) -> np.ndarray:
    # tick = (a + b*x) / (1 + c*x)
    design = np.column_stack([np.ones_like(x), x, -tick * x])
    coef, *_ = np.linalg.lstsq(design, tick, rcond=None)
    return coef


def _predict_projective(x: np.ndarray, coef: np.ndarray) -> np.ndarray:
    a, b, c = coef
    denominator = 1.0 + c * x
    return (a + b * x) / denominator


def fit_projective_ransac(
    x: np.ndarray,
    tick: np.ndarray,
    *,
    residual_mm: float = RANSAC_RESIDUAL_MM,
    trials: int = RANSAC_TRIALS,
) -> tuple[np.ndarray, np.ndarray]:
    if len(x) < 3:
        raise ValueError("projective fit requires at least three ticks")
    rng = np.random.default_rng(0)
    best: tuple[int, float, np.ndarray] | None = None
    for _ in range(trials):
        sample = np.sort(rng.choice(len(x), size=3, replace=False))
        try:
            coef = _fit_projective(x[sample], tick[sample])
            pred = _predict_projective(x, coef)
        except np.linalg.LinAlgError:
            continue
        if not np.all(np.isfinite(pred)):
            continue
        residual = np.abs(pred - tick)
        inliers = residual <= residual_mm
        score = (int(inliers.sum()), -float(np.median(residual[inliers]))) if inliers.any() else (0, -math.inf)
        if best is None or score > (best[0], -best[1]):
            best = (score[0], -score[1], inliers)
    if best is None or best[0] < 3:
        raise ValueError("RANSAC found fewer than three inliers")
    inliers = best[2]
    coef = _fit_projective(x[inliers], tick[inliers])
    pred = _predict_projective(x, coef)
    inliers = np.isfinite(pred) & (np.abs(pred - tick) <= residual_mm)
    coef = _fit_projective(x[inliers], tick[inliers])
    return coef, inliers


def _choose_upper_boundary(image: np.ndarray) -> tuple[float, float, float, float, float]:
    height, width = image.shape[:2]
    crop = image[int(height * (1.0 - BOTTOM_FRACTION)) :]
    work = cv2.resize(crop, None, fx=WORK_SCALE, fy=WORK_SCALE, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), CANNY_LOW, CANNY_HIGH)
    raw = cv2.HoughLinesP(
        edges,
        1,
        HOUGH_THETA,
        threshold=HOUGH_THRESHOLD,
        minLineLength=int(HOUGH_MIN_WIDTH_FRACTION * work.shape[1]),
        maxLineGap=HOUGH_MAX_GAP,
    )
    if raw is None:
        raise ValueError("no Hough segments detected")
    candidates: list[tuple[float, float, float, float, float, float, float]] = []
    for x1, y1, x2, y2 in raw[:, 0]:
        angle = math.degrees(math.atan2(float(y2 - y1), float(x2 - x1)))
        if abs(angle) > MAX_AXIS_ANGLE_DEG:
            continue
        length = math.hypot(float(x2 - x1), float(y2 - y1))
        candidates.append(((y1 + y2) / 2.0, -length, float(x1), float(y1), float(x2), float(y2), angle))
    if not candidates:
        raise ValueError("no near-horizontal boundary segment detected")
    _, _, x1, y1, x2, y2, angle = min(candidates)
    if x2 < x1:
        x1, x2, y1, y2 = x2, x1, y2, y1
    y_offset = height * (1.0 - BOTTOM_FRACTION)
    return (
        x1 / WORK_SCALE,
        y_offset + y1 / WORK_SCALE,
        x2 / WORK_SCALE,
        y_offset + y2 / WORK_SCALE,
        angle,
    )


def _tick_response(
    image: np.ndarray, boundary: tuple[float, float, float, float, float]
) -> tuple[np.ndarray, np.ndarray, float]:
    height, width = image.shape[:2]
    x1, y1, x2, y2, _ = boundary
    start = max(0, int(math.ceil(x1)))
    stop = min(width - 1, int(math.floor(x2)))
    if stop - start < 100:
        raise ValueError("detected ruler span is too short")
    xs = np.arange(start, stop + 1, dtype=np.int32)
    line_y = y1 + (y2 - y1) * (xs.astype(float) - x1) / (x2 - x1)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    offsets = np.arange(BAND_OFFSETS_NATIVE[0], BAND_OFFSETS_NATIVE[1] + 1)
    strip = np.stack(
        [gray[np.clip(np.rint(line_y + offset).astype(int), 0, height - 1), xs] for offset in offsets]
    )
    response = np.mean(np.abs(cv2.Sobel(strip, cv2.CV_32F, 1, 0, ksize=3)), axis=0)
    response = cv2.GaussianBlur(response.reshape(1, -1), (0, 0), 1.0).ravel()
    centered = response - float(response.mean())
    autocorrelation = np.correlate(centered, centered, mode="full")[len(centered) - 1 :]
    low, high = PERIOD_RANGE_NATIVE
    period = float(low + np.argmax(autocorrelation[low : high + 1]))
    return xs.astype(float), response, period


def _longest_tick_sequence(
    xs: np.ndarray, response: np.ndarray, period: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    peaks, _ = find_peaks(
        response,
        distance=max(1, int(math.floor(PEAK_DISTANCE_FRACTION * period))),
        prominence=max(np.finfo(float).eps, PEAK_PROMINENCE_STD * float(response.std())),
    )
    if len(peaks) < 2:
        raise ValueError("fewer than two tick peaks detected")
    sequences: list[list[int]] = [[int(peaks[0])]]
    sequence_steps: list[list[int]] = [[]]
    for left, right in zip(peaks[:-1], peaks[1:]):
        ratio = float(right - left) / period
        step = int(round(ratio))
        if step in (1, 2) and abs(ratio - step) <= 0.45:
            sequences[-1].append(int(right))
            sequence_steps[-1].append(step)
        else:
            sequences.append([int(right)])
            sequence_steps.append([])
    best_index = max(range(len(sequences)), key=lambda index: (len(sequences[index]), -sequences[index][0]))
    selected = np.asarray(sequences[best_index], dtype=int)
    steps = np.asarray(sequence_steps[best_index], dtype=int)
    tick_index = np.concatenate([[0], np.cumsum(steps)]).astype(float)
    return xs[selected], tick_index, steps


def _lomo_errors(x: np.ndarray, tick: np.ndarray, inliers: np.ndarray) -> np.ndarray:
    positions = np.flatnonzero(inliers & (np.mod(tick.astype(int), 10) == 0))
    errors: list[float] = []
    for position in positions:
        keep = inliers.copy()
        keep[position] = False
        if keep.sum() < 3:
            continue
        coef = _fit_projective(x[keep], tick[keep])
        prediction = _predict_projective(np.asarray([x[position]]), coef)[0]
        if np.isfinite(prediction):
            errors.append(abs(float(prediction - tick[position])))
    return np.asarray(errors, dtype=float)


def analyze_image(image: np.ndarray) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    boundary = _choose_upper_boundary(image)
    xs, response, period = _tick_response(image, boundary)
    tick_x, tick_index, steps = _longest_tick_sequence(xs, response, period)
    coef, inliers = fit_projective_ransac(tick_x, tick_index)
    prediction = _predict_projective(tick_x, coef)
    lomo = _lomo_errors(tick_x, tick_index, inliers)
    a, b, c = coef
    denominator = 1.0 + c * tick_x
    derivative = (b - c * a) / np.square(denominator)
    spacing = np.diff(tick_x) / np.maximum(1.0, np.diff(tick_index))
    finite = bool(
        np.all(np.isfinite(prediction))
        and np.all(np.isfinite(derivative))
        and np.all(np.isfinite(lomo))
        and len(lomo) > 0
    )
    monotone = bool(finite and (np.all(derivative > 0) or np.all(derivative < 0)))
    metrics: dict[str, object] = {
        "boundary": boundary,
        "nominal_period_px": period,
        "tick_count": int(len(tick_x)),
        "max_tick_step": int(steps.max()) if len(steps) else 0,
        "ransac_inlier_count": int(inliers.sum()),
        "lomo_count": int(len(lomo)),
        "lomo_p95_mm": float(np.quantile(lomo, 0.95)) if len(lomo) else math.nan,
        "lomo_median_mm": float(np.median(lomo)) if len(lomo) else math.nan,
        "spacing_cv": float(np.std(spacing, ddof=1) / np.mean(spacing)) if len(spacing) > 1 else math.nan,
        "monotone": monotone,
        "finite": finite,
        "validity_pass": bool(len(tick_x) >= MIN_TICKS and (len(steps) == 0 or steps.max() <= 2) and monotone),
    }
    arrays = {
        "signal_x": xs,
        "response": response,
        "tick_x": tick_x,
        "tick_index": tick_index,
        "inliers": inliers,
        "prediction": prediction,
    }
    return metrics, arrays


def _beam_and_reference(saved_as: str) -> tuple[str, str]:
    path = Path(saved_as)
    beam = path.parts[0]
    stem = path.stem.lower()
    if stem.endswith("ref1"):
        return beam, "ref1"
    if stem.endswith("ref2"):
        return beam, "ref2"
    raise ValueError(f"cannot determine reference identity: {saved_as}")


def _validate_review_pass(review_path: Path, repo: Path, manifest_path: Path) -> dict[str, object]:
    review = json.loads(review_path.read_text())
    expected = {
        "verdict": "PASS_CODE_READY",
        "protocol": PROTOCOL,
        "reviewed_commit": current_commit(repo),
        "selection_manifest_sha256": sha256_file(manifest_path),
    }
    mismatches = {key: (review.get(key), value) for key, value in expected.items() if review.get(key) != value}
    if mismatches:
        raise PermissionError(f"formal execution review receipt mismatch: {mismatches}")
    return review


def checkout_is_clean(repo: Path) -> bool:
    return not subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=repo, text=True
    ).strip()


def _write_csv(
    path: Path,
    rows: Iterable[Detection],
    beam_worst: dict[str, float] | None = None,
) -> None:
    image_rows = [
        {"row_type": "image", **asdict(row), "beam_worst_lomo_p95_mm": ""}
        for row in rows
    ]
    beam_rows = [
        {
            "row_type": "beam",
            "beam": beam,
            "reference": "worse_of_ref1_ref2",
            "saved_as": "",
            "sha256": "",
            "boundary_x1": "",
            "boundary_y1": "",
            "boundary_x2": "",
            "boundary_y2": "",
            "boundary_angle_deg": "",
            "nominal_period_px": "",
            "tick_count": "",
            "max_tick_step": "",
            "ransac_inlier_count": "",
            "lomo_count": "",
            "lomo_p95_mm": "",
            "lomo_median_mm": "",
            "spacing_cv": "",
            "monotone": "",
            "finite": "",
            "validity_pass": "",
            "beam_worst_lomo_p95_mm": value,
        }
        for beam, value in sorted((beam_worst or {}).items())
    ]
    exact_rows = image_rows + beam_rows
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(exact_rows[0].keys()))
        writer.writeheader()
        writer.writerows(exact_rows)


def _render_overlay(
    path: Path,
    panels: list[tuple[str, np.ndarray, dict[str, object], dict[str, np.ndarray]]],
) -> None:
    columns = 3
    rows = int(math.ceil(len(panels) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(16, 4.8 * rows), squeeze=False)
    for axis, (title, image, metrics, arrays) in zip(axes.flat, panels):
        boundary = metrics["boundary"]
        assert isinstance(boundary, tuple)
        x1, y1, x2, y2, _ = boundary
        crop_top = max(0, int(min(y1, y2) - 40))
        crop_bottom = min(image.shape[0], int(max(y1, y2) + 150))
        axis.imshow(cv2.cvtColor(image[crop_top:crop_bottom], cv2.COLOR_BGR2RGB))
        axis.plot([x1, x2], [y1 - crop_top, y2 - crop_top], color="#00b7c7", linewidth=1.5)
        tick_x = arrays["tick_x"]
        line_y = y1 + (y2 - y1) * (tick_x - x1) / (x2 - x1)
        colors = np.where(arrays["inliers"], "#f04e45", "#777777")
        axis.scatter(tick_x, line_y - crop_top + 45, c=colors, s=7)
        axis.set_title(
            f"{title}\n{metrics['tick_count']} ticks | LOMO p95={metrics['lomo_p95_mm']:.3f} mm"
        )
        axis.set_axis_off()
    for axis in axes.flat[len(panels) :]:
        axis.set_visible(False)
    fig.suptitle(f"{PROTOCOL}: detected upper boundary and indexed ticks", fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def run(
    *,
    raw_root: Path,
    selection_manifest: Path,
    output: Path,
    mode: str,
    repo: Path,
    review_pass: Path | None = None,
) -> dict[str, object]:
    started_at = datetime.now(timezone.utc).isoformat()
    manifest = json.loads(selection_manifest.read_text())
    files = manifest["files"]
    if mode == "development":
        files = [item for item in files if _beam_and_reference(item["saved_as"])[1] == "ref1"]
        if len(files) != 3:
            raise ValueError("development mode requires exactly three reference-1 files")
        review = None
    elif mode == "formal":
        if review_pass is None:
            raise PermissionError("formal mode requires --review-pass")
        review = _validate_review_pass(review_pass, repo, selection_manifest)
        if not checkout_is_clean(repo):
            raise PermissionError("formal execution requires a clean reviewed checkout")
        if len(files) != 6:
            raise ValueError("formal mode requires exactly six selected files")
    else:
        raise ValueError(f"unsupported mode: {mode}")

    output.mkdir(parents=True, exist_ok=False)
    detections: list[Detection] = []
    panels: list[tuple[str, np.ndarray, dict[str, object], dict[str, np.ndarray]]] = []
    for item in files:
        beam, reference = _beam_and_reference(item["saved_as"])
        if mode == "development" and reference != "ref1":
            raise PermissionError("reference-2 firewall violated in development mode")
        path = raw_root / item["saved_as"]
        if path.stat().st_size != item["bytes"]:
            raise ValueError(f"byte-size mismatch: {path}")
        if crc32_file(path) != item["crc32"]:
            raise ValueError(f"CRC mismatch: {path}")
        digest = sha256_file(path)
        if digest != item["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {path}")
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None or [image.shape[0], image.shape[1]] != [item["height_px"], item["width_px"]]:
            raise ValueError(f"decode or dimension mismatch: {path}")
        metrics, arrays = analyze_image(image)
        boundary = metrics.pop("boundary")
        assert isinstance(boundary, tuple)
        detection = Detection(
            beam=beam,
            reference=reference,
            saved_as=item["saved_as"],
            sha256=digest,
            boundary_x1=float(boundary[0]),
            boundary_y1=float(boundary[1]),
            boundary_x2=float(boundary[2]),
            boundary_y2=float(boundary[3]),
            boundary_angle_deg=float(boundary[4]),
            **metrics,
        )
        detections.append(detection)
        metrics["boundary"] = boundary
        panels.append((f"{beam} {reference}", image, metrics, arrays))

    stem = "development" if mode == "development" else "formal"
    validity = bool(all(row.validity_pass for row in detections))
    beam_worst = (
        {
            beam: max(row.lomo_p95_mm for row in detections if row.beam == beam)
            for beam in sorted({row.beam for row in detections})
        }
        if mode == "formal"
        else None
    )
    _write_csv(output / f"{stem}_metrics.csv", detections, beam_worst)
    _render_overlay(output / f"{stem}_overlay.png", panels)
    summary: dict[str, object] = {
        "protocol": PROTOCOL,
        "mode": mode,
        "scientific_status": "DEVELOPMENT_ONLY" if mode == "development" else "FORMAL_RESULT",
        "commit": current_commit(repo),
        "selection_manifest": str(selection_manifest),
        "selection_manifest_sha256": sha256_file(selection_manifest),
        "file_count": len(detections),
        "all_validity_pass": validity,
        "reference2_read": mode == "formal",
        "review_pass": review,
        "rows": [asdict(row) for row in detections],
    }
    if mode == "formal":
        assert beam_worst is not None
        primary = max(beam_worst.values()) if beam_worst else math.nan
        summary.update(
            {
                "beam_worst_lomo_p95_mm": beam_worst,
                "primary_max_beam_worst_lomo_p95_mm": primary,
                "primary_threshold_mm": 1.0,
                "decision": (
                    "PASS_DIRECTIONAL_SCALE_CARRIER"
                    if validity and primary <= 1.0
                    else "FAIL_VALIDITY" if not validity else "FAIL_PRIMARY"
                ),
            }
        )
    (output / f"{stem}_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    receipt = {
        "run_id": output.name,
        "protocol": PROTOCOL,
        "mode": mode,
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "producer": "Mac-PIDL lightweight deterministic CV",
        "hostname": socket.gethostname(),
        "commit": summary["commit"],
        "git_dirty_at_execution": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
        ),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "command": sys.argv,
        "output": str(output),
        "selection_manifest_sha256": summary["selection_manifest_sha256"],
    }
    (output / "run_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    if mode == "formal":
        decision = str(summary["decision"])
        (output / "decision.md").write_text(
            f"# {PROTOCOL} decision\n\n"
            f"- Verdict: `{decision}`\n"
            f"- Primary value: `{summary['primary_max_beam_worst_lomo_p95_mm']:.6f} mm`\n"
            f"- Threshold: `<= {summary['primary_threshold_mm']:.1f} mm`\n"
            f"- Validity: `{summary['all_validity_pass']}`\n\n"
            "This decision qualifies or rejects only a one-dimensional directional ruler-scale carrier. "
            "It does not validate physical crack width, isotropic scale, forecasting, or road transfer.\n"
        )
        (output / "README_analysis.md").write_text(
            f"# {PROTOCOL} analysis\n\n"
            "## Scientific question\n\n"
            "Can two fixed-camera ruler references per beam support a reproducible one-dimensional "
            "millimetre coordinate?\n\n"
            "## Evidence and reading order\n\n"
            "1. `formal_overlay.png` shows the detected upper boundary and indexed ticks.\n"
            "2. `formal_metrics.csv` contains exact per-image metrics.\n"
            "3. `formal_summary.json` and `decision.md` apply the frozen primary criterion.\n"
            "4. `run_receipt.json` records execution provenance.\n\n"
            "## Interpretation boundary\n\n"
            f"The frozen decision is `{decision}`. The allowed conclusion is limited to the directional "
            "scale carrier. Physical crack-width accuracy, two-dimensional isotropic scale, crack growth, "
            "future prediction, RUL, and road transfer remain blocked.\n"
        )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--selection-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=("development", "formal"), required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--review-pass", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(
        raw_root=args.raw_root,
        selection_manifest=args.selection_manifest,
        output=args.output,
        mode=args.mode,
        repo=args.repo,
        review_pass=args.review_pass,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
