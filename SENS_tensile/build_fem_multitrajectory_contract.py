#!/usr/bin/env python3
"""Build source-backed FEM trajectory contracts and scoped split locks.

This is ingestion and validation only. It never launches temporal training.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "SENS_tensile") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "SENS_tensile"))

from fem_trajectory_bundle import (  # noqa: E402
    BUNDLE_SCHEMA_VERSION,
    build_factorial_loco_split_lock,
    build_loto_split_lock,
    build_source_backed_bundle,
    canonical_json_sha256,
    sha256_file,
    validate_bundle,
    validate_loto_split,
    write_json,
)

DEFAULT_HARD5_ROOT = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729"
)
DEFAULT_FACTORIAL_ROOT = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "griphfith/Umax_012_all_versions_20260729"
)
DEFAULT_MESH = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/"
    "after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/"
    "fem_anchored_mesh_operator_20260715/data/fem_cycle_peak_mechanism_graph.npz"
)

AMPLITUDE_CASES = (
    {
        "trajectory_id": "hard5_eta0_u011_5step_20260729",
        "subdir": "u011/SENS_hard5_u011_eta0_canonical_v1",
        "umax": 0.11,
        "first_hit": 122,
        "confirmed": 125,
    },
    {
        "trajectory_id": "hard5_eta0_u012_5step_20260729",
        "subdir": "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1",
        "umax": 0.12,
        "first_hit": 83,
        "confirmed": 86,
    },
    {
        "trajectory_id": "hard5_eta0_u013_5step_20260729",
        "subdir": "u013/SENS_hard5_u013_eta0_canonical_v1",
        "umax": 0.13,
        "first_hit": 59,
        "confirmed": 62,
    },
)

FACTORIAL_CASES = (
    {
        "trajectory_id": "factorial_hard_8step_u012",
        "subdir": "01_hard_8step_historical",
        "initial_tip_state": "hard_recovery",
        "initial_defect_family": "hard_zero_load_recovery_tip",
        "loading_history": "explicit_8step",
        "n_substeps": 8,
        "load_factors": [0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0],
        "first_hit": 86,
        "confirmed": 89,
        "stored_through": 89,
    },
    {
        "trajectory_id": "factorial_hard_5step_u012",
        "subdir": "02_hard_5step_factorial",
        "initial_tip_state": "hard_recovery",
        "initial_defect_family": "hard_zero_load_recovery_tip",
        "loading_history": "retained_5step",
        "n_substeps": 5,
        "load_factors": [0.25, 0.5, 0.75, 1.0, 0.0],
        "first_hit": 83,
        "confirmed": 86,
        "stored_through": 86,
    },
    {
        "trajectory_id": "factorial_soft_8step_u012",
        "subdir": "03_soft_8step",
        "initial_tip_state": "analytic_soft_profile",
        "initial_defect_family": "analytic_soft_crack_tip_profile",
        "loading_history": "explicit_8step",
        "n_substeps": 8,
        "load_factors": [0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0],
        "first_hit": 83,
        "confirmed": 86,
        "stored_through": 86,
    },
    {
        "trajectory_id": "factorial_soft_5step_u012",
        "subdir": "04_soft_5step",
        "initial_tip_state": "analytic_soft_profile",
        "initial_defect_family": "analytic_soft_crack_tip_profile",
        "loading_history": "retained_5step",
        "n_substeps": 5,
        "load_factors": [0.25, 0.5, 0.75, 1.0, 0.0],
        "first_hit": 84,
        "confirmed": 87,
        "stored_through": 87,
    },
)

PENDING_SLOTS = (
    {
        "slot_id": "independent_initial_defect_variant",
        "status": "awaiting_handoff",
        "required_variation_axis": "initial_defect",
        "source_path": None,
        "source_sha256": None,
        "trajectory_id": None,
        "note": "Producer-reported independent trajectory is still awaiting a source package.",
    },
    {
        "slot_id": "independent_material_variant",
        "status": "awaiting_handoff",
        "required_variation_axis": "material_state",
        "source_path": None,
        "source_sha256": None,
        "trajectory_id": None,
        "note": "Producer-reported independent trajectory is still awaiting a source package.",
    },
    {
        "slot_id": "independent_loading_history_variant",
        "status": "awaiting_handoff",
        "required_variation_axis": "loading_history",
        "source_path": None,
        "source_sha256": None,
        "trajectory_id": None,
        "note": "Producer-reported independent trajectory is still awaiting a source package.",
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hard5-root", type=Path, default=DEFAULT_HARD5_ROOT)
    parser.add_argument("--factorial-root", type=Path, default=DEFAULT_FACTORIAL_ROOT)
    parser.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "analysis" / "fem_multitrajectory_contract_20260729",
    )
    parser.add_argument(
        "--deep", action="store_true", help="Open and validate every state shard"
    )
    return parser.parse_args()


def bundle_json_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BUNDLE_SCHEMA_VERSION,
        "title": "FEM fracture trajectory source-backed bundle",
        "type": "object",
        "required": [
            "schema_version",
            "bundle_id",
            "trajectory_id",
            "family_id",
            "independence_class",
            "claim_scope",
            "source",
            "physics",
            "mesh",
            "state_semantics",
            "event",
            "fields",
            "observable_proxies",
            "states",
            "manifest_sha256",
        ],
        "properties": {
            "schema_version": {"const": BUNDLE_SCHEMA_VERSION},
            "trajectory_id": {"type": "string", "minLength": 1},
            "family_id": {"type": "string", "minLength": 1},
            "independence_class": {
                "enum": [
                    "independent_physical_trajectory",
                    "load_amplitude_sensitivity",
                    "controlled_factorial_combination",
                    "protocol_comparator",
                ]
            },
            "states": {"type": "array", "minItems": 1},
        },
        "additionalProperties": True,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_versions(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["folder"]: row for row in csv.DictReader(handle)}


def audit_factorial_source(
    root: Path, case: dict[str, Any], versions: dict[str, dict[str, str]]
) -> dict[str, Any]:
    source = root / case["subdir"]
    row = versions.get(case["subdir"])
    errors: list[str] = []
    if row is None:
        errors.append("missing versions.csv row")
    else:
        expected = {
            "effective_steps": case["n_substeps"],
            "first_hit_cycle": case["first_hit"],
            "confirmed_cycle": case["confirmed"],
            "stored_through_cycle": case["stored_through"],
        }
        for key, value in expected.items():
            if int(row[key]) != value:
                errors.append(f"versions.csv {key} mismatch")
    shards = sorted((source / "psi_fields").glob("cycle_*.mat"))
    cycles = [int(path.stem.split("_")[-1]) for path in shards]
    if cycles != list(range(1, case["stored_through"] + 1)):
        errors.append(
            "psi_fields are not contiguous through the registered terminal cycle"
        )
    vtk_files = sorted(source.glob("fields_*.vtk"))
    bad_vtk = [
        path.name
        for path in vtk_files
        if not re.search(rf"_{case['n_substeps']:03d}\.vtk$", path.name)
    ]
    if bad_vtk:
        errors.append(f"VTK loading-step suffix mismatch: {bad_vtk[:3]}")
    row_counts = {}
    for name in ("crack_regularized.dat", "extra_scalars.dat", "monitorcycle.dat"):
        path = source / name
        row_counts[name] = (
            sum(1 for _ in path.open(encoding="utf-8", errors="replace")) - 1
        )
        if row_counts[name] != case["stored_through"]:
            errors.append(f"{name} row count mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "checks": {
            "state_shards": len(shards),
            "vtk_files": len(vtk_files),
            "vtk_step_suffix": case["n_substeps"],
            "scalar_row_counts": row_counts,
        },
    }


def build_registry(
    bundles: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    source_audits: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle, report in zip(bundles, reports):
        factorial = bundle["independence_class"] == "controlled_factorial_combination"
        rows.append(
            {
                "package_id": bundle["source"]["package_id"],
                "trajectory_id": bundle["trajectory_id"],
                "availability": "present",
                "validation": "pass"
                if report["valid"]
                and source_audits.get(bundle["trajectory_id"], {"valid": True})["valid"]
                else "fail",
                "evidence_class": "shared_geometry_2x2_factorial"
                if factorial
                else "load_amplitude_sensitivity_library",
                "primary_road_loto_eligible": False,
                "within_hard5_loco_eligible": factorial,
                "family_id": bundle["family_id"],
                "umax": bundle["physics"]["umax"],
                "n_substeps": bundle["physics"]["n_substeps"],
                "initial_tip_state": bundle["physics"]
                .get("factorial_axes", {})
                .get("initial_tip_state", "hard_recovery_shared"),
                "loading_history": bundle["physics"]
                .get("factorial_axes", {})
                .get("loading_history", "retained_5step_shared"),
                "first_hit": bundle["event"]["first_hit"]["cycle"],
                "confirmed": bundle["event"]["confirmed"]["cycle"],
                "state_count": len(bundle["states"]),
                "source_root": bundle["source"]["root"],
                "reason": "Controlled initial-tip x loading-history combination; shared geometry/material/Umax."
                if factorial
                else "Only Umax changes; this family cannot inflate independent-trajectory count.",
            }
        )
    rows.append(
        {
            "package_id": "hard5_u012_formal_duplicate",
            "trajectory_id": "EXCLUDED_DUPLICATE_CONFIGURATION",
            "availability": "present",
            "validation": "registered_not_ingested",
            "evidence_class": "duplicate_hard_5step_configuration",
            "primary_road_loto_eligible": False,
            "within_hard5_loco_eligible": False,
            "family_id": "hard5_u012_hard_5step_duplicate_group",
            "umax": 0.12,
            "n_substeps": 5,
            "initial_tip_state": "hard_recovery",
            "loading_history": "retained_5step",
            "first_hit": 83,
            "confirmed": 86,
            "state_count": "not_counted",
            "source_root": str(
                DEFAULT_FACTORIAL_ROOT / "05_hard_5step_formal_pidl_native_q4"
            ),
            "reason": "Same factorial cell as hard/5-step; excluded to prevent replicate/configuration leakage.",
        }
    )
    rows.append(
        {
            "package_id": "legacy_reversebc_soft_hist0_c69",
            "trajectory_id": "legacy_c69_reversebc_soft_hist0",
            "availability": "remote_reference_only",
            "validation": "rejected_old_c69",
            "evidence_class": "do_not_cite",
            "primary_road_loto_eligible": False,
            "within_hard5_loco_eligible": False,
            "family_id": "legacy_reversebc_soft_hist0",
            "umax": 0.12,
            "n_substeps": "unknown_or_unmatched",
            "initial_tip_state": "legacy",
            "loading_history": "legacy",
            "first_hit": 69,
            "confirmed": 69,
            "state_count": 0,
            "source_root": "/mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat",
            "reason": "Explicit legacy c69 package rejected by provenance marker.",
        }
    )
    for slot in PENDING_SLOTS:
        rows.append(
            {
                "package_id": slot["slot_id"],
                "trajectory_id": "UNASSIGNED",
                "availability": "awaiting_handoff",
                "validation": "not_run_missing_data",
                "evidence_class": "pending_independent_trajectory",
                "primary_road_loto_eligible": False,
                "within_hard5_loco_eligible": False,
                "family_id": "UNASSIGNED",
                "umax": "UNDECLARED",
                "n_substeps": "UNDECLARED",
                "initial_tip_state": "UNDECLARED",
                "loading_history": "UNDECLARED",
                "first_hit": "UNDECLARED",
                "confirmed": "UNDECLARED",
                "state_count": 0,
                "source_root": "",
                "reason": slot["note"],
            }
        )
    return rows


def decision_text(
    amplitude_reports: list[dict[str, Any]],
    factorial_reports: list[dict[str, Any]],
    road_split: dict[str, Any],
    factorial_split: dict[str, Any],
) -> str:
    return f"""# FEM multi-trajectory contract decision

