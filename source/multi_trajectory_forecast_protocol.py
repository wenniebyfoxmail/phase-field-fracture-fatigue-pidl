"""Sealed multi-trajectory forecast protocol and readiness gates.

The producer trajectory schema is intentionally not defined here. A versioned
adapter can be registered only after the Agent/FEM producer publishes a frozen
contract and hash. Until then, the framework reports a hard readiness block.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Callable, Mapping, Sequence


TASK_SAME_REGIME = "observed_state_same_regime_h1_h3"
TASK_TRANSITION = "autonomous_transition_warning"
TASK_RESET = "observation_reset_conditional_propagation"
REQUIRED_TASKS = (TASK_SAME_REGIME, TASK_TRANSITION, TASK_RESET)

CANONICAL_STATE_FIELDS = (
    "damage",
    "fatigue_history",
    "fatigue_degradation",
    "log10_psi_raw",
)
ALLOWED_OUTCOMES = {"event", "right_censored", "unknown"}
ALLOWED_UNCERTAINTY = {
    "calibrated",
    "eligible_calibrated",
    "uncalibrated",
    "uncalibrated_not_available",
    "unavailable",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TrajectoryContractError(ValueError):
    """The producer contract or normalized inventory violates the sealed gate."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class FrozenTrajectoryContractRef:
    """Opaque producer reference that remains unread until an adapter exists."""

    path: Path | None
    expected_sha256: str | None
    schema_id: str | None
    adapter_id: str | None


@dataclass(frozen=True)
class NormalizedTrajectoryRecord:
    """Agent 3 internal inventory emitted by a producer-specific adapter."""

    trajectory_id: str
    independence_group_id: str
    independence_scope: str
    bundle_path: str
    bundle_sha256: str
    bundle_verified: bool
    physics_reference: str
    fem_eta: float
    graph_signature: str
    state_fields: tuple[str, ...]
    state_count: int
    observation_contract_id: str
    scenario_contract_id: str
    task_coverage: Mapping[str, bool]
    event_phase_available: bool
    uncertainty_status: str
    outcome: str


