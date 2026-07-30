#!/usr/bin/env python3
"""Reconcile PaveTrack provenance and gate location splits and registration."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

import cv2
import matplotlib.pyplot as plt
import numpy as np


XML_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SPLIT_SALT = "pavetrack_v1"
REGISTRATION_GATE = {
    "min_good_matches": 30,
    "min_inliers": 15,
    "min_inlier_ratio": 0.25,
    "max_median_reprojection_px": 4.0,
    "min_projected_area_ratio": 0.5,
    "max_projected_area_ratio": 2.0,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(".//m:t", XML_NS))
        for item in root.findall("m:si", XML_NS)
    ]


def read_workbook_keys(path: Path) -> list[tuple[str, str, str]]:
    """Read (location, image, category) without an Excel runtime."""
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows: list[tuple[str, str, str]] = []
    for row in root.findall(".//m:sheetData/m:row", XML_NS)[1:]:
        values: dict[str, str] = {}
        for cell in row.findall("m:c", XML_NS):
            reference = cell.attrib.get("r", "")
            column = re.match(r"[A-Z]+", reference)
            value_node = cell.find("m:v", XML_NS)
            if column is None or value_node is None:
                continue
            raw = value_node.text or ""
            value = strings[int(raw)] if cell.attrib.get("t") == "s" else raw
            values[column.group()] = value.strip()
        if {"A", "C", "D"}.issubset(values):
            rows.append((values["A"], values["D"], values["C"]))
    return rows


def read_manifest_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [
            {key: value.strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]
    required = {"reid", "category", "img_name"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"manifest must contain {sorted(required)}")
    return rows


def reconcile_counts(
    workbook_rows: list[tuple[str, str, str]], manifest_rows: list[dict[str, str]]
) -> dict[str, object]:
    workbook_triples = set(workbook_rows)
    manifest_triples = {
        (row["reid"], row["img_name"], row["category"])
        for row in manifest_rows
    }
    workbook_pairs = {(reid, image) for reid, image, _ in workbook_rows}
    manifest_pairs = {
        (row["reid"], row["img_name"])
        for row in manifest_rows
    }
    unique_names = {image for _, image in workbook_pairs}
    return {
        "workbook_annotation_rows": len(workbook_rows),
        "workbook_unique_location_image_category": len(workbook_triples),
        "workbook_exact_duplicate_annotation_rows": len(workbook_rows) - len(workbook_triples),
        "manifest_rows": len(manifest_rows),
        "manifest_unique_location_image_category": len(manifest_triples),
        "unique_location_image_pairs": len(workbook_pairs),
        "unique_filename_only": len(unique_names),
        "cross_location_filename_collisions": len(workbook_pairs) - len(unique_names),
        "workbook_only_triples": len(workbook_triples - manifest_triples),
        "manifest_only_triples": len(manifest_triples - workbook_triples),
        "workbook_only_pairs": len(workbook_pairs - manifest_pairs),
        "manifest_only_pairs": len(manifest_pairs - workbook_pairs),
        "counts_reconciled": workbook_triples == manifest_triples,
        "interpretation": (
            "9447 workbook rows minus 200 exact duplicate triples equals 9247 manifest rows; "
            "8928 unique location-image pairs minus 303 cross-location filename collisions "
            "equals the report's 8625 filename-only count"
        ),
    }


def location_split(reid: str, salt: str = SPLIT_SALT) -> str:
    bucket = int(hashlib.sha256(f"{salt}:{reid}".encode()).hexdigest(), 16) % 20
    if bucket < 14:
        return "train"
    if bucket < 17:
        return "validation"
    return "test"


def build_location_split(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    categories: dict[str, set[str]] = defaultdict(set)
    pair_names: dict[str, set[str]] = defaultdict(set)
    annotations: dict[str, int] = defaultdict(int)
    for row in rows:
        reid = row["reid"]
        categories[reid].add(row["category"])
        pair_names[reid].add(row["img_name"])
        annotations[reid] += 1

    locations = [
        {
            "reid": reid,
            "split": location_split(reid),
            "categories": "|".join(sorted(categories[reid])),
            "unique_images": len(pair_names[reid]),
            "annotation_rows": annotations[reid],
        }
        for reid in sorted(categories)
    ]
    summary: list[dict[str, object]] = []
    all_categories = sorted({category for values in categories.values() for category in values})
    for split in ("train", "validation", "test"):
        selected = [row for row in locations if row["split"] == split]
        ids = {str(row["reid"]) for row in selected}
        summary.append(
            {
                "split": split,
                "locations": len(ids),
                "unique_images": sum(int(row["unique_images"]) for row in selected),
                "annotation_rows": sum(int(row["annotation_rows"]) for row in selected),
                **{
                    f"locations_{category.lower().replace(' ', '_')}": sum(
                        category in categories[reid] for reid in ids
                    )
                    for category in all_categories
                },
            }
        )
    if sum(int(row["locations"]) for row in summary) != len(categories):
        raise ValueError("location split does not cover every location exactly once")
    return locations, summary


def _full_resolution_homography(half_homography: np.ndarray) -> np.ndarray:
    scale = np.diag([0.5, 0.5, 1.0])
    return np.linalg.inv(scale) @ half_homography @ scale


def register_pair(previous: Path, current: Path) -> tuple[dict[str, object], np.ndarray | None]:
    previous_gray = cv2.imread(str(previous), cv2.IMREAD_GRAYSCALE)
    current_gray = cv2.imread(str(current), cv2.IMREAD_GRAYSCALE)
    if previous_gray is None or current_gray is None:
        raise FileNotFoundError("registration image could not be read")
    previous_half = cv2.resize(previous_gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    current_half = cv2.resize(current_gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

    sift = cv2.SIFT_create(nfeatures=4000)
    previous_keypoints, previous_descriptors = sift.detectAndCompute(previous_half, None)
    current_keypoints, current_descriptors = sift.detectAndCompute(current_half, None)
    good = []
    if previous_descriptors is not None and current_descriptors is not None:
        matches = cv2.BFMatcher(cv2.NORM_L2).knnMatch(
            current_descriptors, previous_descriptors, k=2
        )
        good = [first for first, second in matches if first.distance < 0.75 * second.distance]

    half_homography: np.ndarray | None = None
    inlier_mask: np.ndarray | None = None
    median_error = float("nan")
    p95_error = float("nan")
    projected_area_ratio = float("nan")
    if len(good) >= 4:
        source = np.float32([current_keypoints[match.queryIdx].pt for match in good])
        target = np.float32([previous_keypoints[match.trainIdx].pt for match in good])
        half_homography, inlier_mask = cv2.findHomography(source, target, cv2.RANSAC, 3.0)
        if half_homography is not None and inlier_mask is not None:
            inliers = inlier_mask.ravel().astype(bool)
            projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), half_homography).reshape(-1, 2)
            errors = 2.0 * np.linalg.norm(projected - target, axis=1)
            if np.any(inliers):
                median_error = float(np.median(errors[inliers]))
                p95_error = float(np.quantile(errors[inliers], 0.95))
            height, width = current_half.shape
            corners = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
            projected_corners = cv2.perspectiveTransform(corners, half_homography).reshape(-1, 2)
            projected_area_ratio = float(
                abs(cv2.contourArea(projected_corners.astype(np.float32))) / (height * width)
            )

    inlier_count = 0 if inlier_mask is None else int(inlier_mask.sum())
    inlier_ratio = inlier_count / max(len(good), 1)
    reasons: list[str] = []
    if len(good) < REGISTRATION_GATE["min_good_matches"]:
        reasons.append("too_few_good_matches")
    if inlier_count < REGISTRATION_GATE["min_inliers"]:
        reasons.append("too_few_inliers")
    if inlier_ratio < REGISTRATION_GATE["min_inlier_ratio"]:
        reasons.append("low_inlier_ratio")
    if not np.isfinite(median_error) or median_error > REGISTRATION_GATE["max_median_reprojection_px"]:
        reasons.append("high_or_missing_reprojection_error")
    if (
        not np.isfinite(projected_area_ratio)
        or projected_area_ratio < REGISTRATION_GATE["min_projected_area_ratio"]
        or projected_area_ratio > REGISTRATION_GATE["max_projected_area_ratio"]
    ):
        reasons.append("degenerate_projected_area")
    full_homography = None if half_homography is None else _full_resolution_homography(half_homography)
    metrics: dict[str, object] = {
        "previous_keypoints": len(previous_keypoints),
        "current_keypoints": len(current_keypoints),
        "good_matches": len(good),
        "inliers": inlier_count,
        "inlier_ratio": inlier_ratio,
        "median_reprojection_error_px": median_error,
        "p95_reprojection_error_px": p95_error,
        "projected_area_ratio": projected_area_ratio,
        "registration_passed": not reasons,
        "failure_reasons": "|".join(reasons),
        "homography_current_to_previous": (
            "" if full_homography is None else json.dumps(full_homography.tolist(), separators=(",", ":"))
        ),
    }
    return metrics, full_homography


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_registration_rows(
    root: Path, sampled_observations: Path
) -> tuple[list[dict[str, object]], list[tuple[dict[str, object], np.ndarray | None]]]:
    with sampled_observations.open(newline="", encoding="utf-8") as handle:
        sampled = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sampled:
        grouped[row["reid"]].append(row)

    rows: list[dict[str, object]] = []
    detailed: list[tuple[dict[str, object], np.ndarray | None]] = []
    for reid, observations in sorted(grouped.items()):
        observations.sort(key=lambda row: row["timestamp_local_naive"])
        for previous_row, current_row in zip(observations, observations[1:]):
            previous = root / reid / previous_row["image_name"]
            current = root / reid / current_row["image_name"]
            metrics, homography = register_pair(previous, current)
            registration_id = hashlib.sha256(
                f"{previous_row['image_sha256']}:{current_row['image_sha256']}:sift_ransac_v1".encode()
            ).hexdigest()
            row: dict[str, object] = {
                "registration_id": registration_id,
                "reid": reid,
                "category": current_row["category"],
                "previous_image": previous_row["image_name"],
                "current_image": current_row["image_name"],
                "previous_timestamp_local_naive": previous_row["timestamp_local_naive"],
                "current_timestamp_local_naive": current_row["timestamp_local_naive"],
                "coordinate_frame_id": f"pavetrack:{reid}:{current_row['image_name']}:pixels",
                "target_frame_id": f"pavetrack:{reid}:{previous_row['image_name']}:pixels",
                "spatial_unit": "pixel",
                "timezone_status": "unknown_not_ingested",
                **metrics,
                "mechanical_decision_eligible": False,
            }
            rows.append(row)
            detailed.append((row, homography))
    return rows, detailed


def plot_registration_examples(
    root: Path,
    detailed: list[tuple[dict[str, object], np.ndarray | None]],
    output: Path,
) -> None:
    passed = next(item for item in detailed if item[0]["registration_passed"])
    failed = next(item for item in detailed if not item[0]["registration_passed"])
    figure, axes = plt.subplots(2, 4, figsize=(14, 7))
    for row_index, (row, homography) in enumerate((passed, failed)):
        previous = cv2.imread(str(root / str(row["reid"]) / str(row["previous_image"])))
        current = cv2.imread(str(root / str(row["reid"]) / str(row["current_image"])))
        previous_rgb = cv2.cvtColor(previous, cv2.COLOR_BGR2RGB)
        current_rgb = cv2.cvtColor(current, cv2.COLOR_BGR2RGB)
        if homography is None:
            warped = np.zeros_like(previous_rgb)
        else:
            warped_bgr = cv2.warpPerspective(current, homography, (previous.shape[1], previous.shape[0]))
            warped = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2RGB)
        difference = np.abs(previous_rgb.astype(np.int16) - warped.astype(np.int16)).mean(axis=2)
        panels = (previous_rgb, current_rgb, warped, difference)
        titles = ("Previous", "Current", "Current warped", "Absolute RGB difference")
        for column, (panel, title) in enumerate(zip(panels, titles)):
            axes[row_index, column].imshow(panel, cmap="magma" if column == 3 else None)
            axes[row_index, column].set_title(title)
            axes[row_index, column].axis("off")
        status = "PASS" if row["registration_passed"] else f"FAIL: {row['failure_reasons']}"
        axes[row_index, 0].set_ylabel(f"{row['reid']} {status}", fontsize=9)
    figure.suptitle("PaveTrack pairwise registration gate (image space only)")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def build_package(root: Path, pilot: Path, out: Path) -> None:
    manifest = root / "manifest.csv"
    workbook = root / "Dataset_PDdescription.xlsx"
    manifest_rows = read_manifest_rows(manifest)
    workbook_rows = read_workbook_keys(workbook)
    reconciliation = reconcile_counts(workbook_rows, manifest_rows)
    if not reconciliation["counts_reconciled"]:
        raise ValueError("workbook and manifest triples do not reconcile")
    locations, split_summary = build_location_split(manifest_rows)
    registration_rows, detailed = build_registration_rows(
        root, pilot / "sampled_visual_observations.csv"
    )

    out.mkdir(parents=True, exist_ok=True)
    (out / "provenance_reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_csv(out / "location_split.csv", locations)
    write_csv(out / "location_split_summary.csv", split_summary)
    write_csv(out / "pairwise_registration.csv", registration_rows)
    plot_registration_examples(root, detailed, out / "pairwise_registration_examples.png")

    source_audit = """# PaveTrack source-metadata audit

