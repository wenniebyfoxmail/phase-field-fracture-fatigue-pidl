from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from multi_trajectory_forecast_protocol import (  # noqa: E402
    CANONICAL_STATE_FIELDS,
    REQUIRED_TASKS,
    TASK_RESET,
    TASK_SAME_REGIME,
    TASK_TRANSITION,
    FrozenTrajectoryContractRef,
    NormalizedTrajectoryRecord,
    TrajectoryAdapterRegistry,
    TrajectoryContractError,
    assess_readiness,
    build_leave_one_trajectory_out_folds,
)


def record(
    index: int,
    *,
    group: str | None = None,
    tasks: dict[str, bool] | None = None,
    outcome: str = "event",
    uncertainty: str = "calibrated",
) -> NormalizedTrajectoryRecord:
    return NormalizedTrajectoryRecord(
        trajectory_id=f"trajectory_{index}",
        independence_group_id=group or f"physical_{index}",
        independence_scope="within_hard5_factorial_numerical_trajectory",
        bundle_path=f"/producer/trajectory_{index}.npz",
        bundle_sha256=f"{index:064x}",
        bundle_verified=True,
        physics_reference="FEM_eta0",
        fem_eta=0.0,
        graph_signature="registered_common_graph",
        state_fields=CANONICAL_STATE_FIELDS,
        state_count=20,
        observation_contract_id="observation_v1",
        scenario_contract_id="scenario_v1",
        task_coverage=tasks or {task: True for task in REQUIRED_TASKS},
        event_phase_available=True,
        uncertainty_status=uncertainty,
        outcome=outcome,
    )


def frozen_file(path: Path) -> str:
    path.write_text("opaque producer contract", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_contract_blocks_without_guessing_schema() -> None:
    probe = TrajectoryAdapterRegistry().probe(
        FrozenTrajectoryContractRef(None, None, None, None)
    )
    report = assess_readiness(
        probe,
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=False,
        capacity_manifest_verified=False,
    )
    assert probe.status == "blocked_pending_contract"
    assert not report.training_allowed
    assert report.trajectory_count == 0


def test_frozen_unknown_schema_is_not_opened_without_registered_adapter(
    tmp_path: Path,
) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    probe = TrajectoryAdapterRegistry().probe(
        FrozenTrajectoryContractRef(path, digest, "producer_v1", "missing_adapter")
    )
    assert probe.status == "blocked_pending_registered_adapter"
    assert not probe.records


def test_registered_test_adapter_builds_leave_one_entire_trajectory_out(
    tmp_path: Path,
) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [record(1), record(2), record(3)],
    )
    probe = registry.probe(
        FrozenTrajectoryContractRef(path, digest, "test_only_v1", "test_only_adapter")
    )
    report = assess_readiness(
        probe,
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=True,
        capacity_manifest_verified=True,
    )
    assert report.training_allowed
    assert len(report.folds) == 3
    for fold in report.folds:
        assert fold.held_out_independence_group not in fold.training_independence_groups
        assert not set(fold.held_out_trajectory_ids) & set(fold.training_trajectory_ids)


def test_cycles_from_same_physical_trajectory_cannot_fake_generalisation() -> None:
    with pytest.raises(TrajectoryContractError, match="independence group"):
        build_leave_one_trajectory_out_folds(
            [record(1, group="same_physical"), record(2, group="same_physical")]
        )


def test_all_three_tasks_are_required_for_training(tmp_path: Path) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    incomplete = {task: True for task in REQUIRED_TASKS}
    incomplete[TASK_TRANSITION] = False
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [record(1), record(2, tasks=incomplete), record(3)],
    )
    report = assess_readiness(
        registry.probe(
            FrozenTrajectoryContractRef(
                path, digest, "test_only_v1", "test_only_adapter"
            )
        ),
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=True,
        capacity_manifest_verified=True,
    )
    assert report.task_readiness[TASK_SAME_REGIME]
    assert not report.task_readiness[TASK_TRANSITION]
    assert report.task_readiness[TASK_RESET]
    assert not report.training_allowed


def test_missing_reset_task_blocks_formal_training(tmp_path: Path) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    incomplete = {task: True for task in REQUIRED_TASKS}
    incomplete[TASK_RESET] = False
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [record(1), record(2), record(3, tasks=incomplete)],
    )
    report = assess_readiness(
        registry.probe(
            FrozenTrajectoryContractRef(
                path, digest, "test_only_v1", "test_only_adapter"
            )
        ),
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=True,
        capacity_manifest_verified=True,
    )
    assert report.field_training_allowed
    assert report.transition_training_allowed
    assert not report.task_readiness[TASK_RESET]
    assert not report.training_allowed


def test_same_regime_task_does_not_create_a_false_risk_blocker(
    tmp_path: Path,
) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    incomplete = {task: True for task in REQUIRED_TASKS}
    incomplete[TASK_SAME_REGIME] = False
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [
            record(1, tasks=incomplete, outcome="event"),
            record(2, tasks=incomplete, outcome="right_censored"),
            record(3, tasks=incomplete, outcome="event"),
            record(4, tasks=incomplete, outcome="right_censored"),
        ],
    )
    report = assess_readiness(
        registry.probe(
            FrozenTrajectoryContractRef(
                path, digest, "test_only_v1", "test_only_adapter"
            )
        ),
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=True,
        capacity_manifest_verified=True,
    )
    assert not report.training_allowed
    assert report.risk_training_allowed
    assert report.risk_blockers == ()


