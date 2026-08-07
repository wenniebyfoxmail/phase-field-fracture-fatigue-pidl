#!/usr/bin/env python3
"""Run a quarantined, page-frame-only LTPP registration MVP.

This tool proves an engineering path: frozen source maps -> a common rendered
coordinate canvas -> traceable images and visual overlays.  It uses only the
four already-recorded printed-map frame corners.  Consequently its corner
residual is a construction check, not independent registration evidence, and
its result can never qualify 2-D crack modelling.
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


EXPECTED_DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
WIDTH_M, HEIGHT_M, PX_PER_M = 15.24, 5.00, 100
OUTPUT_WIDTH, OUTPUT_HEIGHT = int(WIDTH_M * PX_PER_M), int(HEIGHT_M * PX_PER_M)
MVP_STATUS = "EXPLORATORY_REGISTRATION_MVP_COMPLETED__NOT_QUALIFIED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_frame(row: dict) -> np.ndarray:
    """Return frame corners in clockwise source-pixel order."""
    required = ("x0", "y0", "x1", "y1")
    if any(key not in row for key in required):
        raise ValueError(f"frame fields missing for {row.get('survey_date')}")
    x0, y0, x1, y1 = (float(row[key]) for key in required)
    if not x0 < x1 or not y0 < y1:
        raise ValueError(f"non-physical source frame for {row.get('survey_date')}")
    return np.float32(((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def target_frame() -> np.ndarray:
    return np.float32(((0, 0), (OUTPUT_WIDTH - 1, 0), (OUTPUT_WIDTH - 1, OUTPUT_HEIGHT - 1), (0, OUTPUT_HEIGHT - 1)))


def warp_from_frame(image: np.ndarray, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    matrix = cv2.getPerspectiveTransform(frame, target_frame())
    warped = cv2.warpPerspective(
        image, matrix, (OUTPUT_WIDTH, OUTPUT_HEIGHT), flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    return warped, matrix


def reprojection_error_px(matrix: np.ndarray, frame: np.ndarray) -> float:
    projected = cv2.perspectiveTransform(frame.reshape(1, -1, 2), matrix).reshape(-1, 2)
    return float(np.max(np.linalg.norm(projected - target_frame(), axis=1)))


def centre_jacobian_determinant(matrix: np.ndarray, frame: np.ndarray) -> float:
    centre = np.mean(frame, axis=0)
    delta = np.float32((centre, centre + (1, 0), centre + (0, 1))).reshape(1, 3, 2)
    mapped = cv2.perspectiveTransform(delta, matrix).reshape(3, 2)
    return float(np.linalg.det(np.column_stack((mapped[1] - mapped[0], mapped[2] - mapped[0]))))


def frame_overlay(image: np.ndarray, frame: np.ndarray) -> np.ndarray:
    overlay = image.copy()
    points = np.round(frame).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(overlay, (points,), True, (20, 180, 20), 3, cv2.LINE_AA)
    return overlay


def registered_grid_overlay(image: np.ndarray) -> np.ndarray:
    overlay = image.copy()
    for metre in range(1, int(WIDTH_M)):
        x = metre * PX_PER_M
        cv2.line(overlay, (x, 0), (x, OUTPUT_HEIGHT - 1), (225, 130, 30), 1, cv2.LINE_AA)
    for metre in range(1, int(HEIGHT_M)):
        y = metre * PX_PER_M
        cv2.line(overlay, (0, y), (OUTPUT_WIDTH - 1, y), (225, 130, 30), 1, cv2.LINE_AA)
    return overlay


def contact_sheet(images: list[tuple[str, np.ndarray]]) -> np.ndarray:
    panels = []
    for date, image in images:
        panel = cv2.resize(image, (762, 250), interpolation=cv2.INTER_AREA)
        bar = np.full((32, panel.shape[1], 3), 250, dtype=np.uint8)
        cv2.putText(bar, date, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack((bar, panel)))
    return np.vstack(tuple(np.hstack((panels[index], panels[index + 1])) for index in range(0, len(panels), 2)))


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8"
    )


def run(grid_results: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite MVP output: {output}")
    gate = json.loads(grid_results.read_text(encoding="utf-8"))
    rows = {row["survey_date"]: row for row in gate["results"]}
    if tuple(sorted(rows))[:8] != EXPECTED_DATES or any(date not in rows for date in EXPECTED_DATES):
        raise ValueError("the frozen eight-date grid receipt is required")
    output.mkdir(parents=True)
    registered_dir, source_dir, grid_dir = (output / name for name in ("registered", "source_frame_overlay", "registered_grid_overlay"))
    for directory in (registered_dir, source_dir, grid_dir):
        directory.mkdir()
    qc_rows, registered = [], []
    for date in EXPECTED_DATES:
        row = rows[date]
        source = Path(row["source_path"])
        if sha256(source) != row["source_sha256"]:
            raise ValueError(f"source hash mismatch for {date}")
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read source image: {source}")
        frame = source_frame(row)
        if frame[:, 0].max() >= image.shape[1] or frame[:, 1].max() >= image.shape[0]:
            raise ValueError(f"source frame outside image for {date}")
        warped, matrix = warp_from_frame(image, frame)
        reprojection = reprojection_error_px(matrix, frame)
        jacobian = centre_jacobian_determinant(matrix, frame)
        if warped.shape[:2] != (OUTPUT_HEIGHT, OUTPUT_WIDTH) or reprojection > 1e-3 or jacobian <= 0:
            raise ValueError(f"structural MVP QC failed for {date}")
        for target, rendered in (
            (registered_dir / f"{date}.png", warped),
            (source_dir / f"{date}.png", frame_overlay(image, frame)),
            (grid_dir / f"{date}.png", registered_grid_overlay(warped)),
        ):
            if not cv2.imwrite(str(target), rendered):
                raise ValueError(f"cannot write {target}")
        registered.append((date, warped))
        qc_rows.append({
            "survey_date": date, "source_sha256": row["source_sha256"],
            "source_width_px": image.shape[1], "source_height_px": image.shape[0],
            "frame_x0_px": row["x0"], "frame_y0_px": row["y0"], "frame_x1_px": row["x1"], "frame_y1_px": row["y1"],
            "output_width_px": OUTPUT_WIDTH, "output_height_px": OUTPUT_HEIGHT,
            "metres_per_pixel": 1 / PX_PER_M, "corner_reprojection_px": reprojection,
            "centre_jacobian_determinant": jacobian, "status": "MVP_FRAME_WARP_COMPLETED",
        })
    sheet = contact_sheet(registered)
    cv2.imwrite(str(output / "registered_contact_sheet.png"), sheet)
    mean = np.mean(np.stack([image for _, image in registered], axis=0), axis=0).astype(np.uint8)
    cv2.imwrite(str(output / "registered_temporal_mean.png"), mean)
    with (output / "per_date_structural_qc.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(qc_rows[0])); writer.writeheader(); writer.writerows(qc_rows)
    receipt = {
        "status": MVP_STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "page_frame_homography_tooling_mvp",
        "grid_results": str(grid_results.resolve()), "grid_results_sha256": sha256(grid_results),
        "script": str(Path(__file__).resolve()), "script_sha256": sha256(Path(__file__).resolve()),
        "dates": list(EXPECTED_DATES), "output_canvas": {"width_px": OUTPUT_WIDTH, "height_px": OUTPUT_HEIGHT, "width_m": WIDTH_M, "height_m": HEIGHT_M, "metres_per_pixel": 1 / PX_PER_M, "image_y_direction": "downward"},
        "controls_used": "only the four pre-existing map-frame corners per date; no crack, WIM, repair, or distress geometry",
        "structural_qc": "frame corner reprojection and positive local orientation only; not a physical registration validation",
        "prohibited_claims": ["independent_control_validation", "v2_final_gate", "physical_registration_qualification", "2d_crack_model_authorization"],
    }
    (output / "mvp_result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# LTPP spatial-registration MVP decision\n\n"
        f"## Status\n\n`{MVP_STATUS}`\n\n"
        "## What completed\n\nAll eight frozen source maps were mapped by their recorded page-frame corners to a shared 1524 x 500 px canvas (0.01 m/px), with original-frame and registered-grid visualizations.\n\n"
        "## What this does not show\n\nThe same four corners construct each homography and cannot validate it. This is not a registration pass, does not assess physical point correspondence, and does not alter the v1 or v2 qualification state.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.grid_results.resolve(), args.output.resolve())
    print(json.dumps({"status": receipt["status"], "date_count": len(receipt["dates"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
