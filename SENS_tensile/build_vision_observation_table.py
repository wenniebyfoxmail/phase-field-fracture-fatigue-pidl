#!/usr/bin/env python3
"""Build a calibrated `reality_obs_v1` table from registered crack masks.

The input is a CSV manifest of probability-mask paths and physical registration
metadata. Raw RGB segmentation is deliberately separate so any CV model can be
used without changing the downstream observation contract.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from reality_assimilation import vision_features_from_probability_mask


REQUIRED_COLUMNS = {
    "asset_id",
    "inspection_id",
    "timestamp",
    "cycle",
    "coordinate_frame",
    "registration_id",
    "mask_path",
    "pixel_size_x",
    "pixel_size_y",
    "origin_x",
    "origin_y",
    "flip_y",
    "umax",
}


def load_probability_mask(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        mask = np.load(path, allow_pickle=False)
    else:
        with Image.open(path) as image:
            if len(image.getbands()) != 1:
                raise ValueError(f"Probability mask {path} must be single-channel")
            raw = np.asarray(image)
        if np.issubdtype(raw.dtype, np.integer):
            mask = raw.astype(float) / float(np.iinfo(raw.dtype).max)
        else:
            mask = raw.astype(float)
    return np.asarray(mask, dtype=float)


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection-manifest", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    args = parser.parse_args()

    manifest = pd.read_csv(args.inspection_manifest)
    missing = sorted(REQUIRED_COLUMNS - set(manifest.columns))
    if missing:
        raise ValueError(f"Inspection manifest is missing columns: {missing}")
    output = []
    for _, row in manifest.iterrows():
        mask_path = Path(str(row["mask_path"]).replace("${HOME}", str(Path.home()))).expanduser()
        if not mask_path.is_absolute():
            mask_path = args.inspection_manifest.parent / mask_path
        features = vision_features_from_probability_mask(
            load_probability_mask(mask_path),
            pixel_size_x=float(row["pixel_size_x"]),
            pixel_size_y=float(row["pixel_size_y"]),
            origin_x=float(row["origin_x"]),
            origin_y=float(row["origin_y"]),
            flip_y=truthy(row["flip_y"]),
        )
        output.append(
            {
                "observation_space_version": "reality_obs_v1",
                "asset_id": str(row["asset_id"]),
                "inspection_id": str(row["inspection_id"]),
                "timestamp": str(row["timestamp"]),
                "cycle": float(row["cycle"]),
                "coordinate_frame": str(row["coordinate_frame"]),
                "registration_id": str(row["registration_id"]),
                "maintenance_event": row.get("maintenance_event", False),
                "umax": float(row["umax"]),
                "mask_path": str(mask_path),
                **features,
            }
        )
    table = pd.DataFrame(output).sort_values(["timestamp", "cycle"])
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output_csv, index=False)
    print(f"Wrote {len(table)} registered vision observations to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
