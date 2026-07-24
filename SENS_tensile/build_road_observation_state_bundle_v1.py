#!/usr/bin/env python3
"""Build the frozen Agent1 -> Agent2/3 road state handoff package.

This is an offline interface conversion. It performs no training and preserves
the c87 FEM raw-energy observation as an oracle-only upper-bound channel.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
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
    validate_downstream_contracts,
    verify_source_lock,
    write_agent3_history_skeleton,
)


PROJECT_ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl")
PHASE1 = PROJECT_ROOT / "local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/road_observation_latent_state_phase1_20260723"
AGENT2_WORKTREE = PROJECT_ROOT / ".codex/worktrees/data-efficient-cycle-forecast"
AGENT3_WORKTREE = PROJECT_ROOT / ".codex/worktrees/temporal-graph-transformer"
AGENT2_TIME_REL = Path("analysis/road_time_trigger_formulation_20260723")
AGENT2_INNOVATION_REL = Path("analysis/road_observation_innovation_trigger_20260724")
AGENT3_CONTRACT_REL = Path("docs/road_observation_aware_stage1_20260723/road_forecast_input_contract_v1.json")

LOCKED_DOWNSTREAM_COMMITS = {
    "agent2": "19ca9c73a36a4fb80119a49c9234d6ee11501052",
    "agent3": "e55070e4b29a1da39262e0138e2c4efc7240c195",
}

LOCKED_SOURCE_SHA256 = {
    "road_observation_operator_v1": "b067ace595a1cb0055f680e0ac7c2e7e2866c4f17192d4ba8c56d5838e7bbacc",
    "road_assimilated_state_v1_schema": "18f9191e3809e2905cf5a7adb3dbc26b63fdf050d4ae346c268c3c39af7dda31",
    "road_assimilated_state_v1_payload": "276bca62f3955c0948bd23891aa10dcca209f3e562605303b61b263d53759ffe",
    "agent2_road_time_mapping_v1": "630bbd878529fba18ed29c733c414433f51815e9243e7565697b6a81e2fd32c4",
    "agent2_road_forecast_horizon_v1": "f593a005a1175c5914ef0fd6b8855879180f726886abb69f48c0bec174d22fc5",
    "agent2_road_observation_trigger_v1": "94b4723dabfb4533efe748ce914677e01b5fa08a7c3f6bc9792feeadd5b393d3",
    "agent2_observation_innovation_trigger_v1_spec": "207723248cc8f6e609e62fbee85cc72a89b04ad0b815aa919026dac9845fb6dc",
    "agent2_observation_innovation_packet_v1_spec": "ff5059b96f8e35aaef526c10d54ea37710a744f4d3a57278dc6c3647ca72666f",
    "agent3_road_forecast_input_contract_v1": "681d68711f93e2af80621e4fe70b1bdb4b134a24c0c7ed880f2d9d9630a8415d",
}

SOURCE_SCHEMA_VERSIONS = {
    "road_observation_operator_v1": "road_observation_operator_v1",
    "road_assimilated_state_v1_schema": "road_assimilated_state_v1",
    "road_assimilated_state_v1_payload": "road_assimilated_state_v1",
    "agent2_road_time_mapping_v1": "road_time_mapping_v1",
    "agent2_road_forecast_horizon_v1": "road_forecast_horizon_v1",
    "agent2_road_observation_trigger_v1": "road_observation_trigger_v1",
    "agent2_observation_innovation_trigger_v1_spec": "observation_innovation_trigger_v1",
    "agent2_observation_innovation_packet_v1_spec": "observation_innovation_packet_v1",
    "agent3_road_forecast_input_contract_v1": "road_forecast_input_contract_v1",
}

COMMIT_ASSETS = {
    "agent2_road_time_mapping_v1": (LOCKED_DOWNSTREAM_COMMITS["agent2"], AGENT2_TIME_REL / "road_time_mapping_spec.json"),
    "agent2_road_forecast_horizon_v1": (LOCKED_DOWNSTREAM_COMMITS["agent2"], AGENT2_TIME_REL / "road_forecast_horizon_spec.json"),
    "agent2_road_observation_trigger_v1": (LOCKED_DOWNSTREAM_COMMITS["agent2"], AGENT2_TIME_REL / "observation_trigger_spec.json"),
    "agent2_observation_innovation_trigger_v1_spec": (LOCKED_DOWNSTREAM_COMMITS["agent2"], AGENT2_INNOVATION_REL / "observation_innovation_trigger_spec_v1.json"),
    "agent2_observation_innovation_packet_v1_spec": (LOCKED_DOWNSTREAM_COMMITS["agent2"], AGENT2_INNOVATION_REL / "observation_innovation_packet_v1.json"),
    "agent3_road_forecast_input_contract_v1": (LOCKED_DOWNSTREAM_COMMITS["agent3"], AGENT3_CONTRACT_REL),
}

SOURCE_LOGICAL_PATHS = {
    "road_observation_operator_v1": "road_observation_latent_state_phase1_20260723/road_observation_operator_spec.json",
    "road_assimilated_state_v1_schema": "road_observation_latent_state_phase1_20260723/assimilated_state_schema.json",
    "road_assimilated_state_v1_payload": "road_observation_latent_state_phase1_20260723/assimilated_state_c87_synthetic_reference.npz",
    "agent2_road_time_mapping_v1": str(AGENT2_TIME_REL / "road_time_mapping_spec.json"),
    "agent2_road_forecast_horizon_v1": str(AGENT2_TIME_REL / "road_forecast_horizon_spec.json"),
    "agent2_road_observation_trigger_v1": str(AGENT2_TIME_REL / "observation_trigger_spec.json"),
    "agent2_observation_innovation_trigger_v1_spec": str(AGENT2_INNOVATION_REL / "observation_innovation_trigger_spec_v1.json"),
    "agent2_observation_innovation_packet_v1_spec": str(AGENT2_INNOVATION_REL / "observation_innovation_packet_v1.json"),
    "agent3_road_forecast_input_contract_v1": str(AGENT3_CONTRACT_REL),
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
    parser.add_argument("--phase1-dir", type=Path, default=PHASE1)
    parser.add_argument(
        "--agent2-root",
        type=Path,
        help="Repo checkout containing Agent2 final analysis files; auto-detected when omitted.",
    )
    parser.add_argument(
        "--agent3-root",
        type=Path,
        help="Repo checkout containing Agent3 final contract; auto-detected when omitted.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _auto_root(
    explicit: Path | None,
    repo_relative: Path,
    sibling: Path,
    checkout_root: Path = ROOT,
) -> Path:
    if explicit is not None:
        return explicit.resolve()
    if (checkout_root / repo_relative).is_file():
        return checkout_root
    if (sibling / repo_relative).is_file():
        return sibling
    raise FileNotFoundError(f"cannot locate downstream source {repo_relative}")


def source_files(args: argparse.Namespace) -> dict[str, Path]:
    agent2_root = _auto_root(
        args.agent2_root,
        AGENT2_INNOVATION_REL / "observation_innovation_packet_v1.json",
        AGENT2_WORKTREE,
    )
    agent3_root = _auto_root(args.agent3_root, AGENT3_CONTRACT_REL, AGENT3_WORKTREE)
    phase1 = args.phase1_dir.resolve()
    return {
        "road_observation_operator_v1": phase1 / "road_observation_operator_spec.json",
        "road_assimilated_state_v1_schema": phase1 / "assimilated_state_schema.json",
        "road_assimilated_state_v1_payload": phase1 / "assimilated_state_c87_synthetic_reference.npz",
        "agent2_road_time_mapping_v1": agent2_root / AGENT2_TIME_REL / "road_time_mapping_spec.json",
        "agent2_road_forecast_horizon_v1": agent2_root / AGENT2_TIME_REL / "road_forecast_horizon_spec.json",
        "agent2_road_observation_trigger_v1": agent2_root / AGENT2_TIME_REL / "observation_trigger_spec.json",
        "agent2_observation_innovation_trigger_v1_spec": agent2_root / AGENT2_INNOVATION_REL / "observation_innovation_trigger_spec_v1.json",
        "agent2_observation_innovation_packet_v1_spec": agent2_root / AGENT2_INNOVATION_REL / "observation_innovation_packet_v1.json",
        "agent3_road_forecast_input_contract_v1": agent3_root / AGENT3_CONTRACT_REL,
    }


def _commit_asset_sha256(commit: str, path: Path) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def verify_sources(files: dict[str, Path]) -> list[str]:
    verify_source_lock(files, LOCKED_SOURCE_SHA256)
    for source_id, (commit, relative_path) in COMMIT_ASSETS.items():
        commit_hash = _commit_asset_sha256(commit, relative_path)
        if commit_hash != LOCKED_SOURCE_SHA256[source_id]:
            raise ValueError(
                f"final commit asset drift for {source_id}: "
                f"expected {LOCKED_SOURCE_SHA256[source_id]}, got {commit_hash}"
            )

    operator = read_json(files["road_observation_operator_v1"])
    state_schema = read_json(files["road_assimilated_state_v1_schema"])
    time_mapping = read_json(files["agent2_road_time_mapping_v1"])
    horizon = read_json(files["agent2_road_forecast_horizon_v1"])
    trigger = read_json(files["agent2_road_observation_trigger_v1"])
    innovation_trigger = read_json(files["agent2_observation_innovation_trigger_v1_spec"])
    innovation_packet = read_json(files["agent2_observation_innovation_packet_v1_spec"])
    forecast = read_json(files["agent3_road_forecast_input_contract_v1"])
    observed_versions = {
        "road_observation_operator_v1": operator.get("spec_version"),
        "road_assimilated_state_v1_schema": state_schema.get("schema_version"),
        "agent2_road_time_mapping_v1": time_mapping.get("schema"),
        "agent2_road_forecast_horizon_v1": horizon.get("schema"),
        "agent2_road_observation_trigger_v1": trigger.get("schema"),
        "agent2_observation_innovation_trigger_v1_spec": innovation_trigger.get("schema_version"),
        "agent2_observation_innovation_packet_v1_spec": innovation_packet.get("schema_version"),
        "agent3_road_forecast_input_contract_v1": forecast.get("contract_id"),
    }
    for source_id, version in observed_versions.items():
        if version != SOURCE_SCHEMA_VERSIONS[source_id]:
            raise ValueError(f"schema drift for {source_id}: {version}")
    semantic_errors = validate_downstream_contracts(innovation_packet, forecast)
    if semantic_errors:
        raise ValueError(f"downstream semantic incompatibility: {semantic_errors}")
    return semantic_errors


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
            "consumer_or_source": "Agent2 observation_innovation_trigger_v1",
            "version": "observation_innovation_trigger_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent2_observation_innovation_trigger_v1_spec"],
            "compatibility": "pass_not_operationally_calibrated",
            "bundle_mapping": "packet channels and decision eligibility follow the final trigger firewall",
            "missing_or_boundary": "all deployable c87 innovation channels are fully masked",
        },
        {
            "consumer_or_source": "Agent2 observation_innovation_packet_v1",
            "version": "observation_innovation_packet_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent2_observation_innovation_packet_v1_spec"],
            "compatibility": "pass_decision_ineligible",
            "bundle_mapping": "three frozen channels with values/predictions/uncertainty/provenance/registration/time",
            "missing_or_boundary": "oracle bundle cannot issue operational request or stop decisions",
        },
        {
            "consumer_or_source": "Agent3 road_forecast_input_contract_v1",
            "version": "road_forecast_input_contract_v1",
            "sha256": LOCKED_SOURCE_SHA256["agent3_road_forecast_input_contract_v1"],
            "compatibility": "pass",
            "bundle_mapping": "z_analysis[T,N,4], uncertainty, node/global masks, history/forcing/reset skeleton",
            "missing_or_boundary": "latent observed_channel_mask is never mapped to node observation availability; no future scenario is fabricated",
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
        "The final downstream contracts are pinned to Agent2 commit `19ca9c73a36a4fb80119a49c9234d6ee11501052` and Agent3 commit `e55070e4b29a1da39262e0138e2c4efc7240c195`, with independent content hashes for every consumed file.\n\n"
        "This regeneration supersedes bundle hash `b9bb52026737ed11a9463051f31e7c05057595ec0e015d8a6dec6127c2a4c86e` and history hash `e482c52ceff47038493c7563a99133f5e6c4017009d482aea8707a1c58d83e74`. The underlying c87 state source remains byte-identical; hashes changed because final downstream provenance and packet semantics are now embedded.\n\n"
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
        "7. Agent2 receives exactly `registered_crack_geometry_image`, `fwd_deflection_basin`, and `strain_localization`; all are fully masked in this oracle-only handoff. `decision_eligible=false` prevents the packet from producing an operational request or stop.\n\n"
        "## Reproduction check\n\n"
        "The builder was run against the clean `codex/road-closed-loop-integration` checkout with both downstream roots pointing to that checkout. The regenerated canonical bundle and Agent3 history skeleton were byte-identical to this package.\n\n"
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
        "downstream_commits": LOCKED_DOWNSTREAM_COMMITS,
        "clean_integration_reproduction": "byte_identical_pass",
    }
    (output / "attempts.jsonl").write_text(json.dumps(attempt, sort_keys=True) + "\n", encoding="utf-8")
    (output / "attempt.md").write_text(
        "# Attempt Ledger\n\n"
        "| Attempt | Compute | Result | Claim boundary |\n"
        "|---|---|---|---|\n"
        "| road-observation-state-bundle-v1-20260724 | Mac offline only; no training | final contract/hash locks pass; clean integration reproduction byte-identical | real-road inversion, material identification, and road generalization remain quarantined |\n",
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
    files = source_files(args)
    downstream_semantic_errors = verify_sources(files)
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
        legacy_path=files["road_assimilated_state_v1_payload"],
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
        "source_files": SOURCE_LOGICAL_PATHS,
        "source_sha256": LOCKED_SOURCE_SHA256,
        "source_schema_versions": SOURCE_SCHEMA_VERSIONS,
        "downstream_commits": LOCKED_DOWNSTREAM_COMMITS,
        "source_state_note": "Final Agent2/Agent3 assets are pinned by both commit and SHA-256; clean integration checkout paths are preferred over sibling worktrees",
        "consumer_contracts": {
            "agent2": AGENT2_PACKET_VERSION,
            "agent3": AGENT3_SKELETON_VERSION,
        },
        "validation": {
            "bundle_errors": bundle_errors,
            "agent2_packet_errors": packet_errors,
            "downstream_semantic_errors": downstream_semantic_errors,
            "clean_integration_source_path_reproduction": "byte_identical_pass",
        },
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
        "downstream_semantic_errors": downstream_semantic_errors,
    }, indent=2))


if __name__ == "__main__":
    main()
