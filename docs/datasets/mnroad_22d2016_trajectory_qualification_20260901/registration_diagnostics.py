#!/usr/bin/env python3
"""Reproduce the printed-page registration diagnostic for MnROAD Cell 22.

Input layout:
  <render-root>/<YYYY-MM-DD>/page-01.jpg ... page-10.jpg

The script tests only the stability of the printed coordinate carrier. It does
not recognise cracks or establish persistent crack identity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


EXACT_DATES = [
    "2017-03-20",
    "2018-03-14",
    "2018-04-27",
    "2018-08-23",
    "2019-03-22",
    "2019-04-16",
    "2019-10-23",
]


def read_gray(root: Path, date: str, page: int) -> np.ndarray:
    image_path = root / date / f"page-{page:02d}.jpg"
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(image_path)
    return image


def register(source: np.ndarray, target: np.ndarray) -> dict:
    orb = cv2.ORB_create(
        nfeatures=12000,
        scaleFactor=1.15,
        nlevels=8,
        fastThreshold=12,
    )
    kp_source, des_source = orb.detectAndCompute(source, None)
    kp_target, des_target = orb.detectAndCompute(target, None)
    if des_source is None or des_target is None:
        return {"status": "no_descriptors"}

    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
        des_source,
        des_target,
        k=2,
    )
    good = [first for first, second in pairs if first.distance < 0.72 * second.distance]
    if len(good) < 20:
        return {"status": "too_few_matches", "good_matches": len(good)}

    source_points = np.float32(
        [kp_source[match.queryIdx].pt for match in good]
    ).reshape(-1, 1, 2)
    target_points = np.float32(
        [kp_target[match.trainIdx].pt for match in good]
    ).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(
        source_points,
        target_points,
        cv2.RANSAC,
        3.0,
    )
    if homography is None or mask is None:
        return {"status": "homography_failed", "good_matches": len(good)}

    inliers = mask.ravel().astype(bool)
    projected = cv2.perspectiveTransform(source_points[inliers], homography)
    residual = np.linalg.norm(
        projected.reshape(-1, 2) - target_points[inliers].reshape(-1, 2),
        axis=1,
    )
    height, width = source.shape
    corners = np.float32(
        [[[0, 0]], [[width - 1, 0]], [[width - 1, height - 1]], [[0, height - 1]]]
    )
    warped_corners = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
    area_ratio = abs(cv2.contourArea(warped_corners.astype(np.float32))) / float(
        width * height
    )
    return {
        "status": "ok",
        "good_matches": len(good),
        "inliers": int(inliers.sum()),
        "inlier_ratio": float(inliers.mean()),
        "median_reprojection_px": float(np.median(residual)),
        "p95_reprojection_px": float(np.percentile(residual, 95)),
        "warped_page_area_ratio": float(area_ratio),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-root", required=True, type=Path)
    args = parser.parse_args()

    records = []
    for page in range(1, 11):
        for source_date, target_date in zip(EXACT_DATES[:-1], EXACT_DATES[1:]):
            result = register(
                read_gray(args.render_root, source_date, page),
                read_gray(args.render_root, target_date, page),
            )
            result.update(
                {
                    "page": page,
                    "source_date": source_date,
                    "target_date": target_date,
                }
            )
            records.append(result)

    passed = [record for record in records if record["status"] == "ok"]
    summary = {
        "pair_count": len(records),
        "solved_pairs": len(passed),
        "minimum_inliers": min(record["inliers"] for record in passed),
        "median_inliers": float(np.median([record["inliers"] for record in passed])),
        "median_inlier_ratio": float(
            np.median([record["inlier_ratio"] for record in passed])
        ),
        "median_reprojection_px": float(
            np.median([record["median_reprojection_px"] for record in passed])
        ),
        "maximum_pair_median_reprojection_px": max(
            record["median_reprojection_px"] for record in passed
        ),
        "maximum_pair_p95_reprojection_px": max(
            record["p95_reprojection_px"] for record in passed
        ),
        "warped_page_area_ratio_range": [
            min(record["warped_page_area_ratio"] for record in passed),
            max(record["warped_page_area_ratio"] for record in passed),
        ],
    }
    print(json.dumps({"summary": summary, "records": records}, indent=2))


if __name__ == "__main__":
    main()

