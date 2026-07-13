#!/usr/bin/env python3
"""Validate PIDL/FEM analysis result packages.

This is a deterministic safety check for generated diagnostic packages. It does
not decide scientific claims or launch experiments.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PRIMARY_MASKS = {"fem_top1_clean", "fem_pz_1200", "fem_core_2400"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_bounded_degradation_package(package: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "decision.md",
        "analysis_manifest.json",
        "tables/bounded_degradation_counterfactual_c89.csv",
        "tables/c69_c89_degradation_transition.csv",
        "tables/c69_c89_degradation_transition_delta.csv",
        "tables/alpha_bound_violation_by_mask.csv",
        "figures/c89_bounded_degradation_counterfactual_panel.pdf",
        "figures/c89_bounded_degradation_counterfactual_panel.png",
    ]
    for rel in required:
        require((package / rel).exists(), f"missing required asset: {rel}", errors)
    if errors:
        return errors

    manifest = load_json(package / "analysis_manifest.json")
    decision_text = (package / "decision.md").read_text(encoding="utf-8")
    verdict = manifest.get("verdict", {})

    require(manifest.get("state_mapping", {}).get("c69_peak", "").find("step344") >= 0, "c69 mapping must be PIDL step344", errors)
    require(manifest.get("state_mapping", {}).get("c89_peak", "").find("step444") >= 0, "c89 mapping must be PIDL step444", errors)
    require(set(manifest.get("primary_masks", [])) == PRIMARY_MASKS, "primary masks must be denominator-safe c89 masks", errors)
    require("quarantined" in manifest.get("top5_policy", ""), "top5 policy must quarantine top5 as primary evidence", errors)
    require(verdict.get("production_run_justified_now") is False, "package must not justify production run now", errors)
    require("no production run launched" in decision_text.lower(), "decision must state no production run launched", errors)
    require("top5 FEM psi mask is not used as primary evidence" in decision_text, "decision must state top5 is not primary evidence", errors)

    counter_rows = read_csv(package / "tables/bounded_degradation_counterfactual_c89.csv")
    primary_rows = [r for r in counter_rows if r.get("role") == "primary"]
    require(len(primary_rows) == 3, "counterfactual table must have exactly three primary rows", errors)
    require({r.get("mask_name") for r in primary_rows} == PRIMARY_MASKS, "counterfactual primary rows must match primary masks", errors)
    require(not any("top5" in r.get("mask_name", "").lower() for r in primary_rows), "top5 cannot appear as primary row", errors)

    transition_rows = read_csv(package / "tables/c69_c89_degradation_transition.csv")
    steps_by_state = {(r.get("state"), r.get("pidl_step")) for r in transition_rows}
    require(("c69", "344") in steps_by_state, "transition table missing c69 step344", errors)
    require(("c89", "444") in steps_by_state, "transition table missing c89 step444", errors)

    if verdict.get("bounded_degradation_failure_likely"):
        require(
            int(verdict.get("bounded_degradation_primary_masks_passing", 0)) >= 1,
            "bounded_degradation true requires at least one passing primary mask",
            errors,
        )
    if verdict.get("raw_driver_branch_should_dominate_next"):
        require(
            verdict.get("recommended_next_branch") == "raw-driver amplitude audit",
            "raw-driver domination must recommend raw-driver amplitude audit",
            errors,
        )

    return errors


def check_bounded_alpha_micro_package(package: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "decision.md",
        "analysis_manifest.json",
        "tables/c89_source_level_counterfactual_by_mask.csv",
        "tables/history_ordering_step_microdiagnostic.csv",
        "tables/intervention_ranking.csv",
        "figures/bounded_alpha_history_order_microdiagnostic_panel.pdf",
        "figures/bounded_alpha_history_order_microdiagnostic_panel.png",
    ]
    for rel in required:
        require((package / rel).exists(), f"missing required asset: {rel}", errors)
    if errors:
        return errors

    manifest = load_json(package / "analysis_manifest.json")
    decision_text = (package / "decision.md").read_text(encoding="utf-8")
    verdict = manifest.get("verdict", {})
    require(set(manifest.get("primary_masks", [])) == PRIMARY_MASKS, "primary masks must be denominator-safe c89 masks", errors)
    require(manifest.get("state_policy", {}).get("c69", "").startswith("transition"), "c69 must be transition diagnostic only", errors)
    require(verdict.get("production_run_justified_now") is False, "micro package must not justify production run now", errors)
    require("no production run launched" in decision_text.lower(), "decision must state no production run launched", errors)
    require("psi_plus_prev" in decision_text, "decision must state psi_plus_prev export limitation", errors)

    counter_rows = read_csv(package / "tables/c89_source_level_counterfactual_by_mask.csv")
    primary_rows = [r for r in counter_rows if r.get("role") == "primary"]
    require({r.get("mask_name") for r in primary_rows} == PRIMARY_MASKS, "counterfactual primary rows must match primary masks", errors)
    require(not any("top5" in r.get("mask_name", "").lower() for r in primary_rows), "top5 cannot appear as primary row", errors)

    ranking_rows = read_csv(package / "tables/intervention_ranking.csv")
    interventions = {r.get("intervention") for r in ranking_rows}
    for expected in {
        "residual_stiffness_or_degradation_floor_1e-3",
        "alpha_cap_0p98_or_0p99",
        "lagged_hist_alpha_driver",
        "raw_driver_amplitude",
    }:
        require(expected in interventions, f"missing intervention ranking: {expected}", errors)
    if verdict.get("residual_floor_candidate"):
        row = next((r for r in ranking_rows if r.get("intervention") == "residual_stiffness_or_degradation_floor_1e-3"), {})
        require(float(row.get("mean_gain_orders", "0")) >= 3.0, "residual floor candidate requires >=3 order gain", errors)

    return errors


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("bounded-degradation")
    sp.add_argument("--package", required=True, type=Path)
    sp = sub.add_parser("bounded-alpha-micro")
    sp.add_argument("--package", required=True, type=Path)
    args = p.parse_args()

    if args.cmd == "bounded-degradation":
        errors = check_bounded_degradation_package(args.package.expanduser())
    elif args.cmd == "bounded-alpha-micro":
        errors = check_bounded_alpha_micro_package(args.package.expanduser())
    else:
        raise SystemExit(f"unknown command: {args.cmd}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        raise SystemExit(1)
    print("result package check passed")


if __name__ == "__main__":
    main()
