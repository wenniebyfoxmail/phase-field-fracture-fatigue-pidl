"""Reviewed adapter for Agent2's signed FEM factorial trajectory contract.

This adapter consumes only the four controlled hard/soft x 5/8-step bundles.
The three Umax sensitivity bundles in the same producer package are deliberately
excluded from the LOCO inventory and cannot inflate the trajectory count.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from multi_trajectory_forecast_protocol import (
    CANONICAL_STATE_FIELDS,
    REQUIRED_TASKS,
    NormalizedTrajectoryRecord,
    TrajectoryContractError,
    sha256_file,
)


AGENT2_COMMIT = "90cf8a3703d03609ad7daf066d04ab051c2f7500"
SCHEMA_ID = "fem_multitrajectory_contract_v1"
ADAPTER_ID = "agent2_factorial_loco_v1"
EXPECTED_CONTRACT_SCHEMA_SHA256 = (
    "43bdb37104015a765402837928c772079ef0a760c96180cc8b5deb7e6fa99bd4"
)
EXPECTED_LOCO_LOCK_SHA256 = (
    "5904af500cde315d8ee9f9087d3f5088c03b59b76cf23f8fbf7b80f6c3fb1691"
)
EXPECTED_GROUPS = {
    "factorial_hard_5step_u012": "hard_tip__5step",
    "factorial_hard_8step_u012": "hard_tip__8step",
    "factorial_soft_5step_u012": "soft_tip__5step",
    "factorial_soft_8step_u012": "soft_tip__8step",
}


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _verify_embedded_hash(
    value: Mapping[str, Any], hash_key: str, expected: str | None = None
) -> str:
    declared = str(value.get(hash_key, ""))
    unhashed = dict(value)
    unhashed.pop(hash_key, None)
    actual = canonical_json_sha256(unhashed)
    if declared != actual:
        raise TrajectoryContractError(f"embedded {hash_key} does not verify")
    if expected is not None and declared != expected:
        raise TrajectoryContractError(
            f"embedded {hash_key} differs from the frozen Agent2 lock"
        )
    return declared


def _verify_package_hashes(package: Path) -> None:
    hash_file = package / "HASHES.sha256"
    if not hash_file.is_file():
        raise TrajectoryContractError("Agent2 package HASHES.sha256 is missing")
    for line in hash_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            expected, relative = line.split(maxsplit=1)
        except ValueError as exc:
            raise TrajectoryContractError("malformed Agent2 package hash line") from exc
        asset = package / relative.lstrip("* ")
        if not asset.is_file() or sha256_file(asset) != expected:
            raise TrajectoryContractError(
                f"Agent2 package asset hash mismatch: {relative}"
            )


def _validate_split(package: Path, trajectory_ids: set[str]) -> None:
    path = package / "within_hard5_factorial_loco_split_lock_v1.json"
    split = json.loads(path.read_text(encoding="utf-8"))
    _verify_embedded_hash(split, "lock_sha256", EXPECTED_LOCO_LOCK_SHA256)
    if split.get("status") != "ready" or not split.get("training_launch_allowed"):
        raise TrajectoryContractError("Agent2 factorial LOCO split is not launch-ready")
    if set(split.get("available_independent_trajectory_ids", ())) != trajectory_ids:
        raise TrajectoryContractError("LOCO split trajectory inventory drifted")
    guards = split.get("leakage_guards", {})
    expected_guards = {
        "split_unit": "trajectory_id",
        "cycle_level_random_split": False,
        "node_level_random_split": False,
        "future_state_in_features": False,
        "event_cycle_as_feature": False,
        "c69_legacy_allowed": False,
        "duplicate_configuration_across_folds": False,
    }
    if any(guards.get(key) != value for key, value in expected_guards.items()):
        raise TrajectoryContractError("LOCO leakage guard differs from sealed policy")
    folds = split.get("folds", ())
    if len(folds) != len(trajectory_ids):
        raise TrajectoryContractError("LOCO split must contain four folds")
    seen_test: set[str] = set()
    for fold in folds:
        train = set(fold.get("train_trajectory_ids", ()))
        test = set(fold.get("test_trajectory_ids", ()))
        if len(test) != 1 or train | test != trajectory_ids or train & test:
            raise TrajectoryContractError("LOCO fold crosses a trajectory boundary")
        if not all(
            fold.get(key) is True
            for key in (
                "cycle_split_forbidden",
                "node_split_forbidden",
                "window_crossing_forbidden",
            )
        ):
            raise TrajectoryContractError("LOCO fold lacks a hard leakage guard")
        seen_test.update(test)
    if seen_test != trajectory_ids:
        raise TrajectoryContractError("each trajectory must be held out exactly once")


def load_agent2_factorial_loco_contract(
    contract_manifest_path: Path,
) -> Sequence[NormalizedTrajectoryRecord]:
    """Load and verify the exact four-trajectory Agent2 consumer inventory."""
    contract_manifest_path = Path(contract_manifest_path)
    package = contract_manifest_path.parent
    manifest = json.loads(contract_manifest_path.read_text(encoding="utf-8"))
    _verify_package_hashes(package)
    if manifest.get("contract_sha256") != EXPECTED_CONTRACT_SCHEMA_SHA256:
        raise TrajectoryContractError("Agent2 contract schema hash drifted")
    if manifest.get("factorial_split_lock_sha256") != EXPECTED_LOCO_LOCK_SHA256:
        raise TrajectoryContractError("Agent2 manifest points to a different LOCO lock")
    if manifest.get("controlled_factorial_combination_count") != 4:
        raise TrajectoryContractError("expected exactly four factorial combinations")
    if manifest.get("factorial_split_status") != "ready":
        raise TrajectoryContractError("factorial split is not marked ready")
    if not manifest.get("scoped_factorial_training_launch_allowed"):
        raise TrajectoryContractError("scoped factorial producer gate is closed")

    bundle_hashes = manifest.get("bundle_manifest_hashes", {})
    records: list[NormalizedTrajectoryRecord] = []
    for trajectory_id, group_id in sorted(EXPECTED_GROUPS.items()):
        bundle_path = package / "bundles" / f"{trajectory_id}.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        internal_hash = _verify_embedded_hash(bundle, "manifest_sha256")
        if internal_hash != bundle_hashes.get(trajectory_id):
            raise TrajectoryContractError(
                f"bundle manifest hash drifted for {trajectory_id}"
            )
        if bundle.get("trajectory_id") != trajectory_id:
            raise TrajectoryContractError("bundle filename/trajectory id mismatch")
        if bundle.get("schema_version") != "fem_trajectory_bundle_v1":
            raise TrajectoryContractError("unsupported Agent2 bundle schema")
        if bundle.get("independence_class") != "controlled_factorial_combination":
            raise TrajectoryContractError("non-factorial bundle entered LOCO inventory")
        if bundle.get("claim_scope") != "shared_geometry_within_hard5_factorial_only":
            raise TrajectoryContractError("bundle claim scope exceeds sealed boundary")
        physics = bundle.get("physics", {})
        if float(physics.get("eta", float("nan"))) != 0.0:
            raise TrajectoryContractError("FEM eta0 is required")
        states = bundle.get("states", ())
        cycles = [int(item.get("cycle", -1)) for item in states]
        if cycles != list(range(1, len(states) + 1)):
            raise TrajectoryContractError("bundle cycles must be contiguous from c1")
        first_hit = int(bundle.get("event", {}).get("first_hit", {}).get("cycle", -1))
        confirmed = int(bundle.get("event", {}).get("confirmed", {}).get("cycle", -1))
        if first_hit < 4 or confirmed < first_hit or confirmed > len(states):
            raise TrajectoryContractError("event cycles do not support sealed tasks")
        semantics = bundle.get("state_semantics", {})
        if (
            semantics.get("state_id") != "cycle_peak_coherent_v1"
            or not semantics.get("all_fields_same_cycle_and_phase")
        ):
            raise TrajectoryContractError("mixed-phase state bundle is forbidden")
        records.append(
            NormalizedTrajectoryRecord(
                trajectory_id=trajectory_id,
                independence_group_id=group_id,
                independence_scope="within_hard5_factorial_numerical_trajectory",
                bundle_path=str(bundle_path),
                bundle_sha256=sha256_file(bundle_path),
                bundle_verified=True,
                physics_reference="FEM_eta0_cycle_peak",
                fem_eta=0.0,
                graph_signature=str(bundle.get("mesh", {}).get("content_sha256", "")),
                state_fields=CANONICAL_STATE_FIELDS,
                state_count=len(states),
                observation_contract_id="synthetic_oracle_fem_state_v1",
                scenario_contract_id="hard5_known_loading_schedule_v1",
                task_coverage={task: True for task in REQUIRED_TASKS},
                event_phase_available=True,
                uncertainty_status="unavailable",
                outcome="event",
            )
        )
    _validate_split(package, set(EXPECTED_GROUPS))
    if len({record.graph_signature for record in records}) != 1:
        raise TrajectoryContractError("factorial bundles do not share one mesh")
    return records