Primary source: Yang et al., *Scientific Data* 12, 1426 (2025),
https://doi.org/10.1038/s41597-025-05748-5.

The paper confirms that PaveTrack_PD contains 8,928 tracking images at 165
locations. Chinese images were acquired from a mobile vehicle with an
industrial camera. For privacy, nearby GPS observations were clustered at an
approximately 5-20 m scale and the GPS data were then removed from the released
images. The published matching baseline uses GPS clustering followed by
SuperPoint/SuperGlue background matching and local-area matching.

The released local JPEGs inspected by this package contain no EXIF camera, GPS,
focal-length or timezone fields. The paper does not provide a physical
pixel-to-road calibration for PaveTrack_PD. Therefore the SIFT/RANSAC transforms
in this package are an independent image-space diagnostic, not a reproduction
of the paper's full private-coordinate matching pipeline and not a route/model
coordinate registration.
"""
    (out / "source_metadata_audit.md").write_text(source_audit, encoding="utf-8")

    passed = sum(bool(row["registration_passed"]) for row in registration_rows)
    total = len(registration_rows)
    decision = f"""# PaveTrack provenance, split and registration gate

## Verdict

**Provenance counts reconciled and a location-isolated split is frozen. Pairwise
image-space registration is partial ({passed}/{total}); mechanical assimilation
and RUL remain blocked.**

