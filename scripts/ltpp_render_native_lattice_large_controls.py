#!/usr/bin/env python3
"""Render already-frozen native lattice evidence with large review markers."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np


DETECTOR_PATH = Path(__file__).with_name("ltpp_detect_native_lattice_grid_mvp.py")
SPEC = importlib.util.spec_from_file_location("ltpp_native_lattice_detector", DETECTOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load detector: {DETECTOR_PATH}")
DETECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DETECTOR)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_large(source: np.ndarray, evidence: dict, title: str) -> np.ndarray:
    gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if source.ndim == 3 else source
    view = cv2.cvtColor(DETECTOR.rotate_bound(gray, evidence["deskew_angle_deg"]), cv2.COLOR_GRAY2BGR)
    for x in evidence["vertical_lattice"]["positions_px"]:
        cv2.line(view, (x, 0), (x, view.shape[0] - 1), (255, 210, 0), 1, cv2.LINE_AA)
    for y in evidence["horizontal_lattice"]["positions_px"]:
        cv2.line(view, (0, y), (view.shape[1] - 1, y), (255, 210, 0), 1, cv2.LINE_AA)
    for x, y in evidence["intersections_px"]:
        cv2.circle(view, (x, y), 12, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(view, (x, y), 10, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(view, (x, y), 7, (0, 220, 0), -1, cv2.LINE_AA)
    header = np.full((78, view.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, title, (18, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "cyan = recovered printed-grid line; large green circle = grid intersection candidate", (18, 53), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "marker only enlarged; no point location, line family, or result was changed", (18, 71), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, view))


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(source_root: Path, evidence_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True)
    written = []
    for date, date_evidence in evidence.items():
        source = cv2.imread(str(source_root / date / "segment_0_50_white.png"), cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError(f"missing source page for {date}")
        view = render_large(source, date_evidence, f"{date}: large-marker native lattice review")
        destination = output / f"{date}.png"
        if not cv2.imwrite(str(destination), view):
            raise ValueError(f"cannot write {destination}")
        written.append(date)
    result = {"evidence_sha256": sha256(evidence_path), "script_sha256": sha256(Path(__file__).resolve()), "dates": written, "marker_radius_px": 12}
    (output / "render_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source_root.resolve(), args.evidence.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
