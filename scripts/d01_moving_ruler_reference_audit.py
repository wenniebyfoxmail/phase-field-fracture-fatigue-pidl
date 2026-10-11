#!/usr/bin/env python3
"""Retrieve only three preregistered development ruler references, never ref2."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from d01_remote_manifest_audit import extract_entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
    if dirty:
        raise RuntimeError("commit acquisition source before execution")
    if args.output.exists():
        raise FileExistsError("fresh output required")
    manifest = json.loads(args.manifest.read_text())
    suffixes = [f"Beam {b}/G{b}-IB-Free/1-G{b}-IB_ref.png" for b in (4, 5, 6)]
    selected = []
    for suffix in suffixes:
        matches = [r for r in manifest["entries"] if r["path"].endswith("/" + suffix)]
        if len(matches) != 1:
            raise ValueError(f"non-unique source entry: {suffix}")
        selected.append(matches[0])
    args.output.mkdir(parents=True)
    receipt = {
        "experiment_id": "S03-E009", "run_id": "S03-E009-R001",
        "role": "dataset_acquisition_only", "protocol": "acquisition-v1",
        "producer": "Mac-PIDL", "hostname": socket.gethostname(), "pid": os.getpid(),
        "commit": commit, "git_dirty": False, "python": sys.executable,
        "runtime": platform.python_version(), "command": sys.argv,
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "gpu": None,
        "source_manifest": str(args.manifest), "source_url": manifest["source_url"],
        "execution": "running", "retrieval": "pending", "files": [],
        "reserved_ref2_accessed": False,
    }
    def save():
        (args.output / "run_receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    save()
    fig, axes = plt.subplots(1, 3, figsize=(12, 7))
    for row, ax in zip(selected, axes):
        file_receipt = extract_entry(manifest["source_url"], row, args.output / "raw_images")
        path = args.output / "raw_images" / file_receipt["saved_as"]
        im = cv2.imread(str(path))
        if im is None:
            raise ValueError(f"decode failed: {path}")
        h, w = im.shape[:2]
        file_receipt.update(width_px=w, height_px=h, crc_size_decode_ok=True, role="development")
        receipt["files"].append(file_receipt)
        save()
        ax.imshow(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        ax.set_title(f"{Path(file_receipt['saved_as']).parts[0]} | {w} x {h} px")
        ax.set(xlabel="Native x (px)", ylabel="Native y (px)")
    fig.suptitle("S03-E009-R001 | all three moving IB ruler references | development data audit")
    fig.tight_layout()
    fig.savefig(args.output / "moving_reference_inventory.png", dpi=180)
    plt.close(fig)
    receipt.update(execution="succeeded", retrieval="verified",
                   ended_at_utc=datetime.now(timezone.utc).isoformat())
    save()
    print(json.dumps({"files": len(receipt["files"]), "all_crc_size_decode_ok": True,
                      "reserved_ref2_accessed": False, "execution": "succeeded"}))


if __name__ == "__main__":
    main()
