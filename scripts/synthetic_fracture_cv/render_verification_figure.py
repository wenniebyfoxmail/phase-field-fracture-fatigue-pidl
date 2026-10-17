#!/usr/bin/env python3
"""Render one compact, non-claim-bearing G1 construction-check figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image


CASES = ("zero", "translation", "affine_strain", "opening_2px", "opening_4px", "closed_slit", "opening_0p25px")


def render_figure(manifest_path: Path, output_path: Path) -> None:
    records = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    by_case = {record["state_id"]: record for record in records if record["reference_texture_id"] == "texture_1701"}
    fig, axes = plt.subplots(2, 4, figsize=(10, 5.2), constrained_layout=True)
    for axis, case in zip(axes.ravel(), CASES):
        record = by_case[case]
        axis.imshow(Image.open(root / record["image_path"]), cmap="gray", vmin=0, vmax=255)
        axis.set_title(f"{case}\nstatus: {record['target_status']}", fontsize=9)
        axis.set_axis_off()
    axes.ravel()[-1].set_axis_off()
    fig.suptitle("S02-E002 G1 analytic construction checks (seed 1701)\nNot an image-recoverability result", fontsize=11)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render_figure(args.manifest, args.output)
    print(json.dumps({"status": "generated", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

