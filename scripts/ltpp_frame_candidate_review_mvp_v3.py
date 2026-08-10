#!/usr/bin/env python3
"""Render immutable A/B frame candidates for frozen human engineering review."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
SOLID_ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_eight_date_solid_outer_boundary_inventory_v4_20260810")
LATTICE_ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_lattice_envelope_frame_range_mvp_20260810")
STATUS = "EXPLORATORY_FRAME_CANDIDATE_REVIEW__PENDING_FROZEN_HUMAN_CHECKLIST__NOT_QUALIFIED"
FIELDS = ("encloses_grid", "includes_0m_baseline", "excludes_summary", "obvious_nonphysical_range")
ALLOWED = {"YES", "NO", "UNCERTAIN"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8"
    )


def candidate_verdict(values: dict[str, str]) -> str:
    if set(values) != set(FIELDS) or any(value not in ALLOWED for value in values.values()):
        raise ValueError("checklist must contain exactly the four frozen YES/NO/UNCERTAIN fields")
    if all(values[field] == "YES" for field in FIELDS[:3]) and values[FIELDS[3]] == "NO":
        return "ACCEPT"
    if any(values[field] == "NO" for field in FIELDS[:3]) or values[FIELDS[3]] == "YES":
        return "REJECT"
    return "UNCERTAIN"


def date_verdict(a: str, b: str, same_geometry: bool) -> str:
    accepted = int(a == "ACCEPT") + int(b == "ACCEPT")
    if accepted == 0:
        return "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"
    if accepted == 1 or same_geometry:
        return "ENGINEERING_FRAME_CANDIDATE"
    return "AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED"


def fit(image: np.ndarray, width: int, height: int) -> np.ndarray:
    scale = min(width / image.shape[1], height / image.shape[0])
    scaled = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    canvas = np.full((height, width, 3), 245, dtype=np.uint8)
    y, x = (height - scaled.shape[0]) // 2, (width - scaled.shape[1]) // 2
    canvas[y:y + scaled.shape[0], x:x + scaled.shape[1]] = scaled
    return canvas


def panel(date: str, a_path: Path | None, b_path: Path | None) -> np.ndarray:
    width, height = 1240, 760
    header = np.full((100, 2 * width + 16, 3), 250, dtype=np.uint8)
    cv2.putText(header, f"{date}: frozen A/B frame-candidate review", (18, 33), cv2.FONT_HERSHEY_SIMPLEX, .86, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "A=solid-profile history; B=lattice-envelope history. Review only; no crop, control, transform, or registration claim.", (18, 69), cv2.FONT_HERSHEY_SIMPLEX, .49, (20, 20, 20), 1, cv2.LINE_AA)
    def load_or_missing(path: Path | None, label: str) -> np.ndarray:
        if path is not None:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is not None:
                return fit(image, width, height)
        out = np.full((height, width, 3), 245, dtype=np.uint8)
        cv2.putText(out, f"{label}: NO_CANDIDATE", (80, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (40, 40, 210), 3, cv2.LINE_AA)
        return out
    a, b = load_or_missing(a_path, "A solid-profile"), load_or_missing(b_path, "B lattice-envelope")
    cv2.putText(a, "A", (24, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 140, 255), 4, cv2.LINE_AA)
    cv2.putText(b, "B", (24, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (210, 0, 170), 4, cv2.LINE_AA)
    return np.vstack((header, np.hstack((a, np.full((height, 16, 3), 210, dtype=np.uint8), b))))


def synthetic_cases() -> list[tuple[str, dict[str, str], dict[str, str], bool, str]]:
    y = {field: "YES" for field in FIELDS[:3]} | {FIELDS[3]: "NO"}
    wrong_summary = y | {"excludes_summary": "NO"}
    missing_base = y | {"includes_0m_baseline": "NO"}
    uncertain = y | {"encloses_grid": "UNCERTAIN"}
    return [
        ("only_a_correct", y, wrong_summary, False, "ENGINEERING_FRAME_CANDIDATE"),
        ("only_b_correct", wrong_summary, y, False, "ENGINEERING_FRAME_CANDIDATE"),
        ("both_wrong", wrong_summary, missing_base, False, "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"),
        ("one_missing_candidate", y, uncertain, False, "ENGINEERING_FRAME_CANDIDATE"),
        ("summary_table_included", wrong_summary, wrong_summary, False, "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"),
        ("omitted_0m_baseline", missing_base, missing_base, False, "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"),
        ("wrong_left_edge", y | {"obvious_nonphysical_range": "YES"}, missing_base, False, "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"),
        ("different_double_accept", y, y, False, "AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED"),
        ("identical_double_accept", y, y, True, "ENGINEERING_FRAME_CANDIDATE"),
    ]


def run_synthetic(out: Path) -> dict:
    if out.exists():
        raise ValueError(f"refusing to overwrite {out}")
    out.mkdir(parents=True)
    rows, cards = [], []
    for name, a_values, b_values, same, expected in synthetic_cases():
        a, b = candidate_verdict(a_values), candidate_verdict(b_values)
        observed = date_verdict(a, b, same)
        rows.append({"case": name, "a_verdict": a, "b_verdict": b, "same_geometry": same, "expected": expected, "observed": observed, "pass": observed == expected})
        card = np.full((250, 720, 3), 250, dtype=np.uint8)
        cv2.putText(card, name, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, .7, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.putText(card, f"A={a}  B={b}  same_geometry={same}", (20, 93), cv2.FONT_HERSHEY_SIMPLEX, .56, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.putText(card, observed, (20, 155), cv2.FONT_HERSHEY_SIMPLEX, .52, (0, 120, 0) if observed == expected else (0, 0, 210), 2, cv2.LINE_AA)
        cv2.putText(card, "PASS" if observed == expected else "FAIL", (20, 215), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 120, 0) if observed == expected else (0, 0, 210), 2, cv2.LINE_AA)
        cards.append(card)
    cols = 3
    overview = np.full((250 * ((len(cards) + cols - 1) // cols), 720 * cols, 3), 230, dtype=np.uint8)
    for index, card in enumerate(cards):
        row, col = divmod(index, cols)
        overview[row * 250:(row + 1) * 250, col * 720:(col + 1) * 720] = card
    cv2.imwrite(str(out / "synthetic_checklist_mapping_overview.png"), overview)
    result = {"status": "SYNTHETIC_SUITE_PASSED" if all(row["pass"] for row in rows) else "SYNTHETIC_SUITE_FAILED", "records": rows}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_manifest(out)
    return result


def review_paths(date: str) -> tuple[Path | None, Path | None]:
    a = SOLID_ROOT / f"{date}_solid_outer_boundary_review.png"
    b = LATTICE_ROOT / f"{date}_lattice_envelope_frame_review.png"
    return (a if a.exists() else None, b if b.exists() else None)


def run_review(out: Path) -> dict:
    if out.exists():
        raise ValueError(f"refusing to overwrite {out}")
    out.mkdir(parents=True)
    records, pages, receipt = [], [], []
    for date in DATES:
        a, b = review_paths(date)
        image = panel(date, a, b)
        path = out / f"{date}_ab_frame_review.png"
        cv2.imwrite(str(path), image)
        pages.append(image)
        records.extend({"date": date, "candidate": candidate, "source_exists": bool(source), **{field: "" for field in FIELDS}, "candidate_verdict": "PENDING_FROZEN_HUMAN_CHECKLIST"} for candidate, source in (("A", a), ("B", b)))
        for label, source in (("A", a), ("B", b)):
            if source:
                receipt.append(f"{sha256(source)}  {label}/{source.name}\n")
    thumb_w, thumb_h = 1240, 390
    overview = np.full((thumb_h * 4, thumb_w * 2, 3), 230, dtype=np.uint8)
    for index, image in enumerate(pages):
        row, col = divmod(index, 2)
        overview[row * thumb_h:(row + 1) * thumb_h, col * thumb_w:(col + 1) * thumb_w] = fit(image, thumb_w, thumb_h)
    cv2.imwrite(str(out / "eight_date_ab_frame_review_overview.png"), overview)
    with (out / "manual_checklist.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    result = {"status": STATUS, "date_count": len(DATES), "records": records, "prohibited_claims": ["candidate_modification", "crop", "controls", "registration", "final_gate", "2d_model"]}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "source_receipt.sha256").write_text("".join(receipt), encoding="utf-8")
    (out / "decision.md").write_text(f"# Frame candidate review MVP v3\n\n`{STATUS}`\n\nRendered immutable A/B candidates. Human checklist is pending; no page canvas is accepted yet.\n", encoding="utf-8")
    write_manifest(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic-output", type=Path)
    group.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_synthetic(args.synthetic_output.resolve()) if args.synthetic_output else run_review(args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "SYNTHETIC_SUITE_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