def test_unverified_bundle_is_rejected_by_normalized_gate(tmp_path: Path) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    registry = TrajectoryAdapterRegistry()
    unverified = record(1)
    unverified = NormalizedTrajectoryRecord(
        **{**unverified.__dict__, "bundle_verified": False}
    )
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [unverified],
    )
    with pytest.raises(TrajectoryContractError, match="verify each bundle"):
        registry.probe(
            FrozenTrajectoryContractRef(
                path, digest, "test_only_v1", "test_only_adapter"
            )
        )


def test_risk_requires_calibration_and_event_censor_diversity(tmp_path: Path) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [
            record(1, outcome="event"),
            record(2, outcome="right_censored"),
            record(3, outcome="event"),
            record(4, outcome="right_censored"),
        ],
    )
    report = assess_readiness(
        registry.probe(
            FrozenTrajectoryContractRef(
                path, digest, "test_only_v1", "test_only_adapter"
            )
        ),
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=True,
        capacity_manifest_verified=True,
    )
    assert report.risk_training_allowed
    assert report.risk_blockers == ()

    registry_missing = TrajectoryAdapterRegistry()
    registry_missing.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [
            record(1, outcome="event"),
            record(2, outcome="event", uncertainty="unavailable"),
            record(3, outcome="event"),
        ],
    )
    missing = assess_readiness(
        registry_missing.probe(
            FrozenTrajectoryContractRef(
                path, digest, "test_only_v1", "test_only_adapter"
            )
        ),
        protocol_id="sealed_test",
        minimum_independent_trajectories=3,
        producer_split_verified=True,
        capacity_manifest_verified=True,
    )
    assert missing.field_training_allowed
    assert not missing.risk_training_allowed
    assert missing.blockers == ()
    assert set(missing.risk_blockers) == {
        "calibrated uncertainty is unavailable on at least one eligible trajectory",
        "every LOTO training fold needs both event and right-censored trajectories",
    }


def test_signed_split_and_exact_factorial_groups_are_hard_gates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "producer.contract"
    digest = frozen_file(path)
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id="test_only_v1",
        adapter_id="test_only_adapter",
        loader=lambda _: [record(1), record(2), record(3), record(4)],
    )
    probe = registry.probe(
        FrozenTrajectoryContractRef(path, digest, "test_only_v1", "test_only_adapter")
    )
    report = assess_readiness(
        probe,
        protocol_id="sealed_test",
        minimum_independent_trajectories=4,
        producer_split_verified=True,
        capacity_manifest_verified=True,
        required_independence_groups=(
            "hard_tip__5step",
            "hard_tip__8step",
            "soft_tip__5step",
            "soft_tip__8step",
        ),
    )
    assert not report.training_allowed
    assert not report.field_training_allowed
    assert any("sealed factorial" in item for item in report.blockers)


def test_contract_hash_mismatch_is_fatal(tmp_path: Path) -> None:
    path = tmp_path / "producer.contract"
    frozen_file(path)
    with pytest.raises(TrajectoryContractError, match="SHA-256"):
        TrajectoryAdapterRegistry().probe(
            FrozenTrajectoryContractRef(path, "0" * 64, "schema", "adapter")
        )


def test_sealed_protocol_forbids_architecture_fishing_and_cycle_leakage() -> None:
    path = (
        ROOT
        / "docs"
        / "multi_trajectory_forecast_protocol_20260729"
        / "sealed_protocol.json"
    )
    protocol = json.loads(path.read_text(encoding="utf-8"))
    assert set(protocol["tasks"]) == set(REQUIRED_TASKS)
    assert protocol["split"]["method"] == "leave-one-entire-trajectory-out"
    assert protocol["split"]["minimum_independent_trajectories"] == 4
    assert protocol["model_matrix"]["formal_baseline"] == "markov"
    assert protocol["model_matrix"]["core_candidate_manifest"] == [
        "markov",
        "tcn",
        "transformer",
    ]
    assert protocol["model_matrix"]["finite_candidates"] == ["tcn", "transformer"]
    assert protocol["model_matrix"]["conditional_reference"] == "diagonal_ssm"
    assert "non-promotable" in protocol["model_matrix"][
        "conditional_reference_policy"
    ]
    assert "any new architecture" in protocol["model_matrix"]["excluded"]
    assert protocol["long_horizon"]["free_rollout_role"] == "stress diagnostic only"
    assert protocol["training_launched"]
    assert protocol["status"] == "completed_within_hard5_factorial_negative_result"


def test_core_manifest_excludes_nonranking_references() -> None:
    package = ROOT / "docs" / "multi_trajectory_forecast_protocol_20260729"
    with (package / "model_matrix.csv").open(newline="", encoding="utf-8") as handle:
        core = list(csv.DictReader(handle))
    assert [row["family"] for row in core] == ["markov", "tcn", "transformer"]
    assert all(row["ranking_eligible"] == "true" for row in core)

    with (package / "nonranking_reference_registry.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        references = {row["family"]: row for row in csv.DictReader(handle)}
    assert references["diagonal_ssm"]["ranking_eligible"] == "false"
    assert references["diagonal_ssm"]["promotable"] == "false"


def test_published_report_lists_explicit_risk_blockers() -> None:
    package = ROOT / "docs" / "multi_trajectory_forecast_protocol_20260729"
    report = json.loads((package / "readiness_report.json").read_text())
    markdown = (package / "readiness_report.md").read_text(encoding="utf-8")
    assert not report["risk_training_allowed"]
    if not report["training_allowed"]:
        assert any("readiness" in item for item in report["risk_blockers"])
    assert any("calibrated uncertainty" in item for item in report["risk_blockers"])
    assert any("event and right-censored" in item for item in report["risk_blockers"])
    assert "## Hazard/RUL blockers\n\n- none" not in markdown
