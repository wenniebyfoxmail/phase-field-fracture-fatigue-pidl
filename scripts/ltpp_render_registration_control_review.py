#!/usr/bin/env python3
"""Render large, high-contrast Tier-C control-point review figures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


COLOURS = {"fit": (0, 220, 0), "development": (0, 145, 255)}


def draw_controls(image: np.ndarray, rows: list[dict], title: str) -> np.ndarray:
    canvas = image.copy()
    for row in rows:
        if row["role"] not in COLOURS:
            continue
        x, y = (int(round(value)) for value in row["source_px"])
        colour = COLOURS[row["role"]]
        cv2.circle(canvas, (x, y), 11, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(canvas, (x, y), 9, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(canvas, (x, y), 7, colour, -1, cv2.LINE_AA)
    header = np.full((75, canvas.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, title, (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.circle(header, (28, 55), 8, COLOURS["fit"], -1, cv2.LINE_AA)
    cv2.putText(header, "green: fit control", (42, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.circle(header, (255, 55), 8, COLOURS["development"], -1, cv2.LINE_AA)
    cv2.putText(header, "orange: development control", (269, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "no circle: v2-reserved / excluded", (565, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, canvas))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mvp-root", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    controls = json.loads(args.controls.read_text(encoding="utf-8"))
    panels = []
    for date, note in (("19951024", "1995: source-wide weak vertical-grid evidence"), ("20120417", "2012: Tier-C diagonal-affine diagnostic selected")):
        image = cv2.imread(str(args.mvp_root / "registered" / f"{date}.png"), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"missing image {date}")
        panels.append(draw_controls(image, controls[date], note))
    result = np.vstack(panels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), result):
        raise ValueError(f"cannot write {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
