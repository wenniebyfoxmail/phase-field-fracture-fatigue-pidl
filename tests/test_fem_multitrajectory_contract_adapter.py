from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_multitrajectory_contract_adapter import (  # noqa: E402
    ADAPTER_ID,
    EXPECTED_GROUPS,
    SCHEMA_ID,
    load_agent2_factorial_loco_contract,
)
from multi_trajectory_forecast_protocol import (  # noqa: E402
    FrozenTrajectoryContractRef,
    TrajectoryAdapterRegistry,
    TrajectoryContractError,
    assess_readiness,
)
sys.path.insert(0, str(ROOT / "SENS_tensile"))
from train_factorial_loco_temporal_operator import event_hit  # noqa: E402


PACKAGE = ROOT / "analysis" / "fem_multitrajectory_contract_20260729"
MANIFEST = PACKAGE / "RUN_MANIFEST.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_signed_agent2_contract_loads_only_four_factorial_trajectories() -> None:
    records = load_agent2_factorial_loco_contract(MANIFEST)
    assert {record.trajectory_id for record in records} == set(EXPECTED_GROUPS)
    assert {record.independence_group_id for record in records} == set(
        EXPECTED_GROUPS.values()
    )
    assert sum(record.state_count for record in records) == 348
    assert all(record.outcome == "event" for record in records)
    assert all(record.uncertainty_status == "unavailable" for record in records)


def test_signed_contract_passes_fields_but_keeps_risk_blocked() -> None:
    registry = TrajectoryAdapterRegistry()
    registry.register(
        schema_id=SCHEMA_ID,
        adapter_id=ADAPTER_ID,
        loader=load_agent2_factorial_loco_contract,
    )
    probe = registry.probe(
        FrozenTrajectoryContractRef(MANIFEST, file_sha(MANIFEST), SCHEMA_ID, ADAPTER_ID)
    )
    report = assess_readiness(
        probe,
        protocol_id="test",
        minimum_independent_trajectories=4,
        producer_split_verified=True,
        capacity_manifest_verified=True,
        required_independence_groups=tuple(EXPECTED_GROUPS.values()),
    )
    assert report.training_allowed
    assert report.field_training_allowed
    assert report.transition_training_allowed
    assert not report.risk_training_allowed
    assert any("right-censored" in item for item in report.risk_blockers)
    assert any("calibrated uncertainty" in item for item in report.risk_blockers)


def test_split_tampering_is_fatal(tmp_path: Path) -> None:
    clone = tmp_path / "contract"
    clone.mkdir()
    (clone / "bundles").mkdir()
    for path in PACKAGE.glob("*.json"):
        (clone / path.name).write_bytes(path.read_bytes())
    for path in (PACKAGE / "bundles").glob("factorial_*.json"):
        (clone / "bundles" / path.name).write_bytes(path.read_bytes())
    split_path = clone / "within_hard5_factorial_loco_split_lock_v1.json"
    split = json.loads(split_path.read_text())
    split["leakage_guards"]["cycle_level_random_split"] = True
    split_path.write_text(json.dumps(split), encoding="utf-8")
    lines = []
    for source_line in (PACKAGE / "HASHES.sha256").read_text().splitlines():
        digest, relative = source_line.split(maxsplit=1)
        asset = clone / relative.lstrip("* ")
        if not asset.exists():
            continue
        if asset == split_path:
            digest = file_sha(asset)
        lines.append(f"{digest}  {relative.lstrip('* ')}")
    (clone / "HASHES.sha256").write_text("\n".join(lines) + "\n")
    with pytest.raises(TrajectoryContractError):
        load_agent2_factorial_loco_contract(clone / "RUN_MANIFEST.json")


def test_transition_warning_uses_physical_right_boundary_criterion() -> None:
    centroids = np.asarray([[0.49, 0.0], [0.49, 0.1], [0.49, -0.1], [0.1, 0.0]])
    state = np.zeros((4, 4), dtype=np.float32)
    state[:2, 0] = 0.99
    assert not event_hit(state, centroids)
    state[2, 0] = 0.95
    assert event_hit(state, centroids)
