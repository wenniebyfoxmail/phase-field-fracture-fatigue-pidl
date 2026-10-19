"""Fail-closed producer orchestration package for S09-E017.

The package is deliberately import-safe: only Python's standard library is
imported at module import time.  Scientific dependencies are named in
``REAL_BINDINGS`` and may be resolved only after a future, canonical resolved
configuration has passed the explicit execution-authority gate.  The current
tracked configuration is intentionally disabled.

Local tests exercise the state machine with artificial adapters.  They do not
read scientific assets, import torch/numpy, construct an optimizer, call a
model, collect autograd, or contact a producer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import importlib
import json
import math
from pathlib import Path
import time
from typing import Any, Mapping, Protocol


SCHEMA_VERSION = "s09-e017-final-run-package-v1"
RUN_ID = "S09-E017-R001-factorised-head-p0"
ARM_ORDER = ("D_DIRECT", "F_AMP", "F_AMP_SHAPE")
ACTIVE_GROUPS = {
    "D_DIRECT": ("A", "S", "R", "P"),
    "F_AMP": ("A", "R", "P"),
    "F_AMP_SHAPE": ("A", "S", "R", "P"),
}
EVALUATION_UPDATES = (0, 1, 4, 16, 32, 64)
UPDATES_PER_ARM = 64
TOTAL_UPDATE_CAP = 192
EXPECTED_CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
EXPECTED_PACKET_SHA256 = (
    "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
)
EXPECTED_BASE_CONFIG_SHA256 = (
    "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05"
)
EXPECTED_GPU_UUID = "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
EXPECTED_HOSTNAME = "GPUServer8"
EXPECTED_VISIBLE_GPU = "5"
RUN_ROOT = "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run"
ARCHIVE_ROOT = "/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0"
CODE_ROOT = "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code"

# These are declarations, not imports.  They bind the future adapter to the
# reviewed loader/model/physics/core implementation without touching assets.
REAL_BINDINGS = {
    "packet_loader": "s09_stage0a_p1_packet:load_verified_packet",
    "runtime_builder": "s09_stage0a_p1_trainer:build_runtime",
    "gpu_identity": "s09_stage0a_p1_trainer:gpu_identity",
    "tracked_execution_files_clean": "s09_code_identity:tracked_execution_files_clean",
    "base_transition_model": "s09_stage0a_transition:Stage0ATransitionOperator",
    "base_example_builder": "s09_stage0a_p1_trainer:_example",
    "hard_constraint_report": "s09_stage0a_p1_trainer:hard_constraint_report",
    "fixed_judgement_loss": "s09_stage0a_transition:fixed_judgement_loss",
    "mechanical_equilibrium": "s09_fem_physics:equilibrium",
    "free_dof_boundary": "s09_fem_physics:boundary",
    "e017_capacity_seed": "s09_e017_factorised_pilot:capacity_supported_seed",
    "e017_learnable_shape": "s09_e017_factorised_pilot:learnable_shape",
    "e017_amplitude": "s09_e017_factorised_pilot:amplitude_from_residual",
    "e017_decoder": "s09_e017_factorised_pilot:decode_factorised_increment",
    "e017_effective_factorisation": "s09_e017_factorised_pilot:effective_factorisation",
    "e017_amplitude_objective": "s09_e017_factorised_pilot:amplitude_objective",
    "e017_shape_objective": "s09_e017_factorised_pilot:shape_objective",
    "e017_reconstruction_objective": (
        "s09_e017_factorised_pilot:reconstruction_objective"
    ),
    "e017_scale_freezer": "s09_e017_factorised_pilot:freeze_gradient_scales",
    "e017_pcgrad": "s09_e017_factorised_pilot:pcgrad_merge",
    "e017_classifier": "s09_e017_factorised_pilot:classify_profiles",
    "field_evaluator_precedent": "s09_e010_producer:evaluate_arm",
    "optimizer_class": "torch.optim:AdamW",
    "real_adapter_entrypoint": "s09_e017_real_adapter:run_reviewed_producer",
}

COUNTER_KEYS = (
    "config_reads",
    "packet_reads",
    "checkpoint_reads",
    "binding_resolutions",
    "runtime_builds",
    "model_forwards",
    "autograd_collections",
    "optimizer_constructions",
    "optimizer_steps",
    "backward_passes",
    "evaluations",
    "evidence_writes",
)

FIRST_STOP_REASONS = (
    "IDENTITY_MISMATCH",
    "DIRTY_STATE",
    "RESOURCE_CHECK_FAILED",
    "PARAMETER_FREEZE_DRIFT",
    "ARM_OBJECT_ALIASING",
    "OPTIMIZER_STATE_NOT_EMPTY",
    "NONFINITE_VALUE",
    "DAMAGE_BOUND_VIOLATION",
    "IRREVERSIBILITY_VIOLATION",
    "FACTORISATION_ROUNDTRIP_FAILURE",
    "MISSING_SCHEDULED_RECORD",
    "RESOURCE_CAP_EXCEEDED",
    "RECEIPT_HASH_MISMATCH",
    "PROHIBITED_OPERATION_ATTEMPT",
)


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
        f"{name} must be an integer >= {minimum}",
    )
    return value


def _digest(value: Any, name: str) -> str:
    _require(isinstance(value, str) and len(value) == 64, f"{name} must be SHA256")
    _require(
        all(character in "0123456789abcdef" for character in value),
        f"{name} must be lowercase SHA256",
    )
    return value


def _finite(value: Any, name: str) -> float:
    _require(
        type(value) in (int, float) and math.isfinite(float(value)),
        f"{name} must be finite",
    )
    return float(value)


def validate_package_config(config: Mapping[str, Any]) -> None:
    """Validate the exact tracked, disabled final-package candidate."""
    required = {
        "schema_version",
        "run_id",
        "status",
        "execution_authorized",
        "source",
        "bindings",
        "data",
        "mapping",
        "physics",
        "arms",
        "optimizer",
        "budget",
        "producer",
        "evidence",
        "stop",
        "launch",
    }
    _require(set(config) == required, "package config keys drift")
    _require(config["schema_version"] == SCHEMA_VERSION, "package schema drift")
    _require(config["run_id"] == RUN_ID, "run id drift")
    _require(
        config["status"] == "FINAL_RUN_PACKAGE_CANDIDATE__NO_EXECUTION",
        "candidate status drift",
    )
    _require(
        config["execution_authorized"] is False,
        "tracked package must remain disabled",
        PermissionError,
    )
    _require(config["bindings"] == REAL_BINDINGS, "real binding declarations drift")

    source = config["source"]
    _require(
        source["reviewed_core_commit"] == "5ac6b7955b56309ac8ff2fda50b16b2e1669110a",
        "core commit drift",
    )
    _require(
        source["reviewed_integration_commit"]
        == "3a5a2020c7b16555e9ecd9ec19377bf87a52d5c5",
        "integration commit drift",
    )
    _require(
        source["producer_package_reviewed_commit"] == "TO_BE_BOUND_AFTER_REVIEW",
        "premature producer commit binding",
    )

    data = config["data"]
    _require(tuple(data["cycles"]) == EXPECTED_CYCLES, "cycle order drift")
    _require(
        _digest(data["packet_manifest_sha256"], "packet") == EXPECTED_PACKET_SHA256,
        "packet identity drift",
    )
    _require(
        _digest(data["base_config_sha256"], "base config")
        == EXPECTED_BASE_CONFIG_SHA256,
        "base config identity drift",
    )
    _require(
        _digest(data["checkpoint_sha256"], "checkpoint") == EXPECTED_CHECKPOINT_SHA256,
        "checkpoint identity drift",
    )
    _require(
        data["evidence_domain"] == "synthetic_exposed_development",
        "evidence domain drift",
    )
    _require(
        data["fresh_holdout"] is False and data["new_fem"] is False,
        "data boundary drift",
    )

    _require(
        config["mapping"]
        == {
            "input_function": (
                "x_to_d_s00_H_s00_alpha_bar_s00_q_prev_s00_f_s00_"
                "load_path_s00_s05_mesh_material_boundary"
            ),
            "output_function": "x_to_d_s04_H_s04_alpha_bar_s04_q_prev_s04_f_s04_u_s04",
            "damage_target_function": "x_to_delta_d_s00_to_s04_peak",
            "sample_semantics": "independent_cycle",
            "autoregressive": False,
        },
        "operator mapping drift",
    )
    _require(
        config["physics"]
        == {
            "group": "P",
            "residual": "native_q4_amor_mechanical_equilibrium_free_displacement_dofs",
            "beta": 0.25,
            "excluded": [
                "damage_stationarity",
                "kuhn_tucker_history_complementarity",
                "fatigue_law_closure",
                "full_incremental_variational_inequality",
            ],
        },
        "physics boundary drift",
    )

    _require(tuple(config["arms"]) == ARM_ORDER, "arm order drift")
    expected_trainable = {
        "D_DIRECT": ["direct_damage_head"],
        "F_AMP": ["amplitude_residual"],
        "F_AMP_SHAPE": ["amplitude_residual", "shape_logits"],
    }
    for arm in ARM_ORDER:
        item = config["arms"][arm]
        _require(
            tuple(item["active_groups"]) == ACTIVE_GROUPS[arm],
            f"active group drift: {arm}",
        )
        _require(
            item["trainable_parameter_classes"] == expected_trainable[arm],
            f"trainable class drift: {arm}",
        )
        _require(
            item["shared_trunk_frozen"] is True
            and item["non_damage_heads_frozen"] is True,
            f"freeze drift: {arm}",
        )
        _require(item["fresh_empty_optimizer"] is True, f"optimizer start drift: {arm}")

    _require(
        config["optimizer"]
        == {
            "class": "AdamW",
            "dtype": "float64",
            "learning_rate": 0.0003,
            "betas": [0.9, 0.999],
            "epsilon": 1e-08,
            "weight_decay": 0.0,
            "scheduler": None,
        },
        "optimizer contract drift",
    )
    budget = config["budget"]
    _require(
        budget
        == {
            "updates_per_arm": 64,
            "total_update_cap": 192,
            "evaluation_updates": [0, 1, 4, 16, 32, 64],
            "fixed_endpoint_update": 64,
            "retry": False,
            "resume": False,
            "budget_transfer": False,
            "early_success_selection": False,
        },
        "budget drift",
    )
    producer = config["producer"]
    _require(
        producer
        == {
            "alias": "gpu-taobo",
            "hostname": EXPECTED_HOSTNAME,
            "cuda_visible_devices": EXPECTED_VISIBLE_GPU,
            "gpu_uuid": EXPECTED_GPU_UUID,
            "code_root": CODE_ROOT,
            "output_root": RUN_ROOT,
            "archive_root": ARCHIVE_ROOT,
            "wall_time_cap_seconds": 1800,
            "reserved_memory_cap_bytes": 20 * 1024**3,
        },
        "producer envelope drift",
    )
    _require(
        tuple(config["stop"]["reasons"]) == FIRST_STOP_REASONS, "stop reason drift"
    )
    _require(config["stop"]["scope"] == "WHOLE_THREE_ARM_RUN", "stop scope drift")
    _require(
        config["stop"]["retry"] is False and config["stop"]["alternate_gpu"] is False,
        "stop fallback drift",
    )
    _require(
        config["launch"]
        == {
            "wrapper_enabled": False,
            "required_cli_flag": "--execute-reviewed-run",
            "required_resolved_status": "RESOLVED_FOR_AUTHORISED_EXECUTION",
            "requires_exact_reviewed_commit": True,
            "requires_live_preflight": True,
        },
        "launch gate drift",
    )
    validate_evidence_schema(config["evidence"])


def validate_evidence_schema(schema: Mapping[str, Any]) -> None:
    required = {
        "start_receipt",
        "per_arm_start",
        "metric_rows",
        "gradient_rows",
        "field_arrays",
        "figures",
        "checkpoints",
        "audit",
        "completion",
    }
    _require(set(schema) == required, "evidence schema keys drift")
    _require(
        schema["metric_rows"]["widths"] == {"A": 2, "S": 6, "R": 2, "P": 4},
        "metric widths drift",
    )
    _require(schema["metric_rows"]["per_cycle"] is True, "per-cycle evidence missing")
    _require(
        schema["gradient_rows"]["representations"] == ["raw", "scaled", "projected"],
        "gradient representations drift",
    )
    _require(
        schema["field_arrays"]["cycles"] == list(EXPECTED_CYCLES), "field cycle drift"
    )
    _require(
        schema["figures"]["shared_physical_colour_scale"] is True,
        "figure colour scale drift",
    )
    _require(
        schema["figures"]["colourbar_location"] == "OUTSIDE_PANEL",
        "colourbar location drift",
    )
    _require(
        schema["checkpoints"]
        == {"scheduled": [64], "failure_safe_last_complete": True},
        "checkpoint policy drift",
    )
    _require(
        schema["completion"]["write_once"] is True
        and schema["completion"]["inventory_sha256"] is True,
        "completion closure drift",
    )


def assert_launch_enabled(
    config: Mapping[str, Any], *, cli_flag: bool, observed_commit: str
) -> None:
    """Reject the tracked candidate before resolving any real binding."""
    _require(cli_flag is True, "--execute-reviewed-run is required", PermissionError)
    _require(
        config.get("execution_authorized") is True,
        "execution_authorized is false",
        PermissionError,
    )
    _require(
        config.get("status") == "RESOLVED_FOR_AUTHORISED_EXECUTION",
        "resolved execution status missing",
        PermissionError,
    )
    _require(
        config.get("launch", {}).get("wrapper_enabled") is True,
        "launch wrapper is disabled",
        PermissionError,
    )
    expected = config.get("source", {}).get("producer_package_reviewed_commit")
    _require(
        isinstance(expected, str) and expected != "TO_BE_BOUND_AFTER_REVIEW",
        "reviewed commit is unbound",
        PermissionError,
    )
    _require(
        observed_commit == expected,
        "execution commit differs from reviewed commit",
        PermissionError,
    )


def resolve_real_bindings(
    config: Mapping[str, Any],
    *,
    cli_flag: bool,
    observed_commit: str,
) -> dict[str, Any]:
    """Resolve declared callables only after the full authority gate passes."""
    assert_launch_enabled(config, cli_flag=cli_flag, observed_commit=observed_commit)
    resolved: dict[str, Any] = {}
    for name, reference in REAL_BINDINGS.items():
        module_name, attribute_name = reference.split(":", 1)
        value: Any = importlib.import_module(module_name)
        for component in attribute_name.split("."):
            value = getattr(value, component)
        _require(callable(value), f"binding is not callable: {name}")
        resolved[name] = value
    return resolved


@dataclass
class RuntimeCounters:
    config_reads: int = 0
    packet_reads: int = 0
    checkpoint_reads: int = 0
    binding_resolutions: int = 0
    runtime_builds: int = 0
    model_forwards: int = 0
    autograd_collections: int = 0
    optimizer_constructions: int = 0
    optimizer_steps: int = 0
    backward_passes: int = 0
    evaluations: int = 0
    evidence_writes: int = 0

    def validate(self) -> None:
        values = asdict(self)
        _require(tuple(values) == COUNTER_KEYS, "counter schema drift")
        for name, value in values.items():
            _strict_int(value, name)


@dataclass(frozen=True)
class ArmStart:
    arm: str
    shared_state_sha256: str
    trainable_names: tuple[str, ...]
    frozen_names: tuple[str, ...]
    parameter_object_ids: tuple[int, ...]
    optimizer_state_entries: int


class ExecutionAdapter(Protocol):
    """Numerical boundary implemented by a future reviewed real adapter."""

    counters: RuntimeCounters

    def preflight(self) -> Mapping[str, Any]:
        ...

    def prepare_arm(self, arm: str) -> ArmStart:
        ...

    def evaluate(self, arm: str, update: int) -> Mapping[str, Any]:
        ...

    def update(self, arm: str, update: int) -> Mapping[str, Any]:
        ...

    def checkpoint(self, arm: str, update: int) -> bytes:
        ...

    def audit(self) -> Mapping[str, Any]:
        ...


@dataclass
class FirstStop(Exception):
    reason: str
    arm: str | None
    attempted_update: int
    detail: str

    def __post_init__(self) -> None:
        _require(self.reason in FIRST_STOP_REASONS, "unknown first-stop reason")
        _require(self.arm is None or self.arm in ARM_ORDER, "unknown first-stop arm")
        _strict_int(self.attempted_update, "attempted update")


@dataclass
class EvidenceWriter:
    """Canonical, write-once evidence writer used by fixture and future runs."""

    root: Path
    inventory: dict[str, dict[str, Any]] = field(default_factory=dict)

    def write_bytes(self, relative: str, payload: bytes) -> str:
        _require(
            relative
            and not relative.startswith("/")
            and ".." not in Path(relative).parts,
            "invalid evidence path",
        )
        path = self.root / relative
        _require(not path.exists(), f"evidence already exists: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)
        digest = sha256_bytes(payload)
        self.inventory[relative] = {"sha256": digest, "size_bytes": len(payload)}
        return digest

    def write_json(self, relative: str, value: Any) -> str:
        return self.write_bytes(relative, canonical_json(value))

    def write_jsonl(self, relative: str, rows: list[Mapping[str, Any]]) -> str:
        _require(rows, f"empty JSONL: {relative}")
        return self.write_bytes(
            relative, b"".join(canonical_json(dict(row)) for row in rows)
        )

    def close_inventory(self) -> str:
        return self.write_json(
            "inventory.json", {"files": dict(sorted(self.inventory.items()))}
        )


def _validate_arm_starts(
    starts: Mapping[str, ArmStart], config: Mapping[str, Any]
) -> None:
    _require(tuple(starts) == ARM_ORDER, "arm start order drift")
    shared = {start.shared_state_sha256 for start in starts.values()}
    _require(len(shared) == 1, "shared initial states differ")
    seen: set[int] = set()
    for arm, start in starts.items():
        _require(start.arm == arm, f"arm start label drift: {arm}")
        _digest(start.shared_state_sha256, f"shared state {arm}")
        _require(
            start.optimizer_state_entries == 0, f"optimizer state not empty: {arm}"
        )
        _require(
            set(start.trainable_names).isdisjoint(start.frozen_names),
            f"trainable/frozen overlap: {arm}",
        )
        expected_classes = tuple(config["arms"][arm]["trainable_parameter_classes"])
        _require(
            all(
                any(name.startswith(prefix) for name in start.trainable_names)
                for prefix in expected_classes
            ),
            f"missing trainable parameter class: {arm}",
        )
        ids = set(start.parameter_object_ids)
        _require(
            len(ids) == len(start.parameter_object_ids) and seen.isdisjoint(ids),
            f"arm parameter objects alias: {arm}",
        )
        seen.update(ids)


def _validate_metric_record(record: Mapping[str, Any], arm: str, update: int) -> None:
    _require(
        record.get("arm") == arm and record.get("update") == update,
        "metric arm/update drift",
    )
    rows = record.get("cycles")
    _require(
        isinstance(rows, list)
        and [row.get("cycle") for row in rows] == list(EXPECTED_CYCLES),
        "metric cycle coverage drift",
    )
    for row in rows:
        vectors = row.get("decision_vectors")
        _require(
            isinstance(vectors, Mapping) and tuple(vectors) == ("A", "S", "R", "P"),
            "metric vector groups drift",
        )
        for group, width in {"A": 2, "S": 6, "R": 2, "P": 4}.items():
            values = vectors[group]
            _require(
                isinstance(values, list) and len(values) == width,
                f"metric width drift: {group}",
            )
            for index, value in enumerate(values):
                _finite(value, f"{group}[{index}]")
        _require(
            row.get("shape_raw_na_reason")
            in (None, "PREDICTED_ZERO_EFFECTIVE_AMPLITUDE"),
            "shape NA reason drift",
        )
        _require(
            isinstance(row.get("shape_decision_imputed"), bool),
            "shape imputation flag drift",
        )
        _require(
            isinstance(row.get("finite"), bool) and row["finite"],
            "nonfinite metric row",
        )


def _validate_update_record(record: Mapping[str, Any], arm: str, update: int) -> None:
    _require(
        record.get("arm") == arm and record.get("update") == update,
        "update record drift",
    )
    _require(
        tuple(record.get("active_groups", ())) == ACTIVE_GROUPS[arm],
        "active group drift",
    )
    _require(record.get("finite") is True, "nonfinite update")
    _require(record.get("hard_constraint_violations") == 0, "hard-constraint violation")
    required = {
        "raw_losses",
        "raw_gradients",
        "scaled_gradients",
        "projected_gradients",
        "frozen_scales",
        "pairwise_geometry",
        "permutation",
        "projection_log",
        "preclip_norm",
        "postclip_norm",
        "raw_group_dot_realised_update",
    }
    _require(required.issubset(record), "gradient evidence incomplete")
    for name in ("preclip_norm", "postclip_norm"):
        _finite(record[name], name)


def run_artificial_fixture(
    *,
    config: Mapping[str, Any],
    adapter: ExecutionAdapter,
    output_root: Path,
) -> Mapping[str, Any]:
    """Exercise orchestration only; caller must supply an artificial adapter."""
    validate_package_config(config)
    _require(
        getattr(adapter, "artificial_fixture", False) is True,
        "real adapters are forbidden in local fixture execution",
        PermissionError,
    )
    _require(not output_root.exists(), "fixture output root already exists")
    writer = EvidenceWriter(output_root)
    start_time = time.monotonic()
    completed = {arm: 0 for arm in ARM_ORDER}
    last_evaluation = {arm: None for arm in ARM_ORDER}
    first_stop: FirstStop | None = None
    try:
        preflight = dict(adapter.preflight())
        _require(
            preflight.get("artificial_fixture") is True,
            "fixture preflight label missing",
        )
        _require(
            preflight.get("identities_valid") is True,
            "fixture identity preflight failed",
        )
        _require(
            preflight.get("resources_valid") is True,
            "fixture resource preflight failed",
        )
        writer.write_json("prelaunch_receipt.json", preflight)
        starts = {arm: adapter.prepare_arm(arm) for arm in ARM_ORDER}
        _validate_arm_starts(starts, config)
        for arm, start in starts.items():
            writer.write_json(f"arms/{arm}/start_identity.json", asdict(start))

        for arm in ARM_ORDER:
            metrics: list[Mapping[str, Any]] = []
            gradients: list[Mapping[str, Any]] = []
            initial = dict(adapter.evaluate(arm, 0))
            _validate_metric_record(initial, arm, 0)
            metrics.append(initial)
            last_evaluation[arm] = 0
            for update in range(1, UPDATES_PER_ARM + 1):
                result = dict(adapter.update(arm, update))
                _validate_update_record(result, arm, update)
                gradients.append(result)
                completed[arm] = update
                if update in EVALUATION_UPDATES[1:]:
                    metric = dict(adapter.evaluate(arm, update))
                    _validate_metric_record(metric, arm, update)
                    metrics.append(metric)
                    last_evaluation[arm] = update
            checkpoint = adapter.checkpoint(arm, 64)
            writer.write_bytes(f"arms/{arm}/checkpoint_update64.fixture", checkpoint)
            writer.write_jsonl(f"arms/{arm}/metrics.jsonl", metrics)
            writer.write_jsonl(f"arms/{arm}/gradients.jsonl", gradients)
        audit = dict(adapter.audit())
        _require(
            audit.get("hard_constraint_violations") == 0,
            "audit hard-constraint violation",
        )
        writer.write_json("audit.json", audit)
        terminal = "ARTIFICIAL_FIXTURE_COMPLETED"
    except FirstStop as error:
        first_stop = error
        terminal = "ARTIFICIAL_FIXTURE_STOPPED"
    except Exception as error:
        first_stop = FirstStop(
            "PROHIBITED_OPERATION_ATTEMPT",
            None,
            sum(completed.values()),
            f"{type(error).__name__}: {error}",
        )
        terminal = "ARTIFICIAL_FIXTURE_STOPPED"

    adapter.counters.validate()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "terminal_state": terminal,
        "scientific_result_created": False,
        "artificial_fixture": True,
        "completed_updates": completed,
        "last_complete_evaluation": last_evaluation,
        "runtime_counters": asdict(adapter.counters),
        "first_stop": None if first_stop is None else asdict(first_stop),
        "retry": False,
        "alternate_gpu": False,
        "elapsed_seconds": time.monotonic() - start_time,
    }
    writer.write_json("completion_receipt.json", receipt)
    writer.close_inventory()
    return receipt