@dataclass(frozen=True)
class ContractProbe:
    status: str
    contract_path: str | None
    contract_sha256: str | None
    schema_id: str | None
    adapter_id: str | None
    records: tuple[NormalizedTrajectoryRecord, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class LeaveOneTrajectoryOutFold:
    fold_id: str
    held_out_independence_group: str
    held_out_trajectory_ids: tuple[str, ...]
    training_independence_groups: tuple[str, ...]
    training_trajectory_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessReport:
    protocol_id: str
    status: str
    contract_status: str
    contract_sha256: str | None
    trajectory_count: int
    independence_group_count: int
    independence_scopes: tuple[str, ...]
    task_readiness: Mapping[str, bool]
    folds: tuple[LeaveOneTrajectoryOutFold, ...]
    field_training_allowed: bool
    transition_training_allowed: bool
    risk_training_allowed: bool
    training_allowed: bool
    blockers: tuple[str, ...]
    risk_blockers: tuple[str, ...]
    claims_allowed: tuple[str, ...]
    claims_forbidden: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


AdapterLoader = Callable[[Path], Sequence[NormalizedTrajectoryRecord]]


@dataclass(frozen=True)
class _AdapterRegistration:
    schema_id: str
    adapter_id: str
    loader: AdapterLoader


class TrajectoryAdapterRegistry:
    """Registry that prevents Agent 3 from guessing an unfinished schema."""

    def __init__(self) -> None:
        self._registrations: dict[str, _AdapterRegistration] = {}

    def register(
        self,
        *,
        schema_id: str,
        adapter_id: str,
        loader: AdapterLoader,
    ) -> None:
        if not schema_id or not adapter_id:
            raise ValueError("schema_id and adapter_id must be non-empty")
        if adapter_id in self._registrations:
            raise ValueError(f"adapter {adapter_id!r} is already registered")
        self._registrations[adapter_id] = _AdapterRegistration(
            schema_id=schema_id,
            adapter_id=adapter_id,
            loader=loader,
        )

    def probe(self, reference: FrozenTrajectoryContractRef) -> ContractProbe:
        if reference.path is None:
            return ContractProbe(
                status="blocked_pending_contract",
                contract_path=None,
                contract_sha256=None,
                schema_id=reference.schema_id,
                adapter_id=reference.adapter_id,
                records=(),
                blockers=("Agent/FEM task 2 trajectory contract is not published",),
            )
        path = Path(reference.path)
        if not path.is_file():
            return ContractProbe(
                status="blocked_contract_missing",
                contract_path=str(path),
                contract_sha256=None,
                schema_id=reference.schema_id,
                adapter_id=reference.adapter_id,
                records=(),
                blockers=("producer contract path is missing or is not a file",),
            )
        if not reference.expected_sha256 or not SHA256_PATTERN.fullmatch(
            reference.expected_sha256
        ):
            return ContractProbe(
                status="blocked_contract_hash_unfrozen",
                contract_path=str(path),
                contract_sha256=None,
                schema_id=reference.schema_id,
                adapter_id=reference.adapter_id,
                records=(),
                blockers=("producer contract SHA-256 is not frozen",),
            )
        actual_sha256 = sha256_file(path)
        if actual_sha256 != reference.expected_sha256:
            raise TrajectoryContractError(
                "producer contract SHA-256 differs from the frozen reference"
            )
        if not reference.schema_id or not reference.adapter_id:
            return ContractProbe(
                status="blocked_schema_adapter_unfrozen",
                contract_path=str(path),
                contract_sha256=actual_sha256,
                schema_id=reference.schema_id,
                adapter_id=reference.adapter_id,
                records=(),
                blockers=("producer schema_id and adapter_id are not frozen",),
            )
        registration = self._registrations.get(reference.adapter_id)
        if registration is None:
            return ContractProbe(
                status="blocked_pending_registered_adapter",
                contract_path=str(path),
                contract_sha256=actual_sha256,
                schema_id=reference.schema_id,
                adapter_id=reference.adapter_id,
                records=(),
                blockers=(
                    "no reviewed Agent 3 adapter is registered for the "
                    "producer contract",
                ),
            )
        if registration.schema_id != reference.schema_id:
            raise TrajectoryContractError(
                "registered adapter schema differs from the frozen producer schema"
            )
        records = tuple(registration.loader(path))
        validate_normalized_records(records)
        return ContractProbe(
            status="contract_loaded",
            contract_path=str(path),
            contract_sha256=actual_sha256,
            schema_id=reference.schema_id,
            adapter_id=reference.adapter_id,
            records=records,
            blockers=(),
        )


def validate_normalized_records(
    records: Sequence[NormalizedTrajectoryRecord],
) -> None:
    """Validate Agent 3 normalized values without assuming producer field names."""
    seen_trajectories: set[str] = set()
    seen_groups: set[str] = set()
    seen_hashes: set[str] = set()
    for record in records:
        if (
            not record.trajectory_id
            or not record.independence_group_id
            or not record.independence_scope
        ):
            raise TrajectoryContractError(
                "trajectory id, independence group and scope must be non-empty"
            )
        if record.trajectory_id in seen_trajectories:
            raise TrajectoryContractError("trajectory_id must be unique")
        if record.independence_group_id in seen_groups:
            raise TrajectoryContractError(
                "one normalized record is required per trajectory independence group"
            )
        if not SHA256_PATTERN.fullmatch(record.bundle_sha256):
            raise TrajectoryContractError("bundle SHA-256 is invalid")
        if not record.bundle_path or not record.bundle_verified:
            raise TrajectoryContractError(
                "the producer adapter must verify each bundle path and SHA-256"
            )
        if record.bundle_sha256 in seen_hashes:
            raise TrajectoryContractError(
                "the same bundle cannot count as multiple independent trajectories"
            )
        if record.state_fields != CANONICAL_STATE_FIELDS:
            raise TrajectoryContractError(
                "normalized state registry differs from the sealed canonical fields"
            )
        if record.state_count < 4:
            raise TrajectoryContractError(
                "a trajectory needs at least one origin plus h1-h3 targets"
            )
        if abs(float(record.fem_eta)) > 1.0e-15:
            raise TrajectoryContractError("FEM eta0 is the required physical reference")
        if not record.physics_reference or not record.graph_signature:
            raise TrajectoryContractError("physics and graph provenance are required")
        if not record.observation_contract_id or not record.scenario_contract_id:
            raise TrajectoryContractError(
                "observation and scenario contracts must be explicit"
            )
        if set(record.task_coverage) != set(REQUIRED_TASKS):
            raise TrajectoryContractError(
                "task coverage must declare exactly the three sealed tasks"
            )
        if record.task_coverage[TASK_TRANSITION] and not record.event_phase_available:
            raise TrajectoryContractError(
                "transition-warning coverage requires a producer event phase"
            )
        if record.uncertainty_status not in ALLOWED_UNCERTAINTY:
            raise TrajectoryContractError("unknown uncertainty status")
        if record.outcome not in ALLOWED_OUTCOMES:
            raise TrajectoryContractError("unknown event/censor outcome")
        seen_trajectories.add(record.trajectory_id)
        seen_groups.add(record.independence_group_id)
        seen_hashes.add(record.bundle_sha256)


def build_leave_one_trajectory_out_folds(
    records: Sequence[NormalizedTrajectoryRecord],
) -> tuple[LeaveOneTrajectoryOutFold, ...]:
    validate_normalized_records(records)
    ordered = sorted(records, key=lambda item: item.independence_group_id)
    folds: list[LeaveOneTrajectoryOutFold] = []
    for held_out in ordered:
        training = [
            record
            for record in ordered
            if record.independence_group_id != held_out.independence_group_id
        ]
        folds.append(
            LeaveOneTrajectoryOutFold(
                fold_id=f"loto__{held_out.independence_group_id}",
                held_out_independence_group=held_out.independence_group_id,
                held_out_trajectory_ids=(held_out.trajectory_id,),
                training_independence_groups=tuple(
                    record.independence_group_id for record in training
                ),
                training_trajectory_ids=tuple(
                    record.trajectory_id for record in training
                ),
            )
        )
    return tuple(folds)


def assess_readiness(
    probe: ContractProbe,
    *,
    protocol_id: str,
    minimum_independent_trajectories: int,
    producer_split_verified: bool,
    capacity_manifest_verified: bool,
    required_independence_groups: Sequence[str] = (),
) -> ReadinessReport:
    """Apply the sealed no-training gate to a normalized trajectory inventory."""
    blockers = list(probe.blockers)
    risk_blockers: list[str] = []
    records = probe.records
    folds: tuple[LeaveOneTrajectoryOutFold, ...] = ()
    task_readiness = {task: False for task in REQUIRED_TASKS}
    if probe.status == "contract_loaded":
        validate_normalized_records(records)
        folds = build_leave_one_trajectory_out_folds(records)
        for task in REQUIRED_TASKS:
            task_readiness[task] = bool(records) and all(
                bool(record.task_coverage[task]) for record in records
            )
        if len(records) < minimum_independent_trajectories:
            blockers.append(
                f"need at least {minimum_independent_trajectories} independent "
                "numerical trajectory groups"
            )
        if required_independence_groups:
            actual_groups = {record.independence_group_id for record in records}
            expected_groups = set(required_independence_groups)
            if actual_groups != expected_groups:
                missing = sorted(expected_groups - actual_groups)
                unexpected = sorted(actual_groups - expected_groups)
                blockers.append(
                    "trajectory independence groups differ from the sealed factorial: "
                    f"missing={missing}, unexpected={unexpected}"
                )
        for task, ready in task_readiness.items():
            if not ready:
                blockers.append(f"task coverage incomplete: {task}")
        observation_contracts = {record.observation_contract_id for record in records}
        scenario_contracts = {record.scenario_contract_id for record in records}
        if len(observation_contracts) != 1:
            blockers.append("observation conditioning differs across trajectories")
        if len(scenario_contracts) != 1:
            blockers.append("future scenario conditioning differs across trajectories")
        independence_scopes = {record.independence_scope for record in records}
        if len(independence_scopes) != 1:
            blockers.append("trajectory independence scope differs across bundles")
    if not producer_split_verified:
        blockers.append(
            "producer leave-one-combination-out split is not frozen and verified"
        )
    if not capacity_manifest_verified:
        blockers.append(
            "road-aware parameter-count manifest is not verified within the "
            "sealed tolerance"
        )

    enough = len(records) >= minimum_independent_trajectories
    common_gate = (
        probe.status == "contract_loaded"
        and enough
        and producer_split_verified
        and capacity_manifest_verified
    )
    field_allowed = common_gate and task_readiness[TASK_SAME_REGIME]
    transition_allowed = common_gate and task_readiness[TASK_TRANSITION]
    calibrated = bool(records) and all(
        record.uncertainty_status in {"calibrated", "eligible_calibrated"}
        for record in records
    )
    every_risk_training_fold_identifiable = bool(folds) and all(
        {"event", "right_censored"}.issubset(
            {
                record.outcome
                for record in records
                if record.independence_group_id
                in set(fold.training_independence_groups)
            }
        )
        for fold in folds
    )
    risk_allowed = (
        transition_allowed
        and task_readiness[TASK_RESET]
        and every_risk_training_fold_identifiable
        and calibrated
    )
    if records and not calibrated:
        risk_blockers.append(
            "calibrated uncertainty is unavailable on at least one trajectory"
        )
    if records and not every_risk_training_fold_identifiable:
        risk_blockers.append(
            "every LOTO training fold needs both event and right-censored trajectories"
        )
    blockers = sorted(set(blockers))
    risk_blockers = sorted(set(risk_blockers))
    training_allowed = (
        field_allowed and transition_allowed and task_readiness[TASK_RESET]
    )
    return ReadinessReport(
        protocol_id=protocol_id,
        status=(
            "ready_for_fair_training" if training_allowed else "not_ready_no_training"
        ),
        contract_status=probe.status,
        contract_sha256=probe.contract_sha256,
        trajectory_count=len(records),
        independence_group_count=len(
            {record.independence_group_id for record in records}
        ),
        independence_scopes=tuple(
            sorted({record.independence_scope for record in records})
        ),
        task_readiness=task_readiness,
        folds=folds,
        field_training_allowed=field_allowed,
        transition_training_allowed=transition_allowed,
        risk_training_allowed=risk_allowed,
        training_allowed=training_allowed,
        blockers=tuple(blockers),
        risk_blockers=tuple(risk_blockers),
        claims_allowed=(
            "sealed protocol and consumer readiness logic are tooling-valid",
            "leave-one-entire-trajectory-out folds are deterministic once "
            "bundles arrive",
        ),
        claims_forbidden=(
            "multi-trajectory forecast performance",
            "trajectory or road-section generalisation",
            "geometry or material generalisation",
            "autonomous transition prediction",
            "calibrated hazard or RUL",
        ),
    )
