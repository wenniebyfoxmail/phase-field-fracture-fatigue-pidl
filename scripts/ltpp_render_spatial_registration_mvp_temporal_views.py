#!/usr/bin/env python3
"""Render adjacent-date visual views from a quarantined registration MVP.

The views are inspection aids only.  They neither estimate transforms nor
identify cracks, so their image differences must not be read as physical
damage development.
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


MVP_STATUS = "EXPLORATORY_REGISTRATION_MVP_COMPLETED__NOT_QUALIFIED"
VIEW_STATUS = "EXPLORATORY_TEMPORAL_VIEW_MVP_COMPLETED__NOT_QUALIFIED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pair_views(earlier: np.ndarray, later: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if earlier.shape != later.shape or earlier.ndim != 3:
        raise ValueError("registered pair must be same-size BGR images")
    blend = cv2.addWeighted(earlier, 0.5, later, 0.5, 0)
    difference = cv2.absdiff(earlier, later)
    return blend, difference


def labelled_panel(title: str, image: np.ndarray) -> np.ndarray:
    panel = cv2.resize(image, (762, 250), interpolation=cv2.INTER_AREA)
    bar = np.full((34, panel.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(bar, title, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((bar, panel))


def write_manifest(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in paths), encoding="utf-8"
    )


def run(mvp_root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite temporal-view output: {output}")
    receipt_path = mvp_root / "mvp_result.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != MVP_STATUS:
        raise ValueError("input is not the quarantined registration MVP")
    dates = receipt.get("dates")
    if not isinstance(dates, list) or len(dates) != 8 or dates != sorted(dates):
        raise ValueError("expected eight sorted MVP dates")
    output.mkdir(parents=True)
    blend_dir, difference_dir = output / "blend", output / "absolute_difference"
    blend_dir.mkdir(); difference_dir.mkdir()
    rows, panels = [], []
    for earlier_date, later_date in zip(dates[:-1], dates[1:]):
        earlier_path = mvp_root / "registered" / f"{earlier_date}.png"
        later_path = mvp_root / "registered" / f"{later_date}.png"
        earlier, later = cv2.imread(str(earlier_path), cv2.IMREAD_COLOR), cv2.imread(str(later_path), cv2.IMREAD_COLOR)
        if earlier is None or later is None:
            raise ValueError(f"missing registered pair {earlier_date}-{later_date}")
        blend, difference = pair_views(earlier, later)
        stem = f"{earlier_date}_{later_date}"
        blend_path, difference_path = blend_dir / f"{stem}.png", difference_dir / f"{stem}.png"
        if not cv2.imwrite(str(blend_path), blend) or not cv2.imwrite(str(difference_path), difference):
            raise ValueError(f"cannot write view pair {stem}")
        title = f"{earlier_date} -> {later_date} | blend (left), absolute image difference (right)"
        panels.append(np.hstack((labelled_panel(title, blend), labelled_panel(title, difference))))
        rows.append({
            "earlier_date": earlier_date, "later_date": later_date,
            "earlier_registered_sha256": sha256(earlier_path), "later_registered_sha256": sha256(later_path),
            "width_px": earlier.shape[1], "height_px": earlier.shape[0],
            "blend_path": str(blend_path.relative_to(output)), "difference_path": str(difference_path.relative_to(output)),
            "status": "VISUAL_INSPECTION_ONLY",
        })
    cv2.imwrite(str(output / "temporal_pair_contact_sheet.png"), np.vstack(panels))
    with (output / "temporal_pairs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    result = {
        "status": VIEW_STATUS, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_mvp_receipt": str(receipt_path.resolve()), "input_mvp_receipt_sha256": sha256(receipt_path),
        "date_pairs": [[row["earlier_date"], row["later_date"]] for row in rows],
        "operation": "0.5/0.5 BGR blend and absolute pixel difference only",
        "prohibited_interpretations": ["physical_crack_growth", "crack_identity", "registration_accuracy", "2d_model_qualification"],
    }
    (output / "temporal_view_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# LTPP registration MVP temporal-view decision\n\n"
        f"## Status\n\n`{VIEW_STATUS}`\n\n"
        "Seven adjacent-date blend and absolute-image-difference panels were rendered from the already quarantined common-canvas MVP. They are visual inspection aids only. Difference intensity may contain page, grid, handwriting, scan, or damage changes; it is not a crack-development measurement.\n",
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
    print(json.dumps({"status": result["status"], "pair_count": len(result["date_pairs"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
