#!/usr/bin/env python3
"""Build the frozen Agent1 -> Agent2/3 road state handoff package.

This is an offline interface conversion. It performs no training and preserves
the c87 FEM raw-energy observation as an oracle-only upper-bound channel.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_observation_state_bundle import (  # noqa: E402
    AGENT2_PACKET_VERSION,
    AGENT3_SKELETON_VERSION,
    BUNDLE_VERSION,
    agent2_innovation_packet,
    build_bundle_from_legacy,
    bundle_schema,
    sha256,
    validate_agent2_packet,
    validate_bundle,
    write_agent3_history_skeleton,
)


PROJECT_ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl")
PHASE1 = PROJECT_ROOT / "local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/road_observation_latent_state_phase1_20260723"
AGENT2 = PROJECT_ROOT / ".codex/worktrees/data-efficient-cycle-forecast/analysis/road_time_trigger_formulation_20260723"
AGENT3 = PROJECT_ROOT / ".codex/worktrees/temporal-graph-transformer/docs/road_observation_aware_stage1_20260723"

SOURCE_FILES = {
    "road_observation_operator_v1": PHASE1 / "road_observation_operator_spec.json",
    "road_assimilated_state_v1_schema": PHASE1 / "assimilated_state_schema.json",
    "road_assimilated_state_v1_payload": PHASE1 / "assimilated_state_c87_synthetic_reference.npz",
    "agent2_road_time_mapping_v1": AGENT2 / "road_time_mapping_spec.json",
    "agent2_road_forecast_horizon_v1": AGENT2 / "road_forecast_horizon_spec.json",
    "agent2_road_observation_trigger_v1": AGENT2 / "observation_trigger_spec.json",
    "agent3_road_forecast_input_contract_v1": AGENT3 / "road_forecast_input_contract_v1.json",
}

LOCKED_SOURCE_SHA256 = {
    "road_observation_operator_v1": "b067ace595a1cb0055f680e0ac7c2e7e2866c4f17192d4ba8c56d5838e7bbacc",
    "road_assimilated_state_v1_schema": "18f9191e3809e2905cf5a7adb3dbc26b63fdf050d4ae346c268c3c39af7dda31",
    "road_assimilated_state_v1_payload": "276bca62f3955c0948bd23891aa10dcca209f3e562605303b61b263d53759ffe",
    "agent2_road_time_mapping_v1": "630bbd878529fba18ed29c733c414433f51815e9243e7565697b6a81e2fd32c4",
    "agent2_road_forecast_horizon_v1": "f593a005a1175c5914ef0fd6b8855879180f726886abb69f48c0bec174d22fc5",
    "agent2_road_observation_trigger_v1": "94b4723dabfb4533efe748ce914677e01b5fa08a7c3f6bc9792feeadd5b393d3",
    "agent3_road_forecast_input_contract_v1": "5b64987822a6b3d1e543f18734317af41d42125562d6968f65d3ee27fde9f37b",
}

SOURCE_SCHEMA_VERSIONS = {
    "road_observation_operator_v1": "road_observation_operator_v1",
    "road_assimilated_state_v1_schema": "road_assimilated_state_v1",
    "road_assimilated_state_v1_payload": "road_assimilated_state_v1",
    "agent2_road_time_mapping_v1": "road_time_mapping_v1",
    "agent2_road_forecast_horizon_v1": "road_forecast_horizon_v1",
    "agent2_road_observation_trigger_v1": "road_observation_trigger_v1",
    "agent3_road_forecast_input_contract_v1": "road_forecast_input_contract_v1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "analysis/road_observation_state_bundle_v1_20260724",
    )
    parser.add_argument(
        "--schema-copy",
        type=Path,
        default=ROOT / "docs/templates/road_observation_state_bundle_v1.schema.json",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_sources() -> None:
    for source_id, path in SOURCE_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        expected = LOCKED_SOURCE_SHA256[source_id]
        if actual != expected:
            raise ValueError(f"source drift for {source_id}: expected {expected}, got {actual}")

    operator = read_json(SOURCE_FILES["road_observation_operator_v1"])
    state_schema = read_json(SOURCE_FILES["road_assimilated_state_v1_schema"])
    time_mapping = read_json(SOURCE_FILES["agent2_road_time_mapping_v1"])
    horizon = read_json(SOURCE_FILES["agent2_road_forecast_horizon_v1"])
    trigger = read_json(SOURCE_FILES["agent2_road_observation_trigger_v1"])
    forecast = read_json(SOURCE_FILES["agent3_road_forecast_input_contract_v1"])
    observed_versions = {
        "road_observation_operator_v1": operator.get("spec_version"),
        "road_assimilated_state_v1_schema": state_schema.get("schema_version"),
        "agent2_road_time_mapping_v1": time_mapping.get("schema"),
        "agent2_road_forecast_horizon_v1": horizon.get("schema"),
        "agent2_road_observation_trigger_v1": trigger.get("schema"),
        "agent3_road_forecast_input_contract_v1": forecast.get("contract_id"),
    }
    for source_id, version in observed_versions.items():
        if version != SOURCE_SCHEMA_VERSIONS[source_id]:
            raise ValueError(f"schema drift for {source_id}: {version}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compatibility_rows() -> list[dict[str, Any]]:
    return [
        {
            "consumer_or_source": "Agent1 road_observation_operator_v1",
            "version": "road_observation_operator_v1",
            "sha256": LOCKED_SOURCE_SHA256["road_observation_operator_v1"],
            "compatibility": "pass",
            "bundle_mapping": "measurement-space node/global/forcing channels plus evidence labels",
            "missing_or_boundary": "no calibrated road H in current package",
        },
        {
            "consumer_or_source": "Agent1 road_assimilated_state_v1",
            "version": "road_assimilated_state_v1",
            "sha256": LOCKED_SOURCE_SHA256["road_assimilated_state_v1_payload"],
            "compatibility": "pass_with_field_rename",
            "bundle_mapping": "alpha_bar->fatigue_history; log10_psi_raw remains canonical; add T axis",
            "missing_or_boundary": "uncertainty remains all-NaN uncalibrated; source remains oracle",
        },
        {
            "consumer_or_source": "Agent2 road_time_mapping_v1",
            "version": "road_time_mapping_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent2_road_time_mapping_v1"],
            "compatibility": "structural_pass_data_missing",
            "bundle_mapping": "timestamp/equivalent_load_index/delta_t/traffic/environment/maintenance with masks",
            "missing_or_boundary": "c87 has no road timestamp WIM ESAL environment or maintenance data",
        },
        {
            "consumer_or_source": "Agent2 road_forecast_horizon_v1",
            "version": "road_forecast_horizon_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent2_road_forecast_horizon_v1"],
            "compatibility": "pass",
            "bundle_mapping": "state mean plus exclusive std/covariance/ensemble uncertainty and common graph",
            "missing_or_boundary": "long-horizon scenario and RUL inputs are outside this bundle",
        },
        {
            "consumer_or_source": "Agent2 road_observation_trigger_v1",
            "version": "road_observation_trigger_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent2_road_observation_trigger_v1"],
            "compatibility": "skeleton_pass_not_decision_eligible",
            "bundle_mapping": "innovation packet with image/FWD/strain null and mask=false",
            "missing_or_boundary": "oracle raw field is audit-only and never exported as an innovation value",
        },
        {
            "consumer_or_source": "Agent3 road_forecast_input_contract_v1",
            "version": "road_forecast_input_contract_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent3_road_forecast_input_contract_v1"],
            "compatibility": "pass",
            "bundle_mapping": "z_analysis[T,N,4], uncertainty, node/global masks, history/forcing/reset skeleton",
            "missing_or_boundary": "observed latent mask maps to node observation only when values and evidence are explicit; no future scenario is fabricated",
        },
    ]


def write_text_assets(output: Path, bundle_hash: str, history_hash: str) -> None:
    (output / "00_intent.md").write_text(
        "# Intent: road observation-state bundle v1\n\n"
        "Mechanism question: can the frozen Agent1 observation/state interface be consumed byte-identically by Agent2 and Agent3 without relabelling FEM latent fields as road sensors?\n\n"
        "Cheapest test: schema adaptation and offline validation only. No training, no FEM solve, and no Taobo job.\n\n"
        "Success: locked source hashes, one canonical state bundle, missing-aware consumer skeletons, and failure tests for provenance/uncertainty/masks/maintenance.\n\n"
        "Failure: any missing road value is fabricated, any oracle field enters operational innovations, or interface pass is reported as real-road inversion.\n",
        encoding="utf-8",
    )
    (output / "decision.md").write_text(
        "# Road Observation-State Bundle v1: Decision\n\n"
        "## Verdict\n\n"
        "**Interface pass; real-road inversion remains untested and quarantined.**\n\n"
        "The frozen c87 Agent1 analysis state can now be consumed through one versioned schema by Agent2 and Agent3. The conversion preserves the original evidence class as `oracle`, preserves uncalibrated uncertainty as all-NaN, and does not create image, FWD, strain, WIM, temperature, moisture, timestamp, or equivalent-load values.\n\n"
        "## Frozen handoff\n\n"
        f"- Canonical bundle SHA-256: `{bundle_hash}`.\n"
        f"- Agent3 history skeleton SHA-256: `{history_hash}`.\n"
        "- Agent2 innovation packet is explicitly `decision_eligible=false`.\n"
        "- Agent2/3 must receive this same bundle hash and may not select model-specific observations or priors.\n\n"
        "## Semantic rules now enforced\n\n"
        "1. `observed_channel_mask` attributes latent analysis updates; it is not a sensor-availability mask.\n"
        "2. Node and global observation masks describe measurement availability. Missing means NaN/null plus `mask=false`, never zero evidence.\n"
        "3. State uncertainty uses exactly one of std, covariance, or ensemble. Uncalibrated std is NaN, not zero confidence.\n"
        "4. Timestamp, equivalent load, delta-t, registration, coordinate frame, evidence class, and source hashes are explicit.\n"
        "5. A maintenance reset requires a declared event id and a new state segment.\n"
        "6. Hidden damage/history/degradation/raw/active variables are rejected as deployable sensors. An explicitly oracle-suffixed audit channel may exist but cannot enter an operational trigger.\n\n"
        "## Unresolved boundary\n\n"
        "This package proves interface compatibility on one eta0 FEM trajectory only. It does not validate an image/FWD/strain observation operator, identify material parameters, calibrate posterior uncertainty, map FEM cycles to road time, or demonstrate road-section generalization. A real-road pass requires registered measurements with load/environment/maintenance provenance and physical holdout validation.\n",
        encoding="utf-8",
    )
    attempt = {
        "attempt_id": "road-observation-state-bundle-v1-20260724",
        "status": "completed_interface_pass_real_road_quarantined",
        "training_run": False,
        "compute": "Mac offline unit validation only",
        "fem_reference": "eta0",
        "source_bundle_evidence": "oracle",
        "claim": "versioned compatibility handoff only",
        "real_road_inversion_pass": False,
        "material_inverse": False,
        "single_trajectory": True,
    }
    (output / "attempts.jsonl").write_text(json.dumps(attempt, sort_keys=True) + "\n", encoding="utf-8")
    (output / "attempt.md").write_text(
        "# Attempt Ledger\n\n"
        "| Attempt | Compute | Result | Claim boundary |\n"
        "|---|---|---|---|\n"
        "| road-observation-state-bundle-v1-20260724 | Mac offline only; no training | interface pass | real-road inversion, material identification, and road generalization remain quarantined |\n",
        encoding="utf-8",
    )


def file_hashes(output: Path, *, exclude: set[str] | None = None) -> dict[str, str]:
    excluded = exclude or set()
    return {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and str(path.relative_to(output)) not in excluded
    }


def main() -> None:
    args = parse_args()
    verify_sources()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    schema = bundle_schema()
    schema_text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    (output / "road_observation_state_bundle_v1.schema.json").write_text(schema_text, encoding="utf-8")
    args.schema_copy.parent.mkdir(parents=True, exist_ok=True)
    args.schema_copy.write_text(schema_text, encoding="utf-8")

    bundle_path = output / "road_observation_state_bundle_c87_oracle.npz"
    history_path = output / "agent3_history_sequence_skeleton.npz"
    build_bundle_from_legacy(
        legacy_path=SOURCE_FILES["road_assimilated_state_v1_payload"],
        output_path=bundle_path,
        expected_legacy_sha256=LOCKED_SOURCE_SHA256["road_assimilated_state_v1_payload"],
        source_sha256=LOCKED_SOURCE_SHA256,
        source_schema_versions=SOURCE_SCHEMA_VERSIONS,
    )
    bundle_errors = validate_bundle(bundle_path)
    if bundle_errors:
        raise ValueError(f"bundle validation failed: {bundle_errors}")
    write_agent3_history_skeleton(bundle_path, history_path)
    packet = agent2_innovation_packet(bundle_path)
    packet_errors = validate_agent2_packet(packet)
    if packet_errors:
        raise ValueError(f"Agent2 packet validation failed: {packet_errors}")
    (output / "agent2_observation_innovation_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_csv(output / "compatibility_matrix.csv", compatibility_rows())
    write_text_assets(output, sha256(bundle_path), sha256(history_path))

    manifest = {
        "package_id": "road-observation-state-bundle-v1-20260724",
        "schema_version": BUNDLE_VERSION,
        "training_run": False,
        "compute": "Mac offline validation",
        "fem_reference": "eta0",
        "source_evidence_class": "oracle",
        "real_road_inversion_pass": False,
        "single_trajectory": True,
        "material_inverse": False,
        "source_files": {key: str(value) for key, value in SOURCE_FILES.items()},
        "source_sha256": LOCKED_SOURCE_SHA256,
        "source_schema_versions": SOURCE_SCHEMA_VERSIONS,
        "source_state_note": "Agent3 contract is hash-locked by content; its source worktree was dirty during handoff construction",
        "consumer_contracts": {
            "agent2": AGENT2_PACKET_VERSION,
            "agent3": AGENT3_SKELETON_VERSION,
        },
        "validation": {"bundle_errors": bundle_errors, "agent2_packet_errors": packet_errors},
        "payload_sha256": {
            bundle_path.name: sha256(bundle_path),
            history_path.name: sha256(history_path),
        },
        "claim_boundary": "interface pass does not imply real-road inversion pass",
    }
    manifest["output_sha256_before_manifest"] = file_hashes(output, exclude={"RUN_MANIFEST.json", "HASHES.sha256"})
    (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = file_hashes(output, exclude={"HASHES.sha256"})
    (output / "HASHES.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()), encoding="utf-8"
    )
    print(json.dumps({
        "output": str(output),
        "bundle_sha256": sha256(bundle_path),
        "history_sha256": sha256(history_path),
        "bundle_errors": bundle_errors,
        "agent2_packet_errors": packet_errors,
    }, indent=2))


if __name__ == "__main__":
    main()
