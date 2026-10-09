#!/usr/bin/env python3
"""S03-E006 held-out D01 local-footprint registration qualification."""

from __future__ import annotations

import argparse
import binascii
import csv
import hashlib
import json
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

from d01_multiview_repeatability import load_gray, register, warp_image
from d01_remote_manifest_audit import extract_entry


PROTOCOL = "S03-E006-v1"
MIN_FIXED_INLIERS = 50
MIN_FIXED_RATIO = 0.20
MIN_MOVING_INLIERS = 15
MIN_MOVING_RATIO = 0.30
MAX_REPROJECTION_NATIVE_PX = 3.0
MIN_FIXED_OVERLAP = 0.90
MIN_NORMALIZED_SUPPORT = 0.75


SELECTION = {
    "Beam 4": {
        "reference": "Beam 4/G4-IB-Fixed/G4-IB_ref1.JPG",
        "low_fixed": "Beam 4/G4-IB-Fixed/G4-IB_t=225.JPG",
        "high_fixed": "Beam 4/G4-IB-Fixed/G4-IB_t=588.JPG",
        "low_moving": [
            "Beam 4/G4-IB-Free/1-G4-IB_t=244.png",
            "Beam 4/G4-IB-Free/1-G4-IB_t=249.png",
            "Beam 4/G4-IB-Free/1-G4-IB_t=254.png",
        ],
        "high_moving": [
            "Beam 4/G4-IB-Free/13-G4-IB_t=594.png",
            "Beam 4/G4-IB-Free/13-G4-IB_t=597.png",
            "Beam 4/G4-IB-Free/13-G4-IB_t=600.png",
        ],
    },
    "Beam 5": {
        "reference": "Beam 5/G5-IB-Fixed/G5-IB_ref1.JPG",
        "low_fixed": "Beam 5/G5-IB-Fixed/G5-IB_t=228.JPG",
        "high_fixed": "Beam 5/G5-IB-Fixed/G5-IB_t=729.JPG",
        "low_moving": [
            "Beam 5/G5-IB-Free/1-G5-IB_t=247.png",
            "Beam 5/G5-IB-Free/1-G5-IB_t=248.png",
            "Beam 5/G5-IB-Free/1-G5-IB_t=249.png",
        ],
        "high_moving": [
            "Beam 5/G5-IB-Free/21-G5-IB_t=737.png",
            "Beam 5/G5-IB-Free/21-G5-IB_t=739.png",
            "Beam 5/G5-IB-Free/21-G5-IB_t=741.png",
        ],
    },
    "Beam 6": {
        "reference": "Beam 6/G6-IB-Fixed/G6-IB_ref1.JPG",
        "low_fixed": "Beam 6/G6-IB-Fixed/G6-IB_t=183.JPG",
        "high_fixed": "Beam 6/G6-IB-Fixed/G6-IB_t=460.JPG",
        "low_moving": [
            "Beam 6/G6-IB-Free/1-G6-IB_t=03_18.png",
            "Beam 6/G6-IB-Free/1-G6-IB_t=03_21.png",
            "Beam 6/G6-IB-Free/1-G6-IB_t=03_23.png",
        ],
        "high_moving": [
            "Beam 6/G6-IB-Free/13-G6-IB_t=07_48.png",
            "Beam 6/G6-IB-Free/13-G6-IB_t=07_50.png",
            "Beam 6/G6-IB-Free/13-G6-IB_t=07_53.png",
        ],
    },
}


def selected_paths() -> list[str]:
    paths = []
    for spec in SELECTION.values():
        paths.extend([spec["reference"], spec["low_fixed"], spec["high_fixed"]])
        paths.extend(spec["low_moving"])
        paths.extend(spec["high_moving"])
    return paths


