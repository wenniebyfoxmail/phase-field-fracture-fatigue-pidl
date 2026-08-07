#!/usr/bin/env python3
"""Compare trend direction of pilot proxy fields and full-section MON_DIS indices."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


PRIMARY_DATES = (
    "1991-06-10",
    "1995-10-24",
    "1997-02-28",
    "1998-04-07",
    "2001-09-13",
    "2003-05-14",
    "2007-11-06",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def negative_count(values: np.ndarray) -> int:
    return int(np.sum(np.diff(values.astype(float)) < 0.0))


def paired_diagnostic(left: np.ndarray, right: np.ndarray) -> dict:
    correlation = spearmanr(left, right)
    left_direction = np.sign(np.diff(left.astype(float)))
    right_direction = np.sign(np.diff(right.astype(float)))
    return {
        "spearman_rho": float(correlation.statistic),
        "spearman_pvalue_descriptive_only": float(correlation.pvalue),
        "direction_agreement_count": int(np.sum(left_direction == right_direction)),
        "transition_count": int(len(left_direction)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields", type=Path, required=True)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with np.load(args.fields, allow_pickle=False) as source:
        dates = [datetime.strptime(str(value), "%Y%m%d").date().isoformat() for value in source["survey_dates"]]
        indices = [dates.index(value) for value in PRIMARY_DATES]
        pilot = pd.DataFrame(
            {
                "survey_date": PRIMARY_DATES,
                "pilot_line_mean": source["line_damage"][indices].mean(axis=(1, 2)),
                "pilot_area_mean": source["area_damage"][indices].mean(axis=(1, 2)),
                "pilot_combined_mean": source["combined_damage"][indices].mean(axis=(1, 2)),
            }
        )

    official = pd.read_csv(args.official)
    official["survey_date"] = pd.to_datetime(official["SURVEY_DATE"]).dt.date.astype(str)
    official = official.rename(
        columns={
            "HPMS16_CRACKING_PERCENT_AC": "official_hpms_percent",
            "MEPDG_CRACKING_PERCENT_AC": "official_mepdg_percent",
            "MEPDG_TRANS_CRACK_LENGTH_AC": "official_trans_length_norm",
            "MEPDG_LONG_CRACK_LENGTH_AC": "official_long_length_norm",
        }
    )
    official = official[
        [
            "survey_date",
            "official_hpms_percent",
            "official_mepdg_percent",
            "official_trans_length_norm",
            "official_long_length_norm",
        ]
    ]
    joined = pilot.merge(official, on="survey_date", how="left", validate="one_to_one")
    if joined.isna().any().any() or len(joined) != 7:
        raise SystemExit("seven-date pilot/official join is incomplete")
    joined["official_total_line_length_norm"] = (
        joined["official_trans_length_norm"] + joined["official_long_length_norm"]
    )

    pilot_columns = ["pilot_line_mean", "pilot_area_mean", "pilot_combined_mean"]
    official_columns = [
        "official_hpms_percent",
        "official_mepdg_percent",
        "official_trans_length_norm",
        "official_long_length_norm",
        "official_total_line_length_norm",
    ]
    negative_transitions = {
        column: negative_count(joined[column].to_numpy(float))
        for column in pilot_columns + official_columns
    }
    paired = {
        "combined_vs_hpms": paired_diagnostic(
            joined["pilot_combined_mean"].to_numpy(float),
            joined["official_hpms_percent"].to_numpy(float),
        ),
        "area_vs_mepdg": paired_diagnostic(
            joined["pilot_area_mean"].to_numpy(float),
            joined["official_mepdg_percent"].to_numpy(float),
        ),
        "line_vs_official_total_line": paired_diagnostic(
            joined["pilot_line_mean"].to_numpy(float),
            joined["official_total_line_length_norm"].to_numpy(float),
        ),
    }
    if any(negative_transitions[column] > 0 for column in official_columns):
        decision = "OFFICIAL_SECTION_TRENDS_ALSO_NONMONOTONE"
    elif any(negative_transitions[column] > 0 for column in pilot_columns):
        decision = "PILOT_ONLY_NONMONOTONICITY"
    else:
        decision = "BOTH_OBSERVATION_SUMMARIES_MONOTONE"

    args.output_dir.mkdir(parents=True, exist_ok=False)
    joined_path = args.output_dir / "joined_trends.csv"
    joined.to_csv(joined_path, index=False)
    payload = {
        "protocol_id": "ltpp_06_1253_mon_dis_trend_diagnostic_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "descriptive_post_pilot_full_section_reference",
        "decision": decision,
        "negative_adjacent_transition_counts": negative_transitions,
        "paired_diagnostics": paired,
        "boundary": (
            "The official series represents 500 ft and the pilot represents 0-50 ft. "
            "Non-monotonicity is an observation-property result, not evidence of physical healing."
        ),
        "inputs": {
            "fields": str(args.fields.resolve()),
            "fields_sha256": sha256(args.fields),
            "official": str(args.official.resolve()),
            "official_sha256": sha256(args.official),
        },
        "outputs": {
            "joined_trends": str(joined_path.resolve()),
            "joined_trends_sha256": sha256(joined_path),
        },
    }
    result_path = args.output_dir / "trend_diagnostic_result.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "negative_transitions": negative_transitions, "paired": paired}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
