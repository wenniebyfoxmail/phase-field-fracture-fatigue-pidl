#!/usr/bin/env python3
"""Audit the minimal climate-free library on existing frozen weak systems."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from run_ltpp_06_1253_reduced_library_identifiability import (
    BASELINE,
    normalized_condition,
    sha256,
    vif_values,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result_path = args.result_root / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("protocol_id") != "ltpp_06_1253_single_annotator_freeze_select_v1":
        raise SystemExit("unexpected frozen v1 result")
    systems = sorted(args.result_root.glob("weak_system__*.csv"))
    if len(systems) != 48:
        raise SystemExit(f"expected 48 frozen weak systems, found {len(systems)}")

    rows = []
    vif_rows = []
    names = list(BASELINE)
    for path in systems:
        frame = pd.read_csv(path)
        matrix = frame[[f"theta__{name}" for name in names]].to_numpy(float)
        rank, condition = normalized_condition(matrix)
        rows.append(
            {
                "system": path.name,
                "rank": rank,
                "candidate_count": len(names),
                "full_rank": rank == len(names),
                "normalized_condition_number": condition,
            }
        )
        for name, value in vif_values(matrix, names).items():
            if name != "constant":
                vif_rows.append({"system": path.name, "term": name, "vif": value})

    systems_frame = pd.DataFrame(rows)
    vif_frame = pd.DataFrame(vif_rows)
    term_summary = (
        vif_frame.groupby("term", as_index=False)
        .agg(
            median_vif=("vif", "median"),
            p90_vif=("vif", lambda values: float(np.quantile(values, 0.90))),
        )
    )
    metrics = {
        "full_rank_system_fraction": float(systems_frame["full_rank"].mean()),
        "median_normalized_condition_number": float(
            systems_frame["normalized_condition_number"].median()
        ),
        "p90_normalized_condition_number": float(
            systems_frame["normalized_condition_number"].quantile(0.90)
        ),
        "maximum_term_median_vif": float(term_summary["median_vif"].max()),
        "maximum_term_p90_vif": float(term_summary["p90_vif"].max()),
    }
    checks = {
        "full_rank_fraction_ge_0p90": metrics["full_rank_system_fraction"] >= 0.90,
        "median_condition_le_1e3": metrics["median_normalized_condition_number"] <= 1e3,
        "p90_condition_le_1e4": metrics["p90_normalized_condition_number"] <= 1e4,
        "all_variable_term_median_vif_le_20": metrics["maximum_term_median_vif"] <= 20,
        "all_variable_term_p90_vif_le_50": metrics["maximum_term_p90_vif"] <= 50,
    }
    decision = (
        "READY_FOR_CLIMATE_FREE_EXPLORATORY_SELECTION"
        if all(checks.values())
        else "CLIMATE_FREE_BASELINE_NOT_IDENTIFIABLE"
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    systems_path = args.output_dir / "system_conditioning.csv"
    vif_path = args.output_dir / "term_vif.csv"
    systems_frame.to_csv(systems_path, index=False)
    term_summary.to_csv(vif_path, index=False)
    payload = {
        "protocol_id": "ltpp_06_1253_climate_free_baseline_gate_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "post_v1_single_annotator_exploratory_gate",
        "candidate_library": names,
        "decision": decision,
        "checks": checks,
        "metrics": metrics,
        "boundary": (
            "Climate exclusion is a scope decision, not evidence that climate is irrelevant. "
            "A pass authorizes only exploratory climate-free stability selection."
        ),
        "inputs": {
            "frozen_v1_result": str(result_path.resolve()),
            "frozen_v1_result_sha256": sha256(result_path),
            "weak_system_count": len(systems),
        },
        "outputs": {
            "system_conditioning": str(systems_path.resolve()),
            "system_conditioning_sha256": sha256(systems_path),
            "term_vif": str(vif_path.resolve()),
            "term_vif_sha256": sha256(vif_path),
        },
    }
    output_path = args.output_dir / "climate_free_baseline_gate_result.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "checks": checks, "metrics": metrics}))
    return 0 if all(checks.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
