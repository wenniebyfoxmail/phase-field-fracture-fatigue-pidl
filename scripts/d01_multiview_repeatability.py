#!/usr/bin/env python3
"""Frozen no-training D01 fixed-versus-moving-view repeatability diagnostic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps

from d01_remote_manifest_audit import extract_entry


PROTOCOL = "S03-E005-v1"
MAX_SIDE = 2000
LOWE_RATIO = 0.75
RANSAC_THRESHOLD_WORKING_PX = 2.0
MIN_INLIERS = 50
MIN_INLIER_RATIO = 0.20
MAX_REPROJECTION_NATIVE_PX = 3.0
MIN_VIEW_OVERLAP = 0.50
MIN_COMMON_COVERAGE = 0.30
MASK_EROSION_PX = 20
RIDGE_KERNELS = (9, 17, 33)


SELECTION = {
    "Beam 4": {
        "low_label": "10 kN",
        "high_label": "50 kN",
        "low_fixed": "Beam 4/G4-IA-Fixed/G4_IA_t=225.jpg",
        "high_fixed": "Beam 4/G4-IA-Fixed/G4_IA_t=588.jpg",
        "low_moving": [
            "Beam 4/G4-IA-Free/2-G4-IA_t=271.png",
            "Beam 4/G4-IA-Free/2-G4-IA_t=278.png",
            "Beam 4/G4-IA-Free/2-G4-IA_t=287.png",
        ],
        "high_moving": [
            "Beam 4/G4-IA-Free/14-G4-IA_t=605.png",
            "Beam 4/G4-IA-Free/14-G4-IA_t=608.png",
            "Beam 4/G4-IA-Free/14-G4-IA_t=611.png",
        ],
        "references": [
            "Beam 4/G4-IA-Fixed/G4_IA_ref1.jpg",
            "Beam 4/G4-IA-Fixed/G4_IA_ref2.jpg",
            "Beam 4/G4-IA-Free/2-G4-IA_t=270ref.png",
        ],
    },
    "Beam 5": {
        "low_label": "10 kN",
        "high_label": "60 kN",
        "low_fixed": "Beam 5/G5-IA-Fixed/G5_IA_t=228.jpg",
        "high_fixed": "Beam 5/G5-IA-Fixed/G5_IA_t=729.jpg",
        "low_moving": [
            "Beam 5/G5-IA-Free/2-G5-IA_t=265.png",
            "Beam 5/G5-IA-Free/2-G5-IA_t=269.png",
            "Beam 5/G5-IA-Free/2-G5-IA_t=271.png",
        ],
        "high_moving": [
            "Beam 5/G5-IA-Free/22-G5-IA_t=746.png",
            "Beam 5/G5-IA-Free/22-G5-IA_t=748.png",
            "Beam 5/G5-IA-Free/22-G5-IA_t=751.png",
        ],
        "references": [
            "Beam 5/G5-IA-Fixed/G5_IA_t=22_ref.jpg",
            "Beam 5/G5-IA-Fixed/G5_IA_t=23_ref.jpg",
            "Beam 5/G5-IA-Free/2-G5-IA_ref.png",
        ],
    },
    "Beam 6": {
        "low_label": "10 kN",
        "high_label": "40 kN",
        "low_fixed": "Beam 6/G6-IA-Fixed/G6_IA_t=183.jpg",
        "high_fixed": "Beam 6/G6-IA-Fixed/G6_IA_t=460.jpg",
        "low_moving": [
            "Beam 6/G6-IA-Free/2-G6-IA_t=03_34.png",
            "Beam 6/G6-IA-Free/2-G6-IA_t=03_36.png",
            "Beam 6/G6-IA-Free/2-G6-IA_t=03_39.png",
        ],
        "high_moving": [
            "Beam 6/G6-IA-Free/14-G6-IA_t=07_58.png",
            "Beam 6/G6-IA-Free/14-G6-IA_t=08_00.png",
            "Beam 6/G6-IA-Free/14-G6-IA_t=08_03.png",
        ],
        "references": [
            "Beam 6/G6-IA-Fixed/G6_IA_t=40_ref.jpg",
            "Beam 6/G6-IA-Fixed/G6_IA_t=41_ref.jpg",
            "Beam 6/G6-IA-Free/2-G6-IA_ref.png",
        ],
    },
}


@dataclass
class Registration:
    homography: np.ndarray | None
    matches: int
    inliers: int
    inlier_ratio: float
    median_reprojection_native_px: float
    overlap_fraction: float
    valid: bool
    reason: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_gray(path: Path) -> tuple[np.ndarray, float, tuple[int, int]]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("L")
        native = np.asarray(image)
    height, width = native.shape
    scale = min(1.0, MAX_SIDE / max(height, width))
    if scale < 1.0:
        work = cv2.resize(
            native,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
    else:
        work = native.copy()
    return work, scale, (height, width)


def feature_image(gray: np.ndarray) -> np.ndarray:
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


def register(source: np.ndarray, destination: np.ndarray, destination_scale: float) -> Registration:
    sift = cv2.SIFT_create(nfeatures=8000, contrastThreshold=0.02, edgeThreshold=10, sigma=1.6)
    kp_src, des_src = sift.detectAndCompute(feature_image(source), None)
    kp_dst, des_dst = sift.detectAndCompute(feature_image(destination), None)
    if des_src is None or des_dst is None or len(kp_src) < 2 or len(kp_dst) < 2:
        return Registration(None, 0, 0, 0.0, float("inf"), 0.0, False, "insufficient_descriptors")
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(des_src, des_dst, k=2)
    good = [first for first, second in pairs if first.distance < LOWE_RATIO * second.distance]
    if len(good) < 4:
        return Registration(None, len(good), 0, 0.0, float("inf"), 0.0, False, "insufficient_ratio_matches")
    src_points = np.float32([kp_src[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_points = np.float32([kp_dst[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(
        src_points,
        dst_points,
        cv2.RANSAC,
        RANSAC_THRESHOLD_WORKING_PX,
        maxIters=5000,
        confidence=0.999,
    )
    if homography is None or mask is None:
        return Registration(None, len(good), 0, 0.0, float("inf"), 0.0, False, "homography_failed")
    inlier_mask = mask.ravel().astype(bool)
    inliers = int(inlier_mask.sum())
    projected = cv2.perspectiveTransform(src_points[inlier_mask], homography)
    error_working = np.linalg.norm(projected - dst_points[inlier_mask], axis=2).ravel()
    median_native = float(np.median(error_working) / destination_scale) if inliers else float("inf")
    source_mask = np.ones(source.shape, dtype=np.uint8)
    warped_mask = cv2.warpPerspective(
        source_mask,
        homography,
        (destination.shape[1], destination.shape[0]),
        flags=cv2.INTER_NEAREST,
    )
    overlap = float(np.mean(warped_mask > 0))
    ratio = inliers / len(good)
    failures = []
    if inliers < MIN_INLIERS:
        failures.append("inliers")
    if ratio < MIN_INLIER_RATIO:
        failures.append("inlier_ratio")
    if median_native > MAX_REPROJECTION_NATIVE_PX:
        failures.append("reprojection")
    if overlap < MIN_VIEW_OVERLAP:
        failures.append("overlap")
    return Registration(
        homography,
        len(good),
        inliers,
        float(ratio),
        median_native,
        overlap,
        not failures,
        "ok" if not failures else "+".join(failures),
    )


def ridge_response(gray: np.ndarray) -> np.ndarray:
    enhanced = feature_image(gray)
    responses = []
    for size in RIDGE_KERNELS:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        responses.append(cv2.morphologyEx(enhanced, cv2.MORPH_BLACKHAT, kernel))
    return np.max(np.stack(responses, axis=0), axis=0).astype(np.float32) / 255.0


def warp_image(image: np.ndarray, homography: np.ndarray, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    warped = cv2.warpPerspective(image, homography, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(
        np.ones(image.shape, dtype=np.uint8),
        homography,
        (shape[1], shape[0]),
        flags=cv2.INTER_NEAREST,
    ) > 0
    return warped, mask


def registration_row(beam: str, stop: str, role: str, path: str, reg: Registration) -> dict[str, object]:
    return {
        "beam_id": beam,
        "stop": stop,
        "role": role,
        "path": path,
        "ratio_matches": reg.matches,
        "inliers": reg.inliers,
        "inlier_ratio": reg.inlier_ratio,
        "median_reprojection_native_px": reg.median_reprojection_native_px,
        "overlap_fraction": reg.overlap_fraction,
        "valid": reg.valid,
        "reason": reg.reason,
    }


def all_selected_paths() -> list[str]:
    paths = []
    for spec in SELECTION.values():
        paths.extend([spec["low_fixed"], spec["high_fixed"]])
        paths.extend(spec["low_moving"])
        paths.extend(spec["high_moving"])
        paths.extend(spec["references"])
    return paths


def retrieve(manifest_path: Path, raw_root: Path) -> list[dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefix = "Monitoring of structural performance of cracked reinforced concrete using DIC and CMfM/"
    by_relative = {}
    for row in manifest["entries"]:
        path = str(row["path"])
        if path.startswith(prefix):
            by_relative[path[len(prefix) :]] = row
    missing = sorted(set(all_selected_paths()) - set(by_relative))
    if missing:
        raise RuntimeError(f"selected files absent from remote manifest: {missing}")
    receipts = []
    for relative in all_selected_paths():
        row = by_relative[relative]
        target = raw_root / relative
        if target.exists():
            if target.stat().st_size != int(row["uncompressed_bytes"]):
                raise RuntimeError(f"existing file size mismatch: {target}")
            receipts.append(
                {
                    "path": prefix + relative,
                    "saved_as": relative,
                    "bytes": target.stat().st_size,
                    "crc32": row["crc32"],
                    "sha256": sha256(target),
                    "reused": True,
                }
            )
        else:
            receipts.append(extract_entry(manifest["source_url"], row, raw_root))
            receipts[-1]["reused"] = False
    return receipts


def analyse(raw_root: Path, output: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object], dict[str, object]]:
    registration_rows: list[dict[str, object]] = []
    measurement_rows: list[dict[str, object]] = []
    panels = []
    scale_inventory = []
    beam_validity = {}

    for beam, spec in SELECTION.items():
        for reference in spec["references"]:
            image, scale, native_shape = load_gray(raw_root / reference)
            scale_inventory.append(
                {
                    "beam_id": beam,
                    "path": reference,
                    "native_height_px": native_shape[0],
                    "native_width_px": native_shape[1],
                    "working_scale": scale,
                    "ruler_reference_declared_by_source": True,
                    "pixels_per_mm": None,
                    "status": "UNASSESSABLE_WITHOUT_RULER_ANNOTATION",
                }
            )

        low_fixed, low_scale, _ = load_gray(raw_root / spec["low_fixed"])
        high_fixed, high_scale, _ = load_gray(raw_root / spec["high_fixed"])
        high_reg = register(high_fixed, low_fixed, low_scale)
        registration_rows.append(
            registration_row(beam, "high_to_low", "fixed", spec["high_fixed"], high_reg)
        )
        valid = high_reg.valid
        if high_reg.homography is None:
            beam_validity[beam] = {"valid": False, "reason": "fixed_high_to_low_registration_failed"}
            continue
        high_on_low, high_mask = warp_image(high_fixed, high_reg.homography, low_fixed.shape)
        global_mask = high_mask.copy()
        warped_by_stop: dict[str, list[tuple[str, np.ndarray, np.ndarray, Registration]]] = {"low": [], "high": []}

        for stop in ("low", "high"):
            fixed = low_fixed if stop == "low" else high_fixed
            fixed_scale = low_scale if stop == "low" else high_scale
            valid_count = 0
            for relative in spec[f"{stop}_moving"]:
                moving, _, _ = load_gray(raw_root / relative)
                reg = register(moving, fixed, fixed_scale)
                registration_rows.append(registration_row(beam, stop, "moving", relative, reg))
                if not reg.valid or reg.homography is None:
                    continue
                valid_count += 1
                composed = reg.homography if stop == "low" else high_reg.homography @ reg.homography
                warped, mask = warp_image(moving, composed, low_fixed.shape)
                warped_by_stop[stop].append((relative, warped, mask, reg))
                global_mask &= mask
            if valid_count < 2:
                valid = False

        if MASK_EROSION_PX:
            size = 2 * MASK_EROSION_PX + 1
            global_mask = cv2.erode(
                global_mask.astype(np.uint8),
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)),
            ).astype(bool)
        coverage = float(global_mask.mean())
        if coverage < MIN_COMMON_COVERAGE:
            valid = False
        beam_validity[beam] = {
            "valid": bool(valid),
            "common_coverage": coverage,
            "valid_low_views": len(warped_by_stop["low"]),
            "valid_high_views": len(warped_by_stop["high"]),
        }
        if not valid or not global_mask.any():
            continue

        low_ridge = ridge_response(low_fixed)
        high_ridge = ridge_response(high_on_low)
        between = float(np.median(np.abs(low_ridge[global_mask] - high_ridge[global_mask])))
        within = {}
        view_errors = {}
        for stop, fixed_ridge in (("low", low_ridge), ("high", high_ridge)):
            values = []
            for relative, warped, _, _ in warped_by_stop[stop]:
                response = ridge_response(warped)
                value = float(np.median(np.abs(fixed_ridge[global_mask] - response[global_mask])))
                values.append(value)
                view_errors[relative] = value
            within[stop] = float(np.median(values))
        max_within = max(within.values())
        passed = max_within < between
        measurement_rows.append(
            {
                "beam_id": beam,
                "low_stop": spec["low_label"],
                "high_stop": spec["high_label"],
                "valid_low_views": len(warped_by_stop["low"]),
                "valid_high_views": len(warped_by_stop["high"]),
                "common_coverage": coverage,
                "within_low": within["low"],
                "within_high": within["high"],
                "max_within": max_within,
                "between_fixed_change": between,
                "repeatability_to_change_ratio": max_within / between if between > 0 else float("inf"),
                "primary_pass": passed,
            }
        )
        high_views = warped_by_stop["high"]
        representative = sorted(high_views, key=lambda item: view_errors[item[0]])[len(high_views) // 2]
        panels.append((beam, low_fixed, high_on_low, representative[1], global_mask, within, between))

    validity_passed = all(v.get("valid", False) for v in beam_validity.values()) and len(beam_validity) == 3
    if not validity_passed:
        decision = "INADMISSIBLE_D01_MULTIVIEW_REPEATABILITY"
        scientific_verdict = "inadmissible"
    elif len(measurement_rows) != 3:
        decision = "INADMISSIBLE_D01_MULTIVIEW_REPEATABILITY"
        scientific_verdict = "inadmissible"
    elif all(bool(row["primary_pass"]) for row in measurement_rows):
        decision = "PASS_D01_MULTIVIEW_REPEATABILITY_DIAGNOSTIC"
        scientific_verdict = "supports"
    else:
        decision = "NO_GO_D01_MULTIVIEW_REPEATABILITY"
        scientific_verdict = "negative"

    decision_payload = {
        "protocol": PROTOCOL,
        "decision": decision,
        "scientific_verdict": scientific_verdict,
        "validity_passed": validity_passed,
        "primary_criterion": "max(within_low, within_high) < between_fixed_change for all three beams",
        "primary_passed": decision == "PASS_D01_MULTIVIEW_REPEATABILITY_DIAGNOSTIC",
        "beam_validity": beam_validity,
        "physical_scale_status": "UNASSESSABLE_WITHOUT_RULER_ANNOTATION",
        "physical_width_claim_allowed": False,
        "claim_boundary": "dimensionless image-repeatability diagnostic only; fixed-view change is not independent crack truth",
    }
    return registration_rows, measurement_rows, decision_payload, {"rows": scale_inventory, "panels": panels}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(panels: list[tuple], measurements: list[dict[str, object]], output: Path) -> None:
    if not panels:
        return
    fig, axes = plt.subplots(len(panels), 4, figsize=(13, 3.5 * len(panels)), squeeze=False)
    by_beam = {row["beam_id"]: row for row in measurements}
    for row_index, (beam, low, high, moving, mask, within, between) in enumerate(panels):
        display = []
        for image in (low, high, moving):
            clipped = image.copy()
            clipped[~mask] = 0
            display.append(clipped)
        titles = ["fixed low", "fixed high registered", "median-error moving high"]
        for column, (image, title) in enumerate(zip(display, titles)):
            axes[row_index, column].imshow(image, cmap="gray", vmin=0, vmax=255)
            axes[row_index, column].set_title(f"{beam}: {title}")
            axes[row_index, column].axis("off")
        values = [within["low"], within["high"], between]
        colors = ["#4477AA", "#66CCEE", "#CC6677"]
        axes[row_index, 3].bar(["within low", "within high", "between"], values, color=colors)
        axes[row_index, 3].set_ylabel("median absolute ridge difference")
        axes[row_index, 3].set_title(
            f"ratio={by_beam[beam]['repeatability_to_change_ratio']:.2f}; "
            f"pass={by_beam[beam]['primary_pass']}"
        )
        axes[row_index, 3].tick_params(axis="x", rotation=20)
    fig.suptitle(
        "S03-E005 D01 multiview repeatability diagnostic\n"
        "Controlled experiment; fixed-view change is not independent crack truth",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output / "d01_multiview_repeatability.png", dpi=180)
    fig.savefig(output / "d01_multiview_repeatability.pdf")
    plt.close(fig)


def self_test() -> None:
    rng = np.random.default_rng(20261009)
    image = (rng.random((600, 800)) * 255).astype(np.uint8)
    cv2.line(image, (100, 100), (700, 520), 0, 5)
    source_to_destination = np.array([[1.0, 0.01, 18], [-0.01, 1.0, 12], [0.0, 0.0, 1.0]])
    source = cv2.warpPerspective(image, np.linalg.inv(source_to_destination), (800, 600))
    reg = register(source, image, 1.0)
    assert reg.homography is not None and reg.valid, reg
    corners = np.float32([[[0, 0]], [[799, 0]], [[799, 599]], [[0, 599]]])
    expected = cv2.perspectiveTransform(corners, source_to_destination)
    actual = cv2.perspectiveTransform(corners, reg.homography)
    assert float(np.median(np.linalg.norm(expected - actual, axis=2))) < 2.0
    assert ridge_response(image).shape == image.shape
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
    registration, measurements, decision, scale = analyse(raw_root, args.output)
    write_csv(args.output / "registration_metrics.csv", registration)
    write_csv(args.output / "measurement_metrics.csv", measurements)
    (args.output / "scale_audit.json").write_text(
        json.dumps({"status": decision["physical_scale_status"], "references": scale["rows"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    make_figure(scale["panels"], measurements, args.output)
    ended = datetime.now(timezone.utc)
    command = " ".join(sys.argv)
    receipt = {
        "protocol": PROTOCOL,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
        "duration_seconds": (ended - started).total_seconds(),
        "producer": "Mac local deterministic CPU",
        "hostname": platform.node(),
        "python": sys.version,
        "opencv": cv2.__version__,
        "command": command,
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()),
        "selected_files": len(receipts),
    }
    (args.output / "run_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