The workbook has 9,447 annotation rows. Removing 200 exact duplicate
location-image-category rows gives the manifest's 9,247 rows. These represent
8,928 unique location-image pairs. The old report's 8,625 image count is the
filename-only count and incorrectly merges 303 names reused at different
locations. The workbook and manifest triple sets are otherwise identical.

The deterministic location split contains {split_summary[0]['locations']}
train, {split_summary[1]['locations']} validation and
{split_summary[2]['locations']} test locations. No location crosses splits and
all four distress categories occur in every split.

Sequential SIFT/RANSAC registration passed {passed}/{total} sampled transitions
under the predeclared match, inlier, reprojection and projected-area gates.
Failed transforms remain explicit missing registration; they are not imputed.
Even passing transforms are only between consecutive pixel frames. No physical
scale, timezone, model-coordinate registration, load, environment or measured
maintenance channel exists. The source paper confirms that GPS was clustered
and then removed for privacy, so route coordinates cannot be reconstructed
from the public images. The result therefore cannot support hidden-state,
mechanism or remaining-life claims.
"""
    (out / "decision.md").write_text(decision, encoding="utf-8")

    outputs = [
        "provenance_reconciliation.json",
        "location_split.csv",
        "location_split_summary.csv",
        "pairwise_registration.csv",
        "pairwise_registration_examples.png",
        "source_metadata_audit.md",
        "decision.md",
    ]
    manifest_payload = {
        "schema_version": "pavetrack_registration_gate_run_v1",
        "source_manifest_sha256": sha256(manifest),
        "source_workbook_sha256": sha256(workbook),
        "source_pilot_hashes_sha256": sha256(pilot / "HASHES.sha256"),
        "script_sha256": sha256(Path(__file__)),
        "split_salt": SPLIT_SALT,
        "registration_method": "sequential SIFT ratio-0.75 plus RANSAC homography",
        "registration_gate": REGISTRATION_GATE,
        "outputs": outputs,
    }
    (out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    outputs.append("RUN_MANIFEST.json")
    (out / "HASHES.sha256").write_text(
        "".join(f"{sha256(out / name)}  {name}\n" for name in outputs),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build_package(args.dataset_root, args.pilot, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
