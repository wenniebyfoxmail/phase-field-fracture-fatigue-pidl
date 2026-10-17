#!/usr/bin/env python3
"""Add same-stem documentation sidecars to frozen prediction PNG assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_root", type=Path)
    args = parser.parse_args()
    root = args.result_root.resolve()
    metrics_path = root / "metrics_receipt.json"
    metrics = json.loads(metrics_path.read_text())
    rows = {row["blind_id"]: row for row in metrics["rows"]}
    written = 0
    for image in sorted((root / "folds").glob("LOSO-*/*__prediction_centerline.png")):
        blind_id = image.name.split("__", 1)[0]
        row = rows[blind_id]
        fold = image.parent.name
        center = row["centerline"]
        sentinel = row.get("sentinel")
        sentinel_text = "not a preregistered zero-crack map"
        if sentinel is not None:
            sentinel_text = (
                f"zero-crack sentinel pass={sentinel['pass']}, occupancy pixels="
                f"{sentinel['occupancy_pixels']}, qualifying components="
                f"{sentinel['qualifying_component_count']}"
            )
        image.with_suffix(".md").write_text(
            f"# {blind_id} frozen prediction centerline\n\n"
            "## Figure question\n"
            f"What centerline did the single authorized challenger predict for `{blind_id}`?\n\n"
            "## Exact data provenance\n"
            f"Terminal Taobo result `{root.name}`, fold `{fold}`, runner SHA-256 "
            f"`{metrics['runner_sha256']}`, metrics receipt `{metrics_path.name}`, and "
            f"prediction PNG SHA-256 `{sha256(image)}`. The source carrier and adjudicated "
            "gold are the frozen 37-map packet.\n\n"
            "## How to read\n"
            "This is a single binary image, not a multi-panel overlay. White pixels are the "
            "predicted skeletonized crack centerline at the frozen 0.35 occupancy threshold; "
            "black pixels are background. No component was removed.\n\n"
            "## Numerical takeaway\n"
            f"Section `{row['section']}`; centreline precision `{center['precision']:.6f}`, "
            f"recall `{center['recall']:.6f}`, F1 `{center['f1']:.6f}`; {sentinel_text}.\n\n"
            "## Limitations and claim boundary\n"
            "The image alone does not distinguish true from false positives; use the fixed "
            "four-map overlay and metrics receipt for that comparison. This result is current-map "
            "recognition on scanned forms only, not forecasting, registration, physical crack "
            "width, or ordinary road-photo deployment. The terminal gate failed and no rerun or "
            "post-hoc rule change is authorized.\n"
        )
        written += 1
    print(json.dumps({"status": "documented", "sidecars_written": written}))
    return 0 if written == 37 else 2


if __name__ == "__main__":
    raise SystemExit(main())