def retrieve(manifest_path: Path, raw_root: Path) -> list[dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefix = "Monitoring of structural performance of cracked reinforced concrete using DIC and CMfM/"
    entries = {
        str(row["path"])[len(prefix) :]: row
        for row in manifest["entries"]
        if str(row["path"]).startswith(prefix)
    }
    missing = sorted(set(selected_paths()) - set(entries))
    if missing:
        raise RuntimeError(f"selected files absent from remote manifest: {missing}")

    def retrieve_one(relative: str) -> dict[str, object]:
        row = entries[relative]
        target = raw_root / relative
        if target.exists():
            data = target.read_bytes()
            if len(data) != int(row["uncompressed_bytes"]):
                raise RuntimeError(f"existing file size mismatch: {target}")
            crc = f"{binascii.crc32(data) & 0xFFFFFFFF:08x}"
            if crc != row["crc32"]:
                raise RuntimeError(f"existing file CRC mismatch: {target}")
            return {
                "path": prefix + relative,
                "saved_as": relative,
                "bytes": len(data),
                "crc32": crc,
                "sha256": hashlib.sha256(data).hexdigest(),
                "reused": True,
            }
        receipt = extract_entry(manifest["source_url"], row, raw_root)
        receipt["reused"] = False
        return receipt

    with ThreadPoolExecutor(max_workers=6) as executor:
        return list(executor.map(retrieve_one, selected_paths()))


def transformed_corners(shape: tuple[int, int], homography: np.ndarray) -> np.ndarray:
    height, width = shape
    corners = np.float32([[[0, 0]], [[width - 1, 0]], [[width - 1, height - 1]], [[0, height - 1]]])
    return cv2.perspectiveTransform(corners, homography).reshape(-1, 2)


def footprint_valid(corners: np.ndarray) -> bool:
    if not np.isfinite(corners).all():
        return False
    contour = corners.astype(np.float32).reshape(-1, 1, 2)
    return bool(cv2.isContourConvex(contour) and cv2.contourArea(contour) > 0)


def evaluate_registration(reg, role: str, corners: np.ndarray | None) -> tuple[bool, str]:
    failures = []
    if reg.homography is None:
        return False, "homography_failed"
    if role == "fixed":
        if reg.inliers < MIN_FIXED_INLIERS:
            failures.append("inliers")
        if reg.inlier_ratio < MIN_FIXED_RATIO:
            failures.append("inlier_ratio")
        if reg.overlap_fraction < MIN_FIXED_OVERLAP:
            failures.append("reference_overlap")
    else:
        if reg.inliers < MIN_MOVING_INLIERS:
            failures.append("inliers")
        if reg.inlier_ratio < MIN_MOVING_RATIO:
            failures.append("inlier_ratio")
        if corners is None or not footprint_valid(corners):
            failures.append("footprint")
    if reg.median_reprojection_native_px > MAX_REPROJECTION_NATIVE_PX:
        failures.append("reprojection")
    return not failures, "ok" if not failures else "+".join(failures)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyse(raw_root: Path):
    registration_rows = []
    support_rows = []
    figure_data = []
    all_valid = True

    for beam, spec in SELECTION.items():
        reference, reference_scale, _ = load_gray(raw_root / spec["reference"])
        fixed_masks = {}
        for stop in ("low", "high"):
            relative = spec[f"{stop}_fixed"]
            image, _, _ = load_gray(raw_root / relative)
            reg = register(image, reference, reference_scale)
            corners = transformed_corners(image.shape, reg.homography) if reg.homography is not None else None
            valid, reason = evaluate_registration(reg, "fixed", corners)
            all_valid &= valid
            if reg.homography is not None:
                _, fixed_masks[stop] = warp_image(image, reg.homography, reference.shape)
            registration_rows.append(
                {
                    "beam_id": beam,
                    "stop": stop,
                    "role": "fixed",
                    "path": relative,
                    "ratio_matches": reg.matches,
                    "inliers": reg.inliers,
                    "inlier_ratio": reg.inlier_ratio,
                    "median_reprojection_native_px": reg.median_reprojection_native_px,
                    "reference_overlap_fraction": reg.overlap_fraction,
                    "footprint_area_px": int(fixed_masks[stop].sum()) if stop in fixed_masks else 0,
                    "valid": valid,
                    "reason": reason,
                }
            )

        moving_masks = {"low": [], "high": []}
        moving_corners = {"low": [], "high": []}
        for stop in ("low", "high"):
            for relative in spec[f"{stop}_moving"]:
                image, _, _ = load_gray(raw_root / relative)
                reg = register(image, reference, reference_scale)
                corners = transformed_corners(image.shape, reg.homography) if reg.homography is not None else None
                valid, reason = evaluate_registration(reg, "moving", corners)
                all_valid &= valid
                area = 0
                if reg.homography is not None:
                    _, mask = warp_image(image, reg.homography, reference.shape)
                    area = int(mask.sum())
                    moving_masks[stop].append(mask)
                    moving_corners[stop].append(corners)
                registration_rows.append(
                    {
                        "beam_id": beam,
                        "stop": stop,
                        "role": "moving",
                        "path": relative,
                        "ratio_matches": reg.matches,
                        "inliers": reg.inliers,
                        "inlier_ratio": reg.inlier_ratio,
                        "median_reprojection_native_px": reg.median_reprojection_native_px,
                        "reference_overlap_fraction": reg.overlap_fraction,
                        "footprint_area_px": area,
                        "valid": valid,
                        "reason": reason,
                    }
                )

        stop_intersections = {}
        for stop in ("low", "high"):
            masks = moving_masks[stop]
            if len(masks) != 3:
                support = float("nan")
                intersection = np.zeros(reference.shape, dtype=bool)
            else:
                intersection = np.logical_and.reduce(masks)
                support = float(intersection.sum() / min(mask.sum() for mask in masks))
            stop_intersections[stop] = intersection
            support_rows.append(
                {
                    "beam_id": beam,
                    "support_type": f"{stop}_same_stop",
                    "intersection_area_px": int(intersection.sum()),
                    "denominator_area_px": int(min((mask.sum() for mask in masks), default=0)),
                    "normalized_support": support,
                    "primary_threshold": MIN_NORMALIZED_SUPPORT,
                    "pass": bool(np.isfinite(support) and support >= MIN_NORMALIZED_SUPPORT),
                }
            )
        cross = stop_intersections["low"] & stop_intersections["high"]
        denominator = min(stop_intersections["low"].sum(), stop_intersections["high"].sum())
        cross_support = float(cross.sum() / denominator) if denominator else float("nan")
        support_rows.append(
            {
                "beam_id": beam,
                "support_type": "cross_stop",
                "intersection_area_px": int(cross.sum()),
                "denominator_area_px": int(denominator),
                "normalized_support": cross_support,
                "primary_threshold": MIN_NORMALIZED_SUPPORT,
                "pass": bool(np.isfinite(cross_support) and cross_support >= MIN_NORMALIZED_SUPPORT),
            }
        )
        figure_data.append((beam, reference, moving_corners, cross, [row for row in support_rows if row["beam_id"] == beam]))

    finite_supports = [float(row["normalized_support"]) for row in support_rows if np.isfinite(float(row["normalized_support"]))]
    minimum_support = min(finite_supports) if finite_supports else float("nan")
    if not all_valid:
        decision = "INADMISSIBLE_D01_LOCAL_REGISTRATION_HOLDOUT"
        verdict = "inadmissible"
    elif len(finite_supports) != 9:
        decision = "INADMISSIBLE_D01_LOCAL_REGISTRATION_HOLDOUT"
        verdict = "inadmissible"
    elif minimum_support >= MIN_NORMALIZED_SUPPORT:
        decision = "PASS_D01_LOCAL_REGISTRATION_HOLDOUT"
        verdict = "supports"
    else:
        decision = "NO_GO_D01_LOCAL_REGISTRATION_HOLDOUT"
        verdict = "negative"
    payload = {
        "protocol": PROTOCOL,
        "decision": decision,
        "scientific_verdict": verdict,
        "validity_passed": bool(all_valid),
        "primary_threshold": MIN_NORMALIZED_SUPPORT,
        "minimum_normalized_support": minimum_support,
        "primary_passed": decision == "PASS_D01_LOCAL_REGISTRATION_HOLDOUT",
        "independent_units": 3,
        "development_region": "IA",
        "holdout_region": "IB",
        "scale_status": "ruler_reference_present_but_pixels_per_mm_not_qualified",
        "claim_boundary": "local registration evidence only; no crack measurement or prediction claim",
    }
    return registration_rows, support_rows, payload, figure_data


def make_figure(figure_data, output: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(13, 12), gridspec_kw={"width_ratios": [1.45, 1]})
    colors = {"low": "#4477AA", "high": "#EE6677"}
    for row_index, (beam, reference, corners_by_stop, cross, supports) in enumerate(figure_data):
        ax = axes[row_index, 0]
        ax.imshow(reference, cmap="gray", vmin=0, vmax=255)
        for stop in ("low", "high"):
            for corners in corners_by_stop[stop]:
                if corners is not None:
                    closed = np.vstack([corners, corners[0]])
                    ax.plot(closed[:, 0], closed[:, 1], color=colors[stop], linewidth=1.3, alpha=0.9)
        overlay = np.zeros((*cross.shape, 4), dtype=float)
        overlay[cross] = (0.95, 0.75, 0.1, 0.35)
        ax.imshow(overlay)
        ax.set_title(f"{beam}: IB footprints on fixed reference")
        ax.axis("off")
        ax = axes[row_index, 1]
        labels = [row["support_type"].replace("_", " ") for row in supports]
        values = [float(row["normalized_support"]) for row in supports]
        ax.bar(labels, values, color=["#4477AA", "#EE6677", "#228833"])
        ax.axhline(MIN_NORMALIZED_SUPPORT, color="black", linestyle="--", label="frozen minimum = 0.75")
        ax.set_ylim(0, 1.06)
        ax.set_ylabel("intersection / smaller footprint")
        ax.set_title(f"{beam}: local support")
        ax.tick_params(axis="x", rotation=18)
        ax.legend(frameon=False, loc="lower right")
    fig.suptitle(
        "S03-E006 held-out IB local-footprint registration\n"
        "Controlled experiment | all beams shown | geometry only",
        fontsize=14,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output / "d01_local_registration_holdout.png", dpi=180)
    fig.savefig(output / "d01_local_registration_holdout.pdf")
    plt.close(fig)


def self_test() -> None:
    assert len(selected_paths()) == 27 and len(set(selected_paths())) == 27
    square = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float32)
    assert footprint_valid(square)
    assert not footprint_valid(np.array([[0, 0], [10, 10], [10, 0], [0, 10]], dtype=np.float32))
    masks = [np.zeros((20, 20), dtype=bool) for _ in range(3)]
    masks[0][2:12, 2:12] = True
    masks[1][3:13, 2:12] = True
    masks[2][2:12, 3:13] = True
    support = np.logical_and.reduce(masks).sum() / min(mask.sum() for mask in masks)
    assert abs(support - 0.81) < 1e-12
    print("SELF_TEST_PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.manifest is None or args.output is None:
        parser.error("--manifest and --output are required unless --self-test is used")

    args.output.mkdir(parents=True, exist_ok=True)
    raw_root = args.output / "raw_images"
    raw_root.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    receipts = retrieve(args.manifest, raw_root)
    (args.output / "selection_manifest.json").write_text(
        json.dumps({"protocol": PROTOCOL, "files": receipts}, indent=2) + "\n",
        encoding="utf-8",
    )
    registrations, supports, decision, figure_data = analyse(raw_root)
    write_csv(args.output / "registration_metrics.csv", registrations)
    write_csv(args.output / "support_metrics.csv", supports)
    (args.output / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    make_figure(figure_data, args.output)
    ended = datetime.now(timezone.utc)
    receipt = {
        "protocol": PROTOCOL,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
        "duration_seconds": (ended - started).total_seconds(),
        "producer": "Mac local deterministic CPU",
        "hostname": platform.node(),
        "python": sys.version,
        "opencv": cv2.__version__,
        "command": " ".join(sys.argv),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()),
        "selected_files": len(receipts),
    }
    (args.output / "run_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