Date: 2026-07-29

## Verdict

**Two different readiness gates now have different outcomes.**

- Road-like leave-one-independent-trajectory-out: **{road_split['status'].upper()}**. Zero independently varied road-like trajectories are currently ingested; the three producer handoffs remain pending. No road-generalization training is allowed.
- Shared-geometry Hard5 2x2 leave-one-combination-out: **{factorial_split['status'].upper()}**. The hard/soft initial-tip state x retained-5/explicit-8 loading-history cells may support a scoped numerical LOCO experiment after {sum(r['valid'] for r in factorial_reports)}/{len(factorial_reports)} bundle validation.

No model training was run by this task. The factorial result is not four independent roads, material generalization, or geometry generalization. It tests only whether a model can hold out one controlled combination while geometry, mesh, material, Umax=0.12, eta=0, and the event rule remain shared.

## Libraries and exclusions

The Umax 0.11/0.12/0.13 set passed {sum(r['valid'] for r in amplitude_reports)}/{len(amplitude_reports)} validation, but remains one load-amplitude sensitivity library. Its Umax=0.12 hard/5-step member duplicates the corresponding factorial configuration and cannot be counted again in a train/test split. The old reverse-BC c69 package remains rejected by provenance identity, while a genuinely new trajectory is not rejected merely because its event happens at cycle 69.

