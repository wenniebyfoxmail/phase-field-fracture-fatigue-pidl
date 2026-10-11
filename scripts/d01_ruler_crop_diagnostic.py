#!/usr/bin/env python3
"""S03-E008 development-only, one-factor crop audit on six viewed references."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
from unittest.mock import patch

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import d01_directional_scale_repeatability as frozen


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.output.exists():
        raise FileExistsError("fresh output required; never overwrite a diagnostic")
    if git(repo, "status", "--porcelain"):
        raise RuntimeError("commit diagnostic code before execution")
    args.output.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    receipt = {
        "experiment_id": "S03-E008", "run_id": "S03-E008-R001",
        "role": "development_diagnostic", "protocol": "diagnostic-v1",
        "producer": "Mac-PIDL", "hostname": socket.gethostname(),
        "commit": git(repo, "rev-parse", "HEAD"), "git_dirty": False,
        "python": sys.executable, "runtime": platform.python_version(),
        "opencv": cv2.__version__, "numpy": np.__version__,
        "command": sys.argv, "started_at_utc": started,
        "output": str(args.output.resolve()), "execution": "running",
        "gpu": None, "formal_claim_execution": False,
    }
    write_json(args.output / "run_receipt.json", receipt)
    selection = json.loads((args.archive / "S03-E007/analysis/selection_manifest.json").read_text())
    baseline_csv = args.archive / "S03-E007/runs/S03-E007-R001/formal_metrics.csv"
    with baseline_csv.open(newline="") as handle:
        archived = {r["saved_as"]: r for r in csv.DictReader(handle) if r["row_type"] == "image"}
    rows, comparisons, failed_views = [], [], {}
    checked = []
    keys = ("nominal_period_px", "tick_count", "max_tick_step", "ransac_inlier_count",
            "lomo_count", "lomo_p95_mm", "lomo_median_mm", "spacing_cv")
    for item in selection["files"]:
        saved = item["saved_as"]
        source = args.archive / "S03-E007/raw_images" / saved
        if frozen.sha256_file(source) != item["sha256"]:
            raise RuntimeError(f"input identity mismatch: {saved}")
        image = cv2.imread(str(source))
        if image is None or image.shape[:2] != (item["height_px"], item["width_px"]):
            raise RuntimeError(f"input decoding mismatch: {saved}")
        beam, reference = frozen._beam_and_reference(saved)
        for arm, fraction in (("baseline", 0.50), ("crop_two_thirds", 2 / 3)):
            with patch.object(frozen, "BOTTOM_FRACTION", fraction):
                metrics, arrays = frozen.analyze_image(image)
            row = {"beam": beam, "reference": reference, "arm": arm,
                   "saved_as": saved, "bottom_fraction": fraction,
                   "search_start_y": int(image.shape[0] * (1 - fraction)),
                   **{k: metrics[k] for k in keys},
                   **{k: metrics[k] for k in ("monotone", "finite", "validity_pass")}}
            for k, v in zip(("boundary_x1", "boundary_y1", "boundary_x2", "boundary_y2", "boundary_angle_deg"), metrics["boundary"]):
                row[k] = v
            if arm == "baseline":
                old = archived[saved]
                for key in (*keys, "boundary_x1", "boundary_y1", "boundary_x2", "boundary_y2", "boundary_angle_deg"):
                    if not np.isclose(float(row[key]), float(old[key]), rtol=1e-9, atol=1e-9):
                        raise RuntimeError(f"baseline reproduction mismatch: {saved} {key}")
                for key in ("monotone", "finite", "validity_pass"):
                    if bool(row[key]) != (old[key] == "True"):
                        raise RuntimeError(f"baseline reproduction mismatch: {saved} {key}")
                checked.append(saved)
            rows.append(row)
            stem = f"{beam.replace(' ', '')}_{reference}_{arm}"
            np.savez_compressed(args.output / f"{stem}.npz", **arrays)
            if beam == "Beam 6" and reference == "ref2":
                failed_views[arm] = (image, metrics, arrays)
        comparisons.append(rows[-2:])
    with (args.output / "comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(args.output / "baseline_reproduction.json", {
        "source_csv": str(baseline_csv), "checked_images": checked,
        "checked_fields": list(keys) + ["boundary", "finite", "monotone", "validity_pass"],
        "all_match": len(checked) == 6,
    })

    # All six cases are displayed, including the five originally successful cases.
    labels = [f"{p[0]['beam']}\n{p[0]['reference']}" for p in comparisons]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(6)
    for shift, arm, color in ((-.18, "baseline", "#0072B2"), (.18, "crop_two_thirds", "#D55E00")):
        counts = [next(r for r in p if r["arm"] == arm)["tick_count"] for p in comparisons]
        bars = ax.bar(x + shift, counts, width=.34, label=arm.replace("_", " "), color=color)
        ax.bar_label(bars, padding=3)
    ax.axhline(50, color="#555555", linestyle="--", label="old >=50 condition (diagnostic)")
    ax.set(xticks=x, xticklabels=labels, ylabel="Indexed peaks (not independently labelled mm)",
           ylim=(0, max(r["tick_count"] for r in rows) * 1.25))
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("S03-E008-R001 | all six viewed fixed references | development only")
    fig.tight_layout()
    fig.savefig(args.output / "coverage_comparison.png", dpi=180)
    fig.savefig(args.output / "coverage_comparison.pdf")
    plt.close(fig)

    render_failed_case(failed_views, args.output)

    manifest = json.loads((args.archive / "S03-E004/analysis/remote_zip_manifest.json").read_text())
    reserved = [r for r in manifest["entries"] if "-IB-Free/" in r["path"] and "_ref" in r["path"]]
    local_refs = {}
    for experiment in ("S03-E004", "S03-E005", "S03-E006", "S03-E007"):
        for path in (args.archive / experiment).rglob("*ref*.png"):
            local_refs.setdefault(path.name, []).append(str(path))
    inventory = [{**r, "local_matches_in_S03_E004_to_E007": local_refs.get(Path(r["path"]).name, []),
                  "pixel_access_in_this_run": False,
                  "role": "candidate_camera_transfer_same_beams_not_specimen_holdout"} for r in reserved]
    write_json(args.output / "reserved_reference_inventory.json", inventory)
    baseline_count = sum(r["validity_pass"] for r in rows if r["arm"] == "baseline")
    candidate_count = sum(r["validity_pass"] for r in rows if r["arm"] != "baseline")
    summary = {
        "baseline_covered_images": baseline_count, "candidate_covered_images": candidate_count,
        "total_images": 6, "independent_beams": 3,
        "engineering_repair_trigger": candidate_count == 6,
        "scientific_verdict": "DIAGNOSTIC_ONLY", "research_disposition": "repair",
        "physical_coordinate_validated": False, "independent_reference": None,
        "reserved_moving_IB_references": len(inventory),
        "reserved_local_matches": sum(bool(r["local_matches_in_S03_E004_to_E007"]) for r in inventory),
    }
    write_json(args.output / "summary.json", summary)
    receipt.update(execution="succeeded", retrieval="verified_local", ended_at_utc=datetime.now(timezone.utc).isoformat())
    write_json(args.output / "run_receipt.json", receipt)
    print(json.dumps(summary, indent=2))


def render_failed_case(failed_views: dict, output: Path) -> None:
    """Render existing arrays only; changing presentation does not rerun scores."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), gridspec_kw={"height_ratios": [2, 1]})
    for col, (arm, (image, metrics, arrays)) in enumerate(failed_views.items()):
        ax = axes[0, col]
        ax.imshow(cv2.cvtColor(image[1500:2800, :3400], cv2.COLOR_BGR2RGB), extent=(0, 3400, 2800, 1500))
        x1, y1, x2, y2, _ = metrics["boundary"]
        ax.plot([x1, x2], [y1, y2], color="#56B4E9", lw=2, label="chosen line")
        tx = arrays["tick_x"]
        ty = y1 + (y2-y1) * (tx-x1) / (x2-x1) + 40
        ax.scatter(tx, ty, s=8, color="#E69F00", label="indexed peaks")
        search_start = int(image.shape[0] * (1 - (0.5 if arm == "baseline" else 2 / 3)))
        if 1500 <= search_start <= 2800:
            ax.axhline(search_start, color="#CC79A7", ls="--", label="search starts here")
        else:
            ax.text(.02, .04, f"search starts y={search_start} (above displayed crop)", transform=ax.transAxes,
                    color="white", bbox={"facecolor": "black", "alpha": .65})
        ax.set_title(f"{arm}: {metrics['tick_count']} peaks; period {metrics['nominal_period_px']:.0f} px")
        ax.set(xlabel="Native x (px)", ylabel="Native y (px)")
        ax.legend(loc="upper right", fontsize=8)
        signal = arrays["response"] - arrays["response"].mean()
        ac = np.correlate(signal, signal, mode="full")[len(signal)-1:]
        lags = np.arange(1, 61)
        axes[1, col].plot(lags, ac[lags] / ac[0], color="#0072B2", lw=1.5)
        axes[1, col].axvspan(8, 30, color="gray", alpha=.1, label="frozen search interval")
        axes[1, col].axvline(metrics["nominal_period_px"], color="#D55E00", ls="--")
        axes[1, col].set(xlabel="Lag (native px)", ylabel="Autocorrelation / lag-0", ylim=(-1, 1))
    fig.suptitle("S03-E008-R001 | Beam 6 ref2 | one changed crop | development, controlled experiment")
    fig.tight_layout()
    fig.savefig(output / "beam6_ref2_crop_audit.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
