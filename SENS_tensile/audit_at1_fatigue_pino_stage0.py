#!/usr/bin/env python3
"""Audit whether the locked Hard5 factorial archive can support AT1-fatigue PINO residuals.

This is a read-only data/provenance audit.  It does not train a model or solve
the FEM problem.  The only write is the requested JSON report.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import scipy.io as sio


CASE_DIRS = {
    "factorial_hard_5step_u012": "02_hard_5step_factorial",
    "factorial_hard_8step_u012": "01_hard_8step_historical",
    "factorial_soft_5step_u012": "04_soft_5step",
    "factorial_soft_8step_u012": "03_soft_8step",
}


def mat_inventory(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        {"name": name, "shape": list(shape), "class": cls}
        for name, shape, cls in sio.whosmat(path)
    ]


def vtk_arrays(path: Path) -> dict[str, list[str]]:
    arrays: dict[str, list[str]] = {"point": [], "cell": []}
    if not path.exists():
        return arrays
    section = ""
    pattern = re.compile(r"^(?:SCALARS|VECTORS)\s+([^\s]+)")
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("POINT_DATA"):
                section = "point"
            elif line.startswith("CELL_DATA"):
                section = "cell"
            else:
                match = pattern.match(line)
                if section and match:
                    arrays[section].append(match.group(1))
    return arrays


def case_audit(
    case_id: str, root: Path, expected_cycles: int, expected_substeps: int
) -> dict[str, object]:
    psi_files = sorted((root / "psi_fields").glob("cycle_*.mat"))
    substep_vtks = sorted(root.glob("fields_*_*.vtk"))
    vtk_pattern = re.compile(r"fields_(\d+)_(\d+)\.vtk$")
    vtk_pairs = [
        (int(match.group(1)), int(match.group(2)))
        for path in substep_vtks
        if (match := vtk_pattern.match(path.name))
    ]
    retained_substep_series_complete = (
        len(vtk_pairs) == expected_cycles * expected_substeps
        and {step for _, step in vtk_pairs} == set(range(1, expected_substeps + 1))
    )
    peak_vtk = root / "peak_load_c1.vtk"
    sample_psi = psi_files[0] if psi_files else root / "psi_fields" / "cycle_0001.mat"
    sample_unloaded = substep_vtks[0] if substep_vtks else root / "missing.vtk"
    return {
        "case_id": case_id,
        "root": str(root),
        "root_exists": root.is_dir(),
        "expected_cycle_states": expected_cycles,
        "expected_substeps_per_cycle": expected_substeps,
        "psi_cycle_files": len(psi_files),
        "psi_cycle_count_matches": len(psi_files) == expected_cycles,
        "psi_sample": str(sample_psi),
        "psi_fields": mat_inventory(sample_psi),
        "peak_vtk": str(peak_vtk),
        "peak_vtk_exists": peak_vtk.exists(),
        "peak_vtk_arrays": vtk_arrays(peak_vtk),
        "cycle_end_vtk_count": len(substep_vtks),
        "cycle_end_vtk_substep_ordinals": sorted({step for _, step in vtk_pairs}),
        "retained_substep_series_complete": retained_substep_series_complete,
        "cycle_end_vtk_sample": str(sample_unloaded),
        "cycle_end_vtk_arrays": vtk_arrays(sample_unloaded),
        "checkpoint_fields": mat_inventory(root / "checkpoint.mat"),
        "initial_state_metadata_fields": mat_inventory(root / "initial_state_metadata.mat"),
        "state0_analysis_fields": mat_inventory(root / "state0_analysis.mat"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--source-base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.dataset / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        item["trajectory_id"]: int(item["state_count"])
        for item in manifest["trajectories"]
    }
    cases = [
        case_audit(
            case_id,
            args.source_base / dirname,
            expected[case_id],
            5 if "5step" in case_id else 8,
        )
        for case_id, dirname in CASE_DIRS.items()
    ]

    materialized_channels = list(manifest.get("state_channels", []))
    per_cycle_psi_names = {
        item["name"]
        for case in cases
        for item in case["psi_fields"]
    }
    full_cycle_u = "u" in per_cycle_psi_names or "displ" in per_cycle_psi_names
    full_cycle_nodal_d = any(
        item["name"] in {"p_field", "d_node"}
        for case in cases
        for item in case["psi_fields"]
    )
    full_cycle_gp_history = any(
        item["name"] in {"history_vars", "history_vars_old", "H_gp", "alpha_bar_gp"}
        for case in cases
        for item in case["psi_fields"]
    )
    substep_state_series = all(c["retained_substep_series_complete"] for c in cases)

    readiness = {
        "mechanical_equilibrium_residual": {
            "computable": bool(full_cycle_u and full_cycle_nodal_d),
            "reason": "Per-cycle coherent peak displacement and nodal damage are absent from psi_fields; peak_load_c1.vtk covers cycle 1 only.",
        },
        "at1_projected_kkt_residual": {
            "computable": bool(full_cycle_u and full_cycle_nodal_d and full_cycle_gp_history),
            "reason": "Per-cycle nodal u/d and Gauss-point committed history/lower-bound state are not archived together.",
        },
        "fatigue_history_residual": {
            "computable": bool(substep_state_series and full_cycle_gp_history),
            "reason": "Cycle files contain peak summaries only; unload/reload substep drivers and Gauss-point fatigue states are absent.",
        },
    }
    full_ready = all(item["computable"] for item in readiness.values())
    report = {
        "audit_id": "at1_fatigue_mesh_pino_stage0_20260824",
        "audit_kind": "read_only_physics_computability",
        "dataset_manifest": str(manifest_path),
        "dataset_id": manifest.get("dataset_id"),
        "claim_scope": manifest.get("claim_scope"),
        "materialized_state_channels": materialized_channels,
        "cases": cases,
        "trajectory_level_findings": {
            "per_cycle_peak_element_summaries_complete": all(c["psi_cycle_count_matches"] for c in cases),
            "per_cycle_coherent_peak_displacement": full_cycle_u,
            "per_cycle_coherent_peak_nodal_damage": full_cycle_nodal_d,
            "per_cycle_gauss_point_internal_state": full_cycle_gp_history,
            "retained_substep_state_series": substep_state_series,
            "terminal_checkpoint_only": True,
        },
        "residual_readiness": readiness,
        "full_at1_fatigue_pino_ready": full_ready,
        "decision": (
            "GO_FULL_AT1_FATIGUE_PINO"
            if full_ready
            else "STOP_FULL_PINO__REQUEST_PRODUCER_MATCHED_SUBSTEP_EXPORT"
        ),
        "minimum_missing_export": {
            "state_granularity": "every retained load substep, including unload and next-cycle reload",
            "nodal": ["u", "d", "d_lower_bound_or_previous_committed_d"],
            "gauss_point": ["committed_tensile_history_H", "alpha_bar", "previous_driver_q", "fatigue_degradation_f"],
            "static": ["coordinates", "Q4 connectivity", "boundary masks", "prescribed load action", "material constants", "quadrature rule"],
            "producer_semantics": ["AMOR split", "history commit timing", "fatigue update ordering", "cycle/substep/raw-step map"],
        },
        "training_launched": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decision": report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
