#!/usr/bin/env python3
"""Canonicalise the owner-confirmed v3 checklist and apply its frozen verdict rule."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
FIELDS = ("encloses_grid", "includes_0m_baseline", "excludes_summary", "obvious_nonphysical_range")
OWNER_CONFIRMED_TRUE_TO_YES = True
NO_CANDIDATE_ROW = ("19980407", "A")
STATUS = "EXPLORATORY_FRAME_CANDIDATE_REVIEW__NOT_QUALIFIED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def candidate_verdict(values: dict[str, str]) -> str:
    if all(values[field] == "YES" for field in FIELDS[:3]) and values[FIELDS[3]] == "NO":
        return "ACCEPT"
    if any(values[field] == "NO" for field in FIELDS[:3]) or values[FIELDS[3]] == "YES":
        return "REJECT"
    if all(values[field] in {"YES", "NO", "UNCERTAIN"} for field in FIELDS):
        return "UNCERTAIN"
    raise ValueError(f"invalid canonical checklist values: {values}")


def date_verdict(rows: list[dict[str, str]]) -> tuple[str, str]:
    accepted = [row for row in rows if row["candidate_verdict"] == "ACCEPT"]
    if len(accepted) == 0:
        return "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED", ""
    if len(accepted) == 1:
        return "ENGINEERING_FRAME_CANDIDATE", accepted[0]["candidate"]
    # The frozen submission contains no editable geometry fields. Two named
    # accepted sources are conservatively treated as geometrically distinct.
    return "AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED", ""


def canonical_row(row: dict[str, str]) -> dict[str, str]:
    date, candidate = row["date"], row["candidate"]
    if (date, candidate) == NO_CANDIDATE_ROW:
        if row["encloses_grid"].strip().lower() != "no grid" or any(row[field].strip() for field in FIELDS[1:]):
            raise ValueError("1998-A must be the owner-confirmed no-grid/no-candidate row")
        return row | {field: "" for field in FIELDS} | {"candidate_verdict": "NO_CANDIDATE"}
    values = {}
    for field in FIELDS:
        value = row[field].strip().upper()
        if value == "TRUE" and OWNER_CONFIRMED_TRUE_TO_YES:
            value = "YES"
        if value not in {"YES", "NO", "UNCERTAIN"}:
            raise ValueError(f"{date}-{candidate} has invalid {field}={row[field]!r}")
        values[field] = value
    return row | values | {"candidate_verdict": candidate_verdict(values)}


def draw_decisions(records: list[dict[str, str]], out: Path) -> None:
    canvas = np.full((130 + 120 * len(records), 1520, 3), 250, dtype=np.uint8)
    cv2.putText(canvas, "LTPP v3 frozen owner checklist: mechanical date decision", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, .82, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Engineering-page-canvas only: no crop, control, registration, residual, final gate, or 2-D model claim.", (24, 82), cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1, cv2.LINE_AA)
    for i, row in enumerate(records):
        y = 145 + i * 120
        colour = (0, 125, 0) if row["date_verdict"] == "ENGINEERING_FRAME_CANDIDATE" else (0, 0, 205)
        cv2.putText(canvas, row["date"], (24, y), cv2.FONT_HERSHEY_SIMPLEX, .72, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"A={row['a_verdict']}   B={row['b_verdict']}", (230, y), cv2.FONT_HERSHEY_SIMPLEX, .58, (20, 20, 20), 2, cv2.LINE_AA)
        text = row["date_verdict"] + (f" ({row['selected_candidate']})" if row["selected_candidate"] else "")
        cv2.putText(canvas, text, (24, y + 48), cv2.FONT_HERSHEY_SIMPLEX, .58, colour, 2, cv2.LINE_AA)
    cv2.imwrite(str(out / "eight_date_frozen_checklist_decision.png"), canvas)


def run(submission: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite {output}")
    with submission.open(newline="", encoding="utf-8") as handle:
        raw = [row for row in csv.DictReader(handle) if row.get("date")]
    expected = {(date, candidate) for date in DATES for candidate in ("A", "B")}
    if {(row["date"], row["candidate"]) for row in raw} != expected:
        raise ValueError("submitted rows must contain exactly A/B for all eight dates")
    canonical = [canonical_row(row) for row in raw]
    output.mkdir(parents=True)
    with (output / "canonical_owner_submission.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(canonical[0])
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(canonical)
    decisions = []
    for date in DATES:
        rows = [row for row in canonical if row["date"] == date]
        verdict, selected = date_verdict(rows)
        decisions.append({"date": date, "a_verdict": next(row["candidate_verdict"] for row in rows if row["candidate"] == "A"), "b_verdict": next(row["candidate_verdict"] for row in rows if row["candidate"] == "B"), "date_verdict": verdict, "selected_candidate": selected})
    with (output / "per_date_decisions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(decisions[0])); writer.writeheader(); writer.writerows(decisions)
    result = {"status": STATUS, "owner_confirmation": {"TRUE_to_YES": True, "19980407_A": "NO_CANDIDATE"}, "records": decisions, "prohibited_claims": ["crop", "controls", "registration", "final_gate", "2d_model"]}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "receipt.sha256").write_text(f"{sha256(submission)}  submitted/manual_checklist.csv\n{sha256(Path(__file__))}  script/{Path(__file__).name}\n", encoding="utf-8")
    (output / "decision.md").write_text(f"# Frame candidate review MVP v3 owner decision\n\n`{STATUS}`\n\nThe owner explicitly confirmed only `TRUE -> YES` and `19980407-A -> NO_CANDIDATE`. The frozen checklist rule yields four engineering-page-canvas candidates and four fail-closed dates. This is not registration evidence.\n", encoding="utf-8")
    draw_decisions(decisions, output)
    manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.submission.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