## Contract gates

Each accepted trajectory carries cycle-peak semantics, explicit substep-to-raw-step mapping, distinct first-hit and confirmed roles, immutable state/provenance hashes, mesh identity, and damage, alpha_bar, fatigue degradation, raw driver, derived damage degradation, and derived active driver. Crack-image and strain-localization channels are synthetic FEM proxies; FWD is unavailable, so none may be relabelled as real road measurement.

Both split locks use complete trajectories. Node, cycle, and cross-window leakage are forbidden. Mixed 5/8-step states are allowed only as explicitly conditioned separate factorial trajectories, never silently merged under one loading protocol.
"""


def manifest_hashes(output: Path) -> None:
    files = sorted(
        path
        for path in output.rglob("*")
        if path.is_file() and path.name != "HASHES.sha256"
    )
    (output / "HASHES.sha256").write_text(
        "\n".join(f"{sha256_file(path)}  {path.relative_to(output)}" for path in files)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "fem_trajectory_bundle_schema_v1.json", bundle_json_schema())
    write_json(
        output / "independent_trajectory_handoff_registry_v1.json",
        {"slots": list(PENDING_SLOTS)},
    )

    bundles: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    source_audits: dict[str, dict[str, Any]] = {}
    amplitude_provenance = (
        args.hard5_root / "MANIFEST.csv",
        args.hard5_root / "comparison" / "comparison_summary.csv",
    )
    for case in AMPLITUDE_CASES:
        source_root = args.hard5_root / case["subdir"]
        bundle = build_source_backed_bundle(
            trajectory_id=case["trajectory_id"],
            family_id="hard5_eta0_5step_load_amplitude_family_20260729",
            independence_class="load_amplitude_sensitivity",
            source_root=source_root,
            mesh_graph_path=args.mesh,
            umax=case["umax"],
            first_hit_cycle=case["first_hit"],
            confirmed_cycle=case["confirmed"],
            n_substeps=5,
            eta=0.0,
            source_package_id=f"Hard5_eta0_5step_Umax_{case['umax']:.2f}_20260729",
            provenance_files=amplitude_provenance,
            mesh_evidence_path=source_root / "peak_load_c1.vtk",
        )
        bundles.append(bundle)
        reports.append(validate_bundle(bundle, deep=args.deep).as_dict())

    versions = read_versions(args.factorial_root / "versions.csv")
    factorial_provenance = (
        args.factorial_root / "README.md",
        args.factorial_root / "versions.csv",
        args.factorial_root / "file_manifest.csv",
        args.factorial_root / "analysis_2x2_factorial" / "README.md",
        args.factorial_root / "analysis_2x2_factorial" / "summary.csv",
    )
    for case in FACTORIAL_CASES:
        audit = audit_factorial_source(args.factorial_root, case, versions)
        source_audits[case["trajectory_id"]] = audit
        source_root = args.factorial_root / case["subdir"]
        bundle = build_source_backed_bundle(
            trajectory_id=case["trajectory_id"],
            family_id="hard5_eta0_u012_shared_geometry_2x2_factorial_20260729",
            independence_class="controlled_factorial_combination",
            source_root=source_root,
            mesh_graph_path=args.mesh,
            umax=0.12,
            first_hit_cycle=case["first_hit"],
            confirmed_cycle=case["confirmed"],
            n_substeps=case["n_substeps"],
            eta=0.0,
            source_package_id=f"Umax_012_2x2::{case['subdir']}",
            provenance_files=factorial_provenance,
            loading_family=case["loading_history"],
            nominal_load_factors=case["load_factors"],
            initial_defect_family=case["initial_defect_family"],
            factorial_axes={
                "initial_tip_state": case["initial_tip_state"],
                "loading_history": case["loading_history"],
            },
            provenance_notes=(
                "shared geometry/mesh/material/Umax/event rule",
                "soft-8 resumed at c47/load-step8 without state reinitialization"
                if case["subdir"] == "03_soft_8step"
                else "continuous producer package",
            ),
            mesh_evidence_path=source_root / "peak_load_c1.vtk",
        )
        report = validate_bundle(bundle, deep=args.deep).as_dict()
        if not audit["valid"]:
            report["valid"] = False
            report["errors"].extend(audit["errors"])
        bundles.append(bundle)
        reports.append(report)

    factorial_mesh_hashes = {
        bundle["trajectory_id"]: bundle["mesh"]["source_package_evidence"][
            "content_sha256"
        ]
        for bundle in bundles[len(AMPLITUDE_CASES) :]
    }
    mesh_group_audit = {
        "valid": len(set(factorial_mesh_hashes.values())) == 1,
        "factorial_vtk_mesh_content_sha256": factorial_mesh_hashes,
        "unique_factorial_mesh_count": len(set(factorial_mesh_hashes.values())),
        "expected_cell_count": bundles[0]["mesh"]["cell_count"],
        "claim": "shared mesh within the 2x2 factorial",
    }
    if not mesh_group_audit["valid"]:
        for report in reports[len(AMPLITUDE_CASES) :]:
            report["valid"] = False
            report["errors"].append("factorial VTK mesh signatures are not identical")

    for bundle in bundles:
        write_json(output / "bundles" / f"{bundle['trajectory_id']}.json", bundle)
    amplitude_reports = reports[: len(AMPLITUDE_CASES)]
    factorial_reports = reports[len(AMPLITUDE_CASES) :]
    road_split = build_loto_split_lock(bundles, PENDING_SLOTS)
    factorial_split = build_factorial_loco_split_lock(bundles)
    road_report = validate_loto_split(road_split, bundles).as_dict()
    factorial_split_report = validate_loto_split(factorial_split, bundles).as_dict()
    write_json(output / "road_loto_split_lock_v1.json", road_split)
    write_json(output / "loto_split_lock_v1.json", road_split)
    write_json(
        output / "within_hard5_factorial_loco_split_lock_v1.json", factorial_split
    )
    write_json(
        output / "bundle_validation.json",
        {
            "deep_validation": args.deep,
            "bundle_reports": reports,
            "factorial_source_audits": source_audits,
            "mesh_group_audit": mesh_group_audit,
            "road_split_report": road_report,
            "factorial_split_report": factorial_split_report,
        },
    )
    registry = build_registry(bundles, reports, source_audits)
    write_csv(output / "fem_package_registry.csv", registry)
    write_json(output / "fem_package_registry.json", {"packages": registry})
    (output / "decision.md").write_text(
        decision_text(
            amplitude_reports, factorial_reports, road_split, factorial_split
        ),
        encoding="utf-8",
    )
    deep_checked = sum(
        int(report["checks"].get("deep_state_shards_checked", 0)) for report in reports
    )
    state_total = sum(len(bundle["states"]) for bundle in bundles)
    (output / "readiness_report.md").write_text(
        f"""# Multi-trajectory readiness

