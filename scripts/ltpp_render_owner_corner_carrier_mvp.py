#!/usr/bin/env python3
"""Render locked owner-corner LTPP maps on an exact exploratory physical carrier."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
PX_PER_M = 100
WIDTH_M, HEIGHT_M = 15.24, 5.00
WIDTH_PX, HEIGHT_PX = 1524, 500
METRES_PER_PIXEL = 1 / PX_PER_M
STATUS = "EXPLORATORY_OWNER_CORNER_CARRIER_RENDERED__NOT_QUALIFIED"
PREREGISTRATION = Path(__file__).resolve().parents[1] / "docs" / "experiments" / "ltpp_geoforecast_owner_corner_carrier_render_mvp_v2_preregistration_20260811.md"
OWNER_ACCEPTANCE = Path(__file__).resolve().parents[1] / "docs" / "reviews" / "ltpp_geoforecast_owner_corner_carrier_visual_acceptance_20260811.md"
TARGET = np.float32(((0, 0), (WIDTH_PX - 1, 0), (WIDTH_PX - 1, HEIGHT_PX - 1), (0, HEIGHT_PX - 1)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(packet: Path) -> None:
    manifest = packet / "manifest.sha256"
    if not manifest.is_file():
        raise ValueError("input manifest is missing")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = packet / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"input manifest mismatch: {relative}")


def validate_source_points(points: object, width: int, height: int) -> np.ndarray:
    if not isinstance(points, list) or len(points) != 4:
        raise ValueError("exactly four source points are required")
    source = np.asarray(points, dtype=np.float32)
    if source.shape != (4, 2) or not np.isfinite(source).all():
        raise ValueError("invalid source point array")
    if source[:, 0].min() < 0 or source[:, 1].min() < 0 or source[:, 0].max() >= width or source[:, 1].max() >= height:
        raise ValueError("source point outside image")
    tl, tr, br, bl = source
    if not (tl[0] < tr[0] and bl[0] < br[0] and tl[1] < bl[1] and tr[1] < br[1]):
        raise ValueError("source point order is not TL, TR, BR, BL")
    cross = []
    for index in range(4):
        a, b, c = source[index], source[(index + 1) % 4], source[(index + 2) % 4]
        first, second = b - a, c - b
        cross.append(float(first[0] * second[1] - first[1] * second[0]))
    if any(value <= 0 for value in cross):
        raise ValueError("source quadrilateral is not clockwise convex")
    return source


def transform_and_warp(image: np.ndarray, source: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    matrix = cv2.getPerspectiveTransform(source, TARGET)
    if not np.isfinite(matrix).all():
        raise ValueError("non-finite homography")
    warped = cv2.warpPerspective(
        image, matrix, (WIDTH_PX, HEIGHT_PX), flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    projected = cv2.perspectiveTransform(source.reshape(1, 4, 2), matrix).reshape(4, 2)
    reprojection = float(np.max(np.linalg.norm(projected - TARGET, axis=1)))
    centre = np.mean(source, axis=0)
    probe = np.float32((centre, centre + (1, 0), centre + (0, 1))).reshape(1, 3, 2)
    mapped = cv2.perspectiveTransform(probe, matrix).reshape(3, 2)
    determinant = float(np.linalg.det(np.column_stack((mapped[1] - mapped[0], mapped[2] - mapped[0]))))
    return warped, matrix, reprojection, determinant


def target_grid_overlay(image: np.ndarray) -> np.ndarray:
    overlay = image.copy()
    layer = overlay.copy()
    for half_metre in range(31):
        x = min(WIDTH_PX - 1, round(half_metre * 0.5 * PX_PER_M))
        colour, width = ((0, 80, 230), 2) if half_metre % 2 == 0 else ((20, 190, 70), 1)
        cv2.line(layer, (x, 0), (x, HEIGHT_PX - 1), colour, width, cv2.LINE_AA)
    cv2.line(layer, (WIDTH_PX - 1, 0), (WIDTH_PX - 1, HEIGHT_PX - 1), (0, 80, 230), 2, cv2.LINE_AA)
    for half_metre in range(11):
        y = min(HEIGHT_PX - 1, round((HEIGHT_M - half_metre * 0.5) * PX_PER_M))
        colour, width = ((0, 80, 230), 2) if half_metre % 2 == 0 else ((20, 190, 70), 1)
        cv2.line(layer, (0, y), (WIDTH_PX - 1, y), colour, width, cv2.LINE_AA)
    cv2.addWeighted(layer, 0.42, overlay, 0.58, 0, overlay)
    return overlay


def red_cyan(previous: np.ndarray, current: np.ndarray) -> np.ndarray:
    prev = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
    curr = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    prev_ink = 255 - prev
    curr_ink = 255 - curr
    return np.dstack((255 - prev_ink, 255 - prev_ink, 255 - curr_ink)).astype(np.uint8)


def contact_sheet(items: list[tuple[str, np.ndarray]], columns: int = 2, panel_width: int = 750) -> np.ndarray:
    panels = []
    for label, image in items:
        scale = panel_width / image.shape[1]
        panel = cv2.resize(image, (panel_width, round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        bar = np.full((34, panel_width, 3), 250, np.uint8)
        cv2.putText(bar, label, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack((bar, panel)))
    panel_height = max(panel.shape[0] for panel in panels)
    blank = np.full((panel_height, panel_width, 3), 255, np.uint8)
    panels = [np.vstack((panel, np.full((panel_height - panel.shape[0], panel_width, 3), 255, np.uint8))) for panel in panels]
    while len(panels) % columns:
        panels.append(blank.copy())
    return np.vstack(tuple(np.hstack(tuple(panels[index:index + columns])) for index in range(0, len(panels), columns)))


def write_figure(path: Path, image: np.ndarray, question: str, provenance: str, encoding: str, limitation: str) -> None:
    if not cv2.imwrite(str(path), image):
        raise ValueError(f"cannot write figure: {path}")
    path.with_suffix(".md").write_text(
        f"# {path.stem}\n\n## Question\n\n{question}\n\n## Provenance\n\n{provenance}\n\n"
        f"## How to read\n\n{encoding}\n\n## Limitation and claim boundary\n\n{limitation}\n",
        encoding="utf-8",
    )


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8"
    )


def run(packet: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    verify_manifest(packet)
    owner_file = packet / "owner_corners.json"
    owner = json.loads(owner_file.read_text(encoding="utf-8"))
    if owner.get("status") != "OWNER_CORNERS_LOCKED_PENDING_VISUAL_REVIEW__EXPLORATORY_ONLY":
        raise ValueError("locked owner-corner packet is required")
    records = {row["survey_date"]: row for row in owner.get("records", [])}
    if tuple(records) != DATES:
        raise ValueError("exact ordered eight-date record set is required")
    output.mkdir(parents=True)
    registered_dir = output / "registered"
    grid_dir = output / "target_grid_overlay"
    pair_dir = output / "adjacent_red_cyan"
    for directory in (registered_dir, grid_dir, pair_dir):
        directory.mkdir()
    registered: list[tuple[str, np.ndarray]] = []
    grids: list[tuple[str, np.ndarray]] = []
    qc_rows = []
    for date in DATES:
        record = records[date]
        if not record.get("locked"):
            raise ValueError(f"unlocked record: {date}")
        source_path = packet / "images" / f"{date}.png"
        if sha256(source_path) != record["source_sha256"]:
            raise ValueError(f"source hash mismatch: {date}")
        image = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read source image: {date}")
        source = validate_source_points(record["points_source_px"], image.shape[1], image.shape[0])
        warped, matrix, reprojection, determinant = transform_and_warp(image, source)
        if warped.shape[:2] != (HEIGHT_PX, WIDTH_PX) or reprojection > 1e-3 or determinant <= 0:
            raise ValueError(f"structural rendering check failed: {date}")
        grid = target_grid_overlay(warped)
        write_figure(
            registered_dir / f"{date}.png", warped,
            "What does this survey map look like on the accepted 15.24 m x 5.00 m carrier?",
            f"Frozen owner-corner packet `{owner_file}`; source date {date}; four-point projective construction.",
            "Array columns run 0-15.24 m left-to-right; rows run 5-0 m top-to-bottom at nominal 0.01 m/px.",
            "Construction-control render only; not independent registration validation or crack-growth evidence.",
        )
        write_figure(
            grid_dir / f"{date}.png", grid,
            "Do printed grid lines visually agree with the exact target carrier grid?",
            f"Registered {date} map plus deterministic target grid.",
            "Green lines mark 0.5 m intervals; orange lines mark 1.0 m intervals.",
            "Visual structural check only. Added lines do not validate physical registration error.",
        )
        registered.append((date, warped)); grids.append((date, grid))
        qc_rows.append({
            "survey_date": date, "source_sha256": record["source_sha256"],
            "source_width_px": image.shape[1], "source_height_px": image.shape[0],
            "output_width_px": WIDTH_PX, "output_height_px": HEIGHT_PX,
            "nominal_pixels_per_metre": PX_PER_M, "metres_per_pixel": METRES_PER_PIXEL,
            "corner_reprojection_max_px": reprojection, "centre_jacobian_determinant": determinant,
            "matrix_finite": bool(np.isfinite(matrix).all()), "status": "STRUCTURAL_RENDER_COMPLETED",
        })
    pairs = []
    for index in range(len(registered) - 1):
        previous_date, previous = registered[index]
        current_date, current = registered[index + 1]
        label = f"{previous_date}_to_{current_date}"
        composite = red_cyan(previous, current)
        write_figure(
            pair_dir / f"{label}.png", composite,
            "Where do adjacent registered scans coincide or disagree visually?",
            f"Registered owner-corner carrier maps for {previous_date} and {current_date}.",
            "Previous-only ink is red, current-only ink is cyan, and coincident ink is dark.",
            "Includes cracks, handwriting and scan differences; it is not a crack-growth map or independent error metric.",
        )
        pairs.append((label, composite))
    write_figure(
        output / "registered_contact_sheet.png", contact_sheet(registered),
        "Are all eight accepted frames rendered completely and with consistent orientation?",
        "Eight registered maps from the locked owner-corner packet.",
        "Each panel uses the same 15.24 m x 5.00 m carrier.",
        "Contact sheet is an engineering visual check, not registration qualification.",
    )
    write_figure(
        output / "target_grid_overlay_contact_sheet.png", contact_sheet(grids),
        "Do target-grid references show any obvious large-scale grid mismatch after rendering?",
        "Eight registered maps with the same deterministic target grid.",
        "Green is 0.5 m spacing and orange is 1.0 m spacing; the right edge is 15.24 m.",
        "No independent controls are assessed; small coloured offsets require later independent audit.",
    )
    write_figure(
        output / "adjacent_red_cyan_contact_sheet.png", contact_sheet(pairs),
        "Across adjacent dates, where is scan ink coincident versus displaced?",
        "Seven adjacent-date composites from the registered carrier maps.",
        "Previous-only ink is red, current-only ink is cyan, coincident ink is dark.",
        "Diagnostic only; colour may reflect cracks, handwriting, scan quality or true change.",
    )
    with (output / "per_date_structural_qc.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(qc_rows[0])); writer.writeheader(); writer.writerows(qc_rows)
    result = {
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_packet": str(packet), "input_manifest_sha256": sha256(packet / "manifest.sha256"),
        "owner_corners_sha256": sha256(owner_file),
        "implementation_path": str(Path(__file__).resolve()), "implementation_sha256": sha256(Path(__file__).resolve()),
        "preregistration_path": str(PREREGISTRATION), "preregistration_sha256": sha256(PREREGISTRATION),
        "owner_acceptance_path": str(OWNER_ACCEPTANCE), "owner_acceptance_sha256": sha256(OWNER_ACCEPTANCE),
        "dates": list(DATES),
        "physical_carrier": {"width_m": WIDTH_M, "height_m": HEIGHT_M,
                             "nominal_pixels_per_metre": PX_PER_M, "metres_per_pixel": METRES_PER_PIXEL,
                             "width_px": WIDTH_PX, "height_px": HEIGHT_PX},
        "controls": "locked owner-visible outer-frame construction controls; no cracks or cross-date features",
        "qualification_metrics_computed": False, "final_gate_run": False,
        "prohibited_claims": ["independent validation", "physical registration qualification", "crack growth measurement", "2-D model authorization"],
    }
    (output / "mvp_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        f"# Owner-corner carrier render MVP decision\n\n## Status\n\n`{STATUS}`\n\n"
        "All eight locked maps were rendered on the frozen 1524 x 500 px, 0.01 m/px carrier. "
        "This completes the exploratory rendering loop only. The construction corners cannot validate their own homography, "
        "so v1 remains negative and the 2-D route remains closed pending independent controls and a one-shot audit.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.packet_root.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "dates": len(result["dates"]), "output": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
