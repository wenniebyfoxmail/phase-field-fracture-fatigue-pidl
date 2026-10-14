#!/usr/bin/env python3
"""Inventory existing D01 outputs only; never annotate, fit, or score forecasts."""
import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Fresh output only; preserve every previous diagnostic and source file.
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = {
        "profiles": args.archive_root / "S03-E015-D01/runs/S03-E015-D01-R001/profile_measurements.csv",
        "forecasts": args.archive_root / "S03-E015-D01/runs/S03-E015-D01-R001/individual_forecasts.csv",
        "ai_unique": args.archive_root / "S03-E017-D01/runs/S03-E017-D01-R001/unique_task_comparison.csv",
    }
    profiles, forecasts, ai = (read_csv(inputs[key]) for key in inputs)
    states = defaultdict(list)
    labels = defaultdict(list)
    for row in profiles:
        if row["role"] == "crack":
            states[(int(row["beam"]), float(row["load_kN"]))].append(row)
    for row in ai:
        labels[(int(row["beam"]), float(row["nominal_stage_kN"]))].append(row)
    pairs = sorted({(int(r["beam"]), float(r["origin_kN"]), float(r["target_kN"])) for r in forecasts})
    assert len(states) == 14 and sum(map(len, states.values())) == 168
    assert len(ai) == 24 and len(forecasts) == 288 and len(pairs) == 8
    assert len({(r["beam"], r["stage_index"], r["transect_id"]) for r in ai}) == 24
    assert set(labels) <= set(states)
    rows = []
    for (beam, load), measured in sorted(states.items()):
        stages = {int(r["stage_index"]) for r in measured}
        source = {r["source"] for r in measured}
        assert len(stages) == len(source) == 1
        assert {int(r["transect_id"]) for r in measured} == set(range(1, 13))
        annotated = labels[(beam, load)]
        assert all(int(r["stage_index"]) in stages for r in annotated)
        visible = sum(r["quality"] == "visible" for r in annotated)
        uncertain = sum(r["quality"] == "uncertain" for r in annotated)
        assert visible + uncertain == len(annotated)
        row = dict(beam=beam, stage_index=next(iter(stages)), nominal_stage_kN=load,
                   prediction_target=any(b == beam and t == load for b, o, t in pairs),
                   measured_transects=len(measured), valid_measurements=sum(r["valid"] == "True" for r in measured),
                   ai_visible_crops=visible, ai_uncertain_crops=uncertain,
                   ai_not_annotated_transects=12-len(annotated),
                   qualified_same_definition_reference_count=0, human_reference_status="pending",
                   measurement_definition_id="E015-five-line-median-half-depth",
                   ai_definition_id="E017-central-row-visible-dark-boundary", source=next(iter(source)))
        rows.append(row)
    missing = [dict(beam=r["beam"], nominal_stage_kN=r["nominal_stage_kN"]) for r in rows
               if r["prediction_target"] and not (r["ai_visible_crops"] + r["ai_uncertain_crops"])]
    assert len(missing) == 5
    with (args.output / "stage_reference_coverage.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(audit_id="S03-REFCOV-20261014-R001", stage_count=len(rows),
                   measured_profile_count=168, prediction_pair_count=len(pairs),
                   prediction_pair_transects=96, ai_unique_count=len(ai),
                   ai_visible_count=sum(r["ai_visible_crops"] for r in rows),
                   ai_uncertain_count=sum(r["ai_uncertain_crops"] for r in rows),
                   missing_ai_target_stages=missing,
                   reference_scope="No qualified same-definition reference in the inspected E015/E017 records; human preparation remains pending.",
                   new_annotations=0, forecast_scores_recomputed=False, pairs=pairs)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    counts = np.array([[r["valid_measurements"], r["ai_visible_crops"],
                        r["ai_uncertain_crops"], r["ai_not_annotated_transects"], 0] for r in rows])
    fig, ax = plt.subplots(figsize=(10, 8.5))
    ax.imshow(counts, cmap="Blues", vmin=0, vmax=12, aspect="auto")
    for i, row in enumerate(counts):
        for j, value in enumerate(row):
            ax.text(j, i, f"{value}/12", ha="center", va="center", color="white" if value > 7 else "#24333d", fontsize=10)
    ax.set_xticks(range(5), ["Algorithm\nmeasurable", "AI visible\n(cross-definition)", "AI uncertain\n(retained)", "Not AI\nannotated", "Qualified same-\ndefinition reference"])
    ax.set_yticks(range(len(rows)), [f"Beam {r['beam']} | {r['nominal_stage_kN']:g} kN" + (" *" if r['prediction_target'] else "") for r in rows])
    for split in (3.5, 9.5):
        ax.axhline(split, color="#9aa8af", linewidth=1.5)
    ax.set_title("D01: measurement coverage is not reference coverage", fontsize=15, pad=18)
    fig.text(.04, .065, "* Next-stage prediction target; all 14 fixed-camera stages, three DEVELOPMENT beams.\n"
             "Counts are out of 12 frozen transects per stage. AI uncertain and unannotated are different.\n"
             "Reference zeros mean not yet qualified, NOT zero error. No forecast rescoring or new labels.", fontsize=10)
    fig.text(.04, .018, "Sources: E015-D01-R001 / E017-D01-R001 | coverage audit S03-REFCOV-20261014-R001", fontsize=9)
    fig.subplots_adjust(left=.23, right=.98, top=.91, bottom=.16)
    for suffix in ("png", "pdf"):
        fig.savefig(args.output / f"stage_reference_coverage.{suffix}", dpi=180)
    plt.close(fig)
    sources = "\n".join(f"- {key}: `{path}`" for key, path in inputs.items())
    (args.output / "stage_reference_coverage.md").write_text(f"""# How to read stage_reference_coverage

## Figure question

Where are current measurements, AI visual checks and qualified same-definition references available for D01 next-stage evaluation?

## Data provenance

{sources}
- Script: `scripts/audit_d01_reference_coverage.py`; inventory only, no private answer key read.
- Every fixed-camera stage and all 12 frozen transects are included. No interpolation or score recomputation.

## Visual grammar and panel guide

One panel: rows identify beam and nominal stage in kN; * marks the eight existing forecast targets. Columns count valid algorithm measurements, visible AI crops, uncertain AI crops, unannotated transects, and qualified references. Every cell uses the same denominator of 12 and colour range 0–12. The two AI-status columns plus the unannotated column sum to 12. The algorithm and reference columns are separate inventories, not alternative partitions.

## Key numerical takeaway

14 stages, 168 measured crack profiles, eight prediction pairs / 96 pair-transects. Existing AI checks cover 24 different crops: 16 visible, eight uncertain. Five target stages have no AI crop labels. Qualified same-definition reference count remains zero in these owning records; human annotation preparation is pending. This is a descriptive inventory, not a model acceptance test.

## Limitations and claim boundary

AI central-row visual boundaries differ from the five-line-median half-depth observable; visible AI labels therefore do not fill the last column. Zero reference means unavailable/unqualified, not zero discrepancy. These are selected development beams, not a new holdout. Counts do not establish physical accuracy, independent repeatability, or future prediction performance. No new annotation was performed and no human preparation was modified.

## Related assets

- Exact table: `stage_reference_coverage.csv`; summary: `summary.json`.
- Decision: `docs/research/S03/reference_interface_draft_20261014.md`.
- Formats: same-stem PNG and PDF.
""")
    repo = Path(__file__).resolve().parents[1]
    receipt = dict(audit_id=summary["audit_id"], completed_utc=datetime.now(timezone.utc).isoformat(),
                   code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                   script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   git_status=subprocess.check_output(["git", "status", "--short"], cwd=repo, text=True),
                   scope="Existing-output coverage inventory, not a new claim-bearing experiment",
                   inputs={k: dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k, p in inputs.items()})
    (args.output / "audit_receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