- Source-backed bundles: {sum(report['valid'] for report in reports)}/{len(reports)} valid.
- Deep state shards: {deep_checked}/{state_total} checked.
- Umax sensitivity library: 3 trajectories; excluded from independent-count inflation.
- Shared-geometry 2x2 factorial: {sum(report['valid'] for report in factorial_reports)}/4 valid; LOCO folds={len(factorial_split['folds'])}; status={factorial_split['status']}.
- Independent road-like trajectories: 0/3 required; status={road_split['status']}.
- Pending producer handoffs: initial-defect, material-state, loading-history variants.
- Training performed by this task: no.

The factorial gate is numerical and scoped. It does not establish independent-road, material, or geometry generalization.
""",
        encoding="utf-8",
    )
    run_manifest = {
        "analysis_id": "fem_multitrajectory_contract_20260729",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_type": "ingestion_validation_and_split_preregistration_only",
        "training_run": False,
        "hard5_source": str(args.hard5_root.resolve()),
        "factorial_source": str(args.factorial_root.resolve()),
        "mesh_source": str(args.mesh.resolve()),
        "deep_validation": args.deep,
        "bundle_count": len(bundles),
        "state_shard_count": state_total,
        "independent_road_like_count": 0,
        "load_amplitude_sensitivity_count": len(AMPLITUDE_CASES),
        "controlled_factorial_combination_count": len(FACTORIAL_CASES),
        "road_split_status": road_split["status"],
        "road_training_launch_allowed": road_split["training_launch_allowed"],
        "factorial_split_status": factorial_split["status"],
        "scoped_factorial_training_launch_allowed": factorial_split[
            "training_launch_allowed"
        ],
        "training_launched": False,
        "bundle_manifest_hashes": {
            bundle["trajectory_id"]: bundle["manifest_sha256"] for bundle in bundles
        },
        "road_split_lock_sha256": road_split["lock_sha256"],
        "factorial_split_lock_sha256": factorial_split["lock_sha256"],
        "contract_sha256": canonical_json_sha256(bundle_json_schema()),
    }
    write_json(output / "RUN_MANIFEST.json", run_manifest)
    manifest_hashes(output)
    if (
        not all(report["valid"] for report in reports)
        or not road_report["valid"]
        or not factorial_split_report["valid"]
    ):
        raise SystemExit("validation failed; inspect bundle_validation.json")
    print(json.dumps(run_manifest, indent=2))


if __name__ == "__main__":
    main()
