#!/usr/bin/env python3
"""Evaluate the frozen eight exposed development points; never run a final gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np


DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
POST1991_DATES = DATES[1:]
DEVELOPMENT_IDS = ("G[5,0]", "G[5,5]", "G[0,2]", "G[0,3]", "G[10,2]", "G[10,3]", "G[3,1]", "G[7,4]")
EXPECTED_OWNER_SHA256 = "3f86fc7c0d28d578387d5e8d99295faf8e9bc4d45e437f4d1e181940e96a4803"
ID_PATTERN = re.compile(r"G\[(\d+),(\d+)\]")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical_coordinate(candidate: str) -> tuple[float, float]:
    match = ID_PATTERN.fullmatch(candidate)
    if not match:
        raise ValueError(f"invalid candidate: {candidate}")
    i, j = map(int, match.groups())
    return 15.24 * i / 10.0, float(j)


def source_to_physical_matrix(points: list[list[float]]) -> np.ndarray:
    source = np.asarray(points, dtype=np.float32)
    target = np.asarray(((0, 5), (15.24, 5), (15.24, 0), (0, 0)), dtype=np.float32)
    return cv2.getPerspectiveTransform(source, target)


def transform_point(matrix: np.ndarray, point: list[float]) -> tuple[float, float]:
    value = cv2.perspectiveTransform(np.asarray([[point]], dtype=np.float32), matrix)[0, 0]
    return float(value[0]), float(value[1])


def metrics(errors: list[float]) -> dict[str, float]:
    values = np.asarray(errors, dtype=float)
    return {
        "median_error_m": float(np.median(values)),
        "p95_error_m": float(np.quantile(values, 0.95, method="linear")),
        "maximum_error_m": float(np.max(values)),
    }


def write_sidecar(path: Path, date: str) -> None:
    path.with_suffix(".md").write_text(
        f"# {date} development8 error overlay\n\n"
        "## Question\n\nHow far are the user-reviewed printed-grid centres from the four-corner projective suggestions?\n\n"
        "## Provenance and encoding\n\nThe background is the development8 pilot crop. Green circles are frozen projective suggestions; magenta circles are user-reviewed points. Yellow arrows show the suggestion-to-review displacement amplified five times for visibility, while labels report the unamplified physical error in metres.\n\n"
        "## Limitation and claim boundary\n\nThese are exposed user-reviewed development points. They are not independent Tier B/final controls and cannot qualify registration or authorize a 2-D model.\n",
        encoding="utf-8",
    )


def evaluate(owner_packet: Path, pilot_root: Path, output: Path, dates: tuple[str, ...] = DATES) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    owner_file = owner_packet / "owner_corners.json"
    if sha256(owner_file) != EXPECTED_OWNER_SHA256:
        raise ValueError("unexpected owner-corner receipt")
    owner = json.loads(owner_file.read_text(encoding="utf-8"))
    owner_records = {row["survey_date"]: row for row in owner["records"]}
    output.mkdir(parents=True)
    overlays = output / "error_overlays"
    overlays.mkdir()
    point_rows = []
    date_rows = []
    complete_dates = 0
    for date in dates:
        record = json.loads((pilot_root / "records" / f"{date}.json").read_text(encoding="utf-8"))
        if record.get("task_profile") != "development8" or tuple(record["tasks"]) != DEVELOPMENT_IDS:
            raise ValueError(f"unexpected development task inventory: {date}")
        missing = sum(record["tasks"][candidate]["status"] != "usable" for candidate in DEVELOPMENT_IDS)
        matrix = source_to_physical_matrix(owner_records[date]["points_source_px"])
        errors = []
        image = cv2.imread(str(pilot_root / "images" / f"{date}.png"), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read pilot image: {date}")
        origin = record["crop_source_px"]
        for candidate in DEVELOPMENT_IDS:
            task = record["tasks"][candidate]
            row = {"survey_date": date, "candidate_id": candidate, "status": task["status"]}
            if task["status"] == "usable":
                click_crop = task["reviewed_crop_px"]
                click_source = [click_crop[0] + origin["left"], click_crop[1] + origin["top"]]
                observed = transform_point(matrix, click_source)
                expected = physical_coordinate(candidate)
                error = float(np.linalg.norm(np.asarray(observed) - np.asarray(expected)))
                errors.append(error)
                row.update({
                    "click_source_x_px": click_source[0], "click_source_y_px": click_source[1],
                    "observed_x_m": observed[0], "observed_y_m": observed[1],
                    "expected_x_m": expected[0], "expected_y_m": expected[1], "error_m": error,
                })
                suggestion = np.asarray(task["suggested_crop_px"], dtype=float)
                reviewed = np.asarray(click_crop, dtype=float)
                end = suggestion + 5.0 * (reviewed - suggestion)
                s = tuple(np.rint(suggestion).astype(int)); r = tuple(np.rint(reviewed).astype(int)); e = tuple(np.rint(end).astype(int))
                cv2.circle(image, s, 10, (0, 170, 60), 3, cv2.LINE_AA)
                cv2.circle(image, r, 8, (180, 30, 230), 3, cv2.LINE_AA)
                cv2.arrowedLine(image, s, e, (0, 190, 255), 3, cv2.LINE_AA, tipLength=0.18)
                cv2.putText(image, f"{candidate} {error:.3f}m", (r[0] + 10, r[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 3, cv2.LINE_AA)
                cv2.putText(image, f"{candidate} {error:.3f}m", (r[0] + 10, r[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            point_rows.append(row)
        date_metric = metrics(errors) if missing == 0 else {"median_error_m": None, "p95_error_m": None, "maximum_error_m": None}
        if missing == 0:
            complete_dates += 1
        date_rows.append({"survey_date": date, "missing_control_count": missing, **date_metric,
                          "status": "DEVELOPMENT8_COMPLETE" if missing == 0 else "DEVELOPMENT8_INCOMPLETE"})
        overlay = overlays / f"{date}.png"
        if not cv2.imwrite(str(overlay), image):
            raise ValueError(f"cannot write overlay: {date}")
        write_sidecar(overlay, date)
    fieldnames = ["survey_date", "candidate_id", "status", "click_source_x_px", "click_source_y_px", "observed_x_m", "observed_y_m", "expected_x_m", "expected_y_m", "error_m"]
    with (output / "per_point_errors.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore"); writer.writeheader(); writer.writerows(point_rows)
    with (output / "per_date_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=date_rows[0].keys()); writer.writeheader(); writer.writerows(date_rows)
    result = {
        "status": "EXPLORATORY_7_DATE_DEVELOPMENT8_EVALUATED__NOT_QUALIFIED" if dates == POST1991_DATES else "EXPLORATORY_DEVELOPMENT8_EVALUATED__NOT_QUALIFIED",
        "complete_dates": complete_dates,
        "total_dates": len(dates),
        "final_controls_used": False,
        "final_gate_run": False,
        "dates": date_rows,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (output / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(output)}\n" for path in files), encoding="ascii")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-packet", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date-profile", choices=("all8", "post1991_7"), default="all8")
    args = parser.parse_args()
    dates = DATES if args.date_profile == "all8" else POST1991_DATES
    print(json.dumps(evaluate(args.owner_packet.resolve(), args.pilot_root.resolve(), args.output.resolve(), dates)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
