"""No-training runner/config/evidence integration for S09-E010.

This module connects the independently reviewed E010 numerical core to the
frozen E008 runtime.  It constructs the three isolated arm states and checks
the complete update directions, schedule and evidence contract, but exposes no
optimizer step or producer launch function.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch

from s09_e009_four_arm import (
    ARM_ANCHOR_25,
    arm_direction as e009_arm_direction,
    atomic_losses,
    flattened_objective_gradients,
    flattened_parameters,
    grouped_losses,
    parameter_state_sha256,
)
from s09_e010_support_amplitude import (
    ARM_A25,
    ARM_B0,
    ARM_B25,
    ARM_ORDER,
    GLOBAL_CLIP_NORM,
    NORM_EPSILON,
    SUPPORT_THRESHOLD,
    balanced_direction,
    balanced_objectives,
    support_amplitude_losses,
    three_arm_direction,
)
from s09_stage0a_p1_packet import canonical_json, sha256_file
from s09_stage0a_p1_trainer import Runtime, build_runtime


SCHEMA_VERSION = "s09-e010-three-arm-no-training-integration-v1"
PLANNED_RUN_ID = "S09-E010-R001-support-amplitude-three-arm"
EVALUATION_UPDATES = (0, 16, 64, 128, 256, 496, 500)
UPDATES_PER_ARM = 500
TOTAL_UPDATE_CAP = 1500
EXPECTED_CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
EXPECTED_PACKET_SHA256 = (
    "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
)
EXPECTED_CORE_COMMIT = "45d8ec5f158d6fbdc608437f02da4fa43501157f"
EXPECTED_PROTOCOL_REVISION = "v2-support-amplitude-balanced-three-arm-screen"
EXPECTED_PROTOCOL_SHA256 = (
    "c97be5487710f53cd1106d042ecea1871a5e8b85dc8a82f5556ac9b0ebe6dee2"
)
EXPECTED_BASE_RUNTIME_CONFIG_SHA256 = (
    "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
)
BASE_RUNTIME_CONFIG_RELATIVE = (
    "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
)
TRUSTED_BASE_RUNTIME_CONFIG = (
    Path(__file__).resolve().parents[1] / BASE_RUNTIME_CONFIG_RELATIVE
)
EXPECTED_PRODUCER = {
    "alias": "Taobo GPU",
    "forbidden_fallback": "CSD3",
    "remote_root": "/mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm",
    "archive_root": (
        "/mnt/data2/drtao/pidl_archives/"
        "S09-E010-R001-support-amplitude-three-arm"
    ),
    "resolved_environment": "TO_BE_LOCKED_BY_FUTURE_READ_ONLY_PREFLIGHT",
}
TERMINAL_COMPLETED = "COMPLETED"
TERMINAL_EXECUTION_FAILED = "EXECUTION_FAILED"
TERMINAL_METHOD_INAPPLICABLE = "METHOD_INAPPLICABLE"
TERMINAL_STATES = (
    TERMINAL_COMPLETED,
    TERMINAL_EXECUTION_FAILED,
    TERMINAL_METHOD_INAPPLICABLE,
)
TERMINATION_RECEIPT_FIELDS = (
    "arm",
    "terminal_state",
    "stop_update",
    "optimizer_steps_completed",
    "fully_logged_updates",
    "evaluation_updates_present",
    "last_valid_evaluation_update",
    "reason",
    "update500_checkpoint_present",
    "finite_status",
    "hard_constraint_counts",
    "artifacts",
)


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _load_verified_json(
    path: Path, expected_sha256: str, message: str
) -> dict[str, Any]:
    payload = path.read_bytes()
    _require(hashlib.sha256(payload).hexdigest() == expected_sha256, message)
    return json.loads(
        payload.decode("utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _tensor_sha256(value: torch.Tensor) -> str:
    array = np.ascontiguousarray(value.detach().cpu().numpy())
    return hashlib.sha256(
        array.dtype.str.encode("ascii")
        + b"\0"
        + np.asarray(array.shape, dtype=np.int64).tobytes()
        + array.tobytes()
    ).hexdigest()


def _validate_base_runtime_identity(
    *, source: Mapping[str, Any], base_config_path: Path, synthetic_test_adapter: bool
) -> None:
    actual_sha256 = sha256_file(base_config_path)
    if not synthetic_test_adapter:
        _require(
            actual_sha256 == EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
            "untrusted base E008 runtime config bytes",
        )
        _require(
            source.get("base_runtime_config_sha256")
            == EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
            "base E008 runtime config trust anchor drift",
        )
        return

    supplied = _load_json(base_config_path)
    trusted = _load_verified_json(
        TRUSTED_BASE_RUNTIME_CONFIG,
        EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
        "synthetic adapter trusted base identity drift",
    )
    _require(
        supplied.get("data", {}).get("native_nodes") == 9
        and supplied.get("data", {}).get("native_q4_elements") == 4,
        "synthetic adapter permits only the fixed 9-node/4-Q4 support",
    )
    trusted["data"]["native_nodes"] = 9
    trusted["data"]["native_q4_elements"] = 4
    _require(
        supplied == trusted,
        "synthetic adapter changed a non-resolution base-runtime invariant",
    )
    _require(
        source.get("base_runtime_config_sha256") == actual_sha256,
        "synthetic base-runtime hash mismatch",
    )


def validate_integration_config(
    config: Mapping[str, Any],
    *,
    base_config_path: Path,
    synthetic_test_adapter: bool = False,
) -> None:
    """Fail closed on drift from the reviewed three-arm no-training contract."""
    _require(
        set(config)
        == {
            "schema_version",
            "planned_run_id",
            "status",
            "execution_authorized",
            "source",
            "data",
            "model",
            "optimisation",
            "budget",
            "arms",
            "evidence",
            "producer",
        },
        "integration top-level keys drift",
    )
    _require(config.get("schema_version") == SCHEMA_VERSION, "integration schema drift")
    _require(
        config.get("planned_run_id") == PLANNED_RUN_ID, "planned run identity drift"
    )
    _require(
        config.get("status") == "RUNNER_INTEGRATION_CANDIDATE__NO_TRAINING",
        "integration status drift",
    )
    _require(
        config.get("execution_authorized") is False,
        "no-training integration must remain unauthorised",
        PermissionError,
    )
    source = config.get("source", {})
    _require(
        set(source)
        == {
            "protocol_revision",
            "protocol_sha256",
            "core_code_ready_commit",
            "base_runtime_config",
            "base_runtime_config_sha256",
            "integration_reviewed_commit",
            "input_packet_sha256",
        },
        "source keys drift",
    )
    _require(
        source.get("protocol_revision") == EXPECTED_PROTOCOL_REVISION,
        "protocol revision drift",
    )
    _require(
        source.get("protocol_sha256") == EXPECTED_PROTOCOL_SHA256,
        "protocol identity drift",
    )
    _require(
        source.get("core_code_ready_commit") == EXPECTED_CORE_COMMIT,
        "reviewed core commit drift",
    )
    _require(
        source.get("base_runtime_config") == BASE_RUNTIME_CONFIG_RELATIVE,
        "base E008 runtime config path drift",
    )
    _validate_base_runtime_identity(
        source=source,
        base_config_path=base_config_path,
        synthetic_test_adapter=synthetic_test_adapter,
    )
    _require(
        source.get("integration_reviewed_commit")
        == "TO_BE_SET_AFTER_EXACT_COMMIT_REVIEW"
        and source.get("input_packet_sha256") == EXPECTED_PACKET_SHA256,
        "no-training source identity drift",
    )
    _require(
        config.get("data")
        == {
            "selected_cycles": list(EXPECTED_CYCLES),
            "batch_size": 1,
            "support_threshold": SUPPORT_THRESHOLD,
            "target_only_training_fields": ["support_mask", "target_amplitude"],
            "target_derived_inference_fields": [],
        },
        "data support, order or leakage boundary drift",
    )
    _require(
        config.get("model")
        == {
            "seed": 20261016,
            "dtype": "float64",
            "initialisation": (
                "one_constructed_model_then_complete_"
                "parameter_and_buffer_copy_per_arm"
            ),
        },
        "model or initialisation contract drift",
    )
    _require(
        config.get("optimisation")
        == {
            "optimizer": "AdamW",
            "learning_rate": 0.0003,
            "betas": [0.9, 0.999],
            "epsilon": 1e-8,
            "weight_decay": 0.0,
            "gradient_epsilon": NORM_EPSILON,
            "global_clip_norm": GLOBAL_CLIP_NORM,
            "complete_direction_clip_count": 1,
        },
        "optimisation contract drift",
    )
    _require(
        config.get("budget")
        == {
            "updates_per_arm": UPDATES_PER_ARM,
            "total_update_cap": TOTAL_UPDATE_CAP,
            "evaluation_updates": list(EVALUATION_UPDATES),
            "unused_budget_transfer": False,
        },
        "three-arm budget or evaluation schedule drift",
    )
    arms = config.get("arms", {})
    _require(tuple(arms) == ARM_ORDER, "arm order drift")
    _require(
        arms[ARM_A25]
        == {
            "rule": "exact_e009_a25_replay",
            "beta": 0.25,
            "support_coefficient": 0.0,
            "amplitude_coefficient": 0.0,
        },
        "A25 arm drift",
    )
    for arm, beta in ((ARM_B25, 0.25), (ARM_B0, 0.0)):
        _require(
            arms[arm]
            == {
                "rule": "support_amplitude_balanced_damage_anchor",
                "beta": beta,
                "support_coefficient": 1.0,
                "amplitude_coefficient": 1.0,
            },
            f"{arm} drift",
        )
    evidence = config.get("evidence", {})
    _require(
        set(evidence)
        == {
            "required_per_arm_common",
            "required_completed_arm_only",
            "required_shared",
            "termination_receipt_required_fields",
            "terminal_states",
            "cross_arm_comparison",
        },
        "evidence keys drift",
    )
    _require(
        evidence.get("required_per_arm_common")
        == [
            "start_identity.json",
            "train_log.jsonl",
            "gradient_diagnostics.jsonl",
            "diagnostic_metrics.jsonl",
            "termination_receipt.json",
        ],
        "common per-arm evidence contract drift",
    )
    _require(
        evidence.get("required_completed_arm_only") == ["checkpoint_update500.pt"],
        "completed-arm evidence contract drift",
    )
    _require(
        evidence.get("required_shared")
        == [
            "config_resolved.json",
            "input_packet_identity.json",
            "environment.txt",
            "exact_a25_replay_trace.json",
            "decision_metrics.json",
            "decision_table.csv",
            "decision_figure.png",
            "per_cycle_metrics.csv",
            "decision.md",
            "completion_receipt.json",
        ],
        "shared evidence contract drift",
    )
    _require(
        evidence.get("termination_receipt_required_fields")
        == list(TERMINATION_RECEIPT_FIELDS),
        "termination receipt field contract drift",
    )
    _require(
        evidence.get("terminal_states")
        == {
            TERMINAL_COMPLETED: {
                "optimizer_steps_completed": UPDATES_PER_ARM,
                "fully_logged_updates": UPDATES_PER_ARM,
                "required_evaluation_updates": list(EVALUATION_UPDATES),
                "update500_checkpoint_required": True,
            },
            TERMINAL_EXECUTION_FAILED: {
                "partial_counts_required": True,
                "last_valid_evaluation_required_if_any": True,
                "update500_checkpoint_required": False,
            },
            TERMINAL_METHOD_INAPPLICABLE: {
                "allowed_arms": list(ARM_ORDER),
                "reason": "ANCHOR_STATIONARY_OR_INAPPLICABLE",
                "stop_location_required": True,
                "update500_checkpoint_required": False,
            },
        },
        "terminal-state evidence contract drift",
    )
    _require(
        evidence.get("cross_arm_comparison")
        == {
            "requires_shared_identity_pass": True,
            "requires_exact_a25_replay_pass": True,
            "integer_pair_count_decision": True,
            "invalid_if_any_precondition_fails": True,
        },
        "cross-arm comparison validity contract drift",
    )
    _require(config.get("producer") == EXPECTED_PRODUCER, "producer contract drift")


def validate_termination_receipt(receipt: Mapping[str, Any]) -> None:
    """Validate one future terminal arm receipt without stepping anything."""
    _require(
        set(receipt) == set(TERMINATION_RECEIPT_FIELDS),
        "termination receipt keys drift",
    )
    arm, state = receipt["arm"], receipt["terminal_state"]
    _require(arm in ARM_ORDER, "unknown arm in termination receipt")
    _require(state in TERMINAL_STATES, "unknown terminal state")
    steps, logged, stop = (
        receipt["optimizer_steps_completed"],
        receipt["fully_logged_updates"],
        receipt["stop_update"],
    )
    _require(
        isinstance(steps, int)
        and not isinstance(steps, bool)
        and 0 <= steps <= UPDATES_PER_ARM,
        "invalid optimizer step count",
    )
    _require(
        isinstance(logged, int)
        and not isinstance(logged, bool)
        and 0 <= logged <= steps,
        "invalid fully logged update count",
    )
    _require(
        isinstance(stop, int)
        and not isinstance(stop, bool)
        and steps <= stop <= min(steps + 1, UPDATES_PER_ARM),
        "invalid stop update",
    )
    evaluations = receipt["evaluation_updates_present"]
    _require(
        isinstance(evaluations, list)
        and evaluations == sorted(set(evaluations))
        and all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value in EVALUATION_UPDATES
            and value <= steps
            for value in evaluations
        ),
        "invalid evaluation update record",
    )
    _require(
        receipt["last_valid_evaluation_update"]
        == (evaluations[-1] if evaluations else None),
        "last valid evaluation mismatch",
    )
    _require(
        isinstance(receipt["finite_status"], bool), "finite status must be boolean"
    )
    hard_counts, artifacts = receipt["hard_constraint_counts"], receipt["artifacts"]
    _require(
        isinstance(hard_counts, Mapping)
        and bool(hard_counts)
        and all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in hard_counts.values()
        ),
        "hard-constraint counts must be nonnegative integers",
    )
    _require(isinstance(artifacts, Mapping), "artifacts must be a mapping")
    checkpoint = receipt["update500_checkpoint_present"]
    _require(isinstance(checkpoint, bool), "checkpoint presence must be boolean")
    if checkpoint:
        _require(
            steps == logged == UPDATES_PER_ARM
            and EVALUATION_UPDATES[-1] in evaluations,
            "update-500 checkpoint requires complete update/evaluation state",
        )
        _require(
            isinstance(artifacts.get("checkpoint_update500.pt"), str)
            and bool(artifacts["checkpoint_update500.pt"].strip()),
            "present update-500 checkpoint requires artifact identity",
        )
    else:
        _require(
            "checkpoint_update500.pt" not in artifacts,
            "absent checkpoint has artifact identity",
        )
    if state == TERMINAL_COMPLETED:
        _require(
            steps == logged == stop == UPDATES_PER_ARM,
            "completed arm must contain 500 updates",
        )
        _require(
            evaluations == list(EVALUATION_UPDATES),
            "completed arm is missing an evaluation",
        )
        _require(
            checkpoint is True and receipt["reason"] is None,
            "completed arm receipt drift",
        )
        _require(receipt["finite_status"] is True, "completed arm must remain finite")
        _require(
            all(value == 0 for value in hard_counts.values()),
            "hard-constraint violation",
        )
    elif state == TERMINAL_EXECUTION_FAILED:
        _require(
            isinstance(receipt["reason"], str) and bool(receipt["reason"].strip()),
            "failed arm requires a reason",
        )
    else:
        _require(
            receipt["reason"] == "ANCHOR_STATIONARY_OR_INAPPLICABLE",
            "method-inapplicable reason drift",
        )
        _require(
            checkpoint is False and receipt["finite_status"] is True,
            "method-inapplicable drift",
        )
        _require(
            all(value == 0 for value in hard_counts.values()),
            "hard-constraint violation",
        )


def cross_arm_performance_eligible(
    *, shared_identity_pass: bool, exact_a25_replay_pass: bool
) -> bool:
    return shared_identity_pass is True and exact_a25_replay_pass is True


def build_schedule(cycles: tuple[int, ...] = EXPECTED_CYCLES) -> tuple[int, ...]:
    _require(cycles == EXPECTED_CYCLES, "noncanonical cycle schedule")
    schedule = tuple(cycles[index % len(cycles)] for index in range(UPDATES_PER_ARM))
    _require(
        len(schedule) == UPDATES_PER_ARM and schedule[-4:] == (1, 2, 3, 4),
        "schedule drift",
    )
    return schedule


def _initialise_arm_states(
    base_model: torch.nn.Module,
    *,
    learning_rate: float,
    betas: tuple[float, float],
    optimizer_epsilon: float,
    weight_decay: float,
) -> tuple[dict[str, torch.nn.Module], dict[str, torch.optim.AdamW], dict[str, Any]]:
    models = {arm: copy.deepcopy(base_model) for arm in ARM_ORDER}
    optimizers = {
        arm: torch.optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            betas=betas,
            eps=optimizer_epsilon,
            weight_decay=weight_decay,
        )
        for arm, model in models.items()
    }
    state_hashes = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    parameter_ids = {
        arm: {id(parameter) for parameter in model.parameters()}
        for arm, model in models.items()
    }
    buffer_ids = {
        arm: {id(buffer) for buffer in model.buffers()} for arm, model in models.items()
    }
    disjoint = all(
        parameter_ids[left].isdisjoint(parameter_ids[right])
        and buffer_ids[left].isdisjoint(buffer_ids[right])
        for index, left in enumerate(ARM_ORDER)
        for right in ARM_ORDER[index + 1 :]
    )
    _require(len(set(state_hashes.values())) == 1, "initial arm states differ")
    _require(disjoint, "arm parameter/buffer objects are shared")
    _require(
        all(not optimizer.state for optimizer in optimizers.values()),
        "optimizer state not empty",
    )
    return models, optimizers, {
        "initial_state_sha256": state_hashes,
        "parameter_and_buffer_objects_disjoint": disjoint,
        "optimizer_states_empty": True,
    }


def _losses_and_additions(
    runtime: Runtime, index: int
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor], dict[str, Any]]:
    atomic, context = atomic_losses(runtime, index)
    additions, addition_record = support_amplitude_losses(
        predicted_peak=context["output"]["d_peak"],
        target_peak=context["target"]["d_peak"],
        damage_pre=context["d_pre"],
        nodal_weight=context["output"]["nodal_weight"],
    )
    return atomic, additions, addition_record


def _direction_with_damage_reference(
    model: torch.nn.Module,
    atomic: Mapping[str, torch.Tensor],
    additions: Mapping[str, torch.Tensor],
    arm: str,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, Any]]:
    """Build the reviewed direction once while retaining its same-graph g_D."""
    if arm == ARM_A25:
        objectives = {
            **grouped_losses(atomic),
            "L_D_alignment": grouped_losses(atomic)["L_D"],
        }
        gradients, layout = flattened_objective_gradients(model, objectives)
        direction, diagnostic = balanced_direction(
            {
                "L_D": gradients["L_D"],
                "L_S": torch.zeros_like(gradients["L_D"]),
                "L_A": torch.zeros_like(gradients["L_D"]),
                "L_U": gradients["L_U"],
                "L_H": gradients["L_H"],
                "L_P": gradients["L_P"],
            },
            beta=0.25,
        )
        return direction, gradients["L_D_alignment"], {
            **diagnostic,
            "arm": arm,
            "layout": layout,
            "exact_e009_a25_replay": True,
        }
    objectives = balanced_objectives(atomic, additions)
    gradients, layout = flattened_objective_gradients(model, objectives)
    direction, diagnostic = balanced_direction(
        gradients, beta=0.25 if arm == ARM_B25 else 0.0
    )
    return direction, gradients["L_D"], {
        **diagnostic,
        "arm": arm,
        "layout": layout,
        "exact_e009_a25_replay": False,
    }


@dataclass
class IntegrationBundle:
    base_runtime: Runtime
    arm_runtimes: dict[str, Runtime]
    optimizers: dict[str, torch.optim.AdamW]
    schedule: tuple[int, ...]
    receipt: dict[str, Any]


def build_no_training_integration(
    *,
    packet_dir: Path,
    base_config_path: Path,
    integration_config_path: Path,
    device: torch.device,
    synthetic_test_adapter: bool = False,
) -> IntegrationBundle:
    config = _load_json(integration_config_path)
    validate_integration_config(
        config,
        base_config_path=base_config_path,
        synthetic_test_adapter=synthetic_test_adapter,
    )
    _require(device.type == "cpu", "no-training integration is CPU-only")
    torch.manual_seed(int(config["model"]["seed"]))
    base_runtime = build_runtime(
        packet_dir=packet_dir,
        config_path=base_config_path,
        device=device,
        executable=False,
    )
    _require(
        base_runtime.packet_identity["manifest_sha256"] == EXPECTED_PACKET_SHA256
        or synthetic_test_adapter,
        "packet identity drift",
    )
    _require(
        tuple(int(value) for value in base_runtime.arrays["cycles"]) == EXPECTED_CYCLES,
        "cycle order drift",
    )
    opt = config["optimisation"]
    models, optimizers, isolation = _initialise_arm_states(
        base_runtime.model,
        learning_rate=opt["learning_rate"],
        betas=tuple(opt["betas"]),
        optimizer_epsilon=opt["epsilon"],
        weight_decay=opt["weight_decay"],
    )
    for arm in ARM_ORDER:
        model_ids = {id(parameter) for parameter in models[arm].parameters()}
        optimizer_ids = {
            id(parameter)
            for group in optimizers[arm].param_groups
            for parameter in group["params"]
        }
        _require(optimizer_ids == model_ids, f"optimizer/model binding mismatch: {arm}")
    isolation["optimizer_parameters_match_arm_models"] = True
    arm_runtimes = {
        arm: replace(base_runtime, model=model) for arm, model in models.items()
    }
    before = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    directions: dict[str, Any] = {}
    core_matches: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARM_ORDER}
    for arm in ARM_ORDER:
        runtime = arm_runtimes[arm]
        first_record: dict[str, Any] | None = None
        for index, cycle in enumerate(EXPECTED_CYCLES):
            atomic, additions, addition_record = _losses_and_additions(runtime, index)
            direction, g_d, diagnostic = _direction_with_damage_reference(
                runtime.model, atomic, additions, arm
            )
            _require(
                diagnostic["layout"]["parameter_order"]
                == flattened_parameters(runtime.model)[1],
                f"parameter order mismatch: {arm}",
            )
            runtime.model.zero_grad(set_to_none=True)
            expected_atomic, expected_additions, _ = _losses_and_additions(
                runtime, index
            )
            if arm == ARM_A25:
                expected, _ = e009_arm_direction(
                    runtime.model, expected_atomic, ARM_ANCHOR_25
                )
            else:
                expected, _ = three_arm_direction(
                    runtime.model, expected_atomic, expected_additions, arm
                )
            maximum_difference = float(
                torch.max(torch.abs(direction - expected)).detach().cpu()
            )
            _require(
                maximum_difference == 0.0,
                f"reviewed core direction mismatch: {arm}/{cycle}",
            )
            core_matches[arm].append(
                {
                    "cycle": cycle,
                    "runner_direction_sha256": _tensor_sha256(direction),
                    "reviewed_core_direction_sha256": _tensor_sha256(expected),
                    "maximum_absolute_difference": maximum_difference,
                }
            )
            if first_record is None:
                first_record = {
                    "direction_sha256": _tensor_sha256(direction),
                    "damage_gradient_sha256": _tensor_sha256(g_d),
                    "direction_norm": float(
                        torch.linalg.vector_norm(direction).detach().cpu()
                    ),
                    "damage_gradient_norm": float(
                        torch.linalg.vector_norm(g_d).detach().cpu()
                    ),
                    "vector_length": int(direction.numel()),
                    "clip_count_for_complete_direction": diagnostic[
                        "clip_count_for_complete_direction"
                    ],
                    "exact_e009_a25_replay": diagnostic["exact_e009_a25_replay"],
                    "support_node_count": addition_record["support_node_count"],
                    "target_amplitude": addition_record["target_amplitude"],
                }
            runtime.model.zero_grad(set_to_none=True)
        _require(first_record is not None, f"missing direction record: {arm}")
        directions[arm] = {
            **first_record,
            "reviewed_core_cycle_count": len(core_matches[arm]),
            "reviewed_core_maximum_absolute_difference": max(
                record["maximum_absolute_difference"] for record in core_matches[arm]
            ),
        }
    after = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    _require(before == after, "direction preflight mutated an arm model")
    _require(
        all(not optimizer.state for optimizer in optimizers.values()),
        "optimizer state populated",
    )
    schedule = build_schedule()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "planned_run_id": PLANNED_RUN_ID,
        "verdict": "NO_TRAINING_INTEGRATION_PASS",
        "execution_authorized": False,
        "optimizer_step_performed": False,
        "config_sha256": sha256_file(integration_config_path),
        "base_runtime_config_sha256": sha256_file(base_config_path),
        "packet_manifest_sha256": base_runtime.packet_identity["manifest_sha256"],
        "arm_order": list(ARM_ORDER),
        "updates_per_arm": UPDATES_PER_ARM,
        "total_update_cap": TOTAL_UPDATE_CAP,
        "evaluation_updates": list(EVALUATION_UPDATES),
        "schedule_sha256": hashlib.sha256(
            np.asarray(schedule, dtype=np.int64).tobytes()
        ).hexdigest(),
        "schedule_first_16": list(schedule[:16]),
        "schedule_last_4": list(schedule[-4:]),
        "isolation": isolation,
        "model_hashes_unchanged": before == after,
        "optimizer_states_empty_after_direction_preflight": True,
        "directions": directions,
        "reviewed_core_matches": core_matches,
    }
    canonical_json(receipt)
    return IntegrationBundle(base_runtime, arm_runtimes, optimizers, schedule, receipt)


def write_no_training_receipt(bundle: IntegrationBundle, output_path: Path) -> None:
    _require(
        bundle.receipt.get("execution_authorized") is False,
        "producer-authorised receipt is forbidden here",
        PermissionError,
    )
    _require(not output_path.exists(), "receipt output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(bundle.receipt))
