"""No-training integration contract for the S09-E009 four-arm screen.

This module binds the reviewed four-arm primitives to the verified S09-E008
runtime, schedule, optimiser isolation and evidence manifest.  It deliberately
does not expose an optimiser-step or producer launch function.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch

from s09_e009_four_arm import (
    ARM_ANCHOR_0,
    ARM_ANCHOR_25,
    ARM_ORDER,
    ARM_REPLAY,
    ARM_SCALAR,
    GLOBAL_CLIP_NORM,
    NORM_EPSILON,
    atomic_losses,
    damage_anchor_direction,
    flattened_objective_gradients,
    flattened_parameters,
    grouped_losses,
    initialise_arm_states,
    parameter_state_sha256,
    replay_losses,
    scalar_data_direction,
)
from s09_multiobjective_update import merge_objective_gradients
from s09_stage0a_p1_packet import canonical_json, sha256_file
from s09_stage0a_p1_trainer import Runtime, build_runtime


SCHEMA_VERSION = "s09-e009-four-arm-no-training-integration-v1"
PLANNED_RUN_ID = "S09-E009-R001-four-arm-damage-separation"
EVALUATION_UPDATES = (0, 16, 64, 128, 256, 496, 500)
UPDATES_PER_ARM = 500
TOTAL_UPDATE_CAP = 2000
EXPECTED_CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
EXPECTED_CORE_COMMIT = "8b6a2e49b241ae73f433645cb30a69291f7aee53"
EXPECTED_PROTOCOL_REVISION = "v3-four-arm-damage-separation-screen"
EXPECTED_PROTOCOL_SHA256 = "67f84d05ffca2054d47cef6e016b5c86098681bbf41813486adf8c9a72588ff8"
EXPECTED_BASE_RUNTIME_CONFIG_SHA256 = (
    "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
)
BASE_RUNTIME_CONFIG_RELATIVE = (
    "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
)
TRUSTED_BASE_RUNTIME_CONFIG = Path(__file__).resolve().parents[1] / BASE_RUNTIME_CONFIG_RELATIVE
EXPECTED_PRODUCER = {
    "alias": "Taobo GPU",
    "forbidden_fallback": "CSD3",
    "remote_root": "/mnt/data2/drtao/wennie/S09-E009-R001-four-arm-damage-separation",
    "archive_root": "/mnt/data2/drtao/pidl_archives/S09-E009-R001-four-arm-damage-separation",
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


def _require(condition: bool, message: str, error: type[Exception] = ValueError) -> None:
    if not condition:
        raise error(message)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _direction_sha256(direction: torch.Tensor) -> str:
    array = np.ascontiguousarray(direction.detach().cpu().numpy())
    return hashlib.sha256(array.dtype.str.encode("ascii") + b"\0" +
                          np.asarray(array.shape, dtype=np.int64).tobytes() +
                          array.tobytes()).hexdigest()


def _validate_base_runtime_identity(*, source: Mapping[str, Any], base_config_path: Path,
                                    synthetic_test_adapter: bool) -> None:
    """Bind production to one reviewed file; allow one explicit tiny-Q4 test projection."""
    actual_sha256 = sha256_file(base_config_path)
    if not synthetic_test_adapter:
        _require(actual_sha256 == EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
                 "untrusted base E008 runtime config bytes")
        _require(source.get("base_runtime_config_sha256") ==
                 EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
                 "base E008 runtime config trust anchor drift")
        return

    supplied = _load_json(base_config_path)
    _require(sha256_file(TRUSTED_BASE_RUNTIME_CONFIG) ==
             EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
             "synthetic adapter trusted base identity drift")
    trusted = _load_json(TRUSTED_BASE_RUNTIME_CONFIG)
    _require(supplied.get("data", {}).get("native_nodes") == 9 and
             supplied.get("data", {}).get("native_q4_elements") == 4,
             "synthetic adapter permits only the fixed 9-node/4-Q4 support")
    trusted["data"]["native_nodes"] = 9
    trusted["data"]["native_q4_elements"] = 4
    _require(supplied == trusted,
             "synthetic adapter changed a non-resolution base-runtime invariant")
    _require(source.get("base_runtime_config_sha256") == actual_sha256,
             "synthetic base-runtime hash mismatch")


def validate_integration_config(config: Mapping[str, Any], *, base_config_path: Path,
                                synthetic_test_adapter: bool = False) -> None:
    """Fail closed on drift from the design-reviewed no-training contract."""
    _require(set(config) == {
        "schema_version", "planned_run_id", "status", "execution_authorized",
        "source", "data", "model", "optimisation", "budget", "arms", "evidence",
        "producer",
    }, "integration top-level keys drift")
    _require(config.get("schema_version") == SCHEMA_VERSION, "integration schema drift")
    _require(config.get("planned_run_id") == PLANNED_RUN_ID, "planned run identity drift")
    _require(config.get("status") == "RUNNER_INTEGRATION_CANDIDATE__NO_TRAINING",
             "integration status drift")
    _require(config.get("execution_authorized") is False,
             "no-training integration must remain unauthorised", PermissionError)
    source = config.get("source", {})
    _require(set(source) == {
        "protocol_revision", "protocol_sha256", "core_code_ready_commit",
        "base_runtime_config", "base_runtime_config_sha256",
        "integration_reviewed_commit", "input_packet_sha256",
    }, "source keys drift")
    _require(source.get("protocol_revision") == EXPECTED_PROTOCOL_REVISION,
             "protocol revision drift")
    _require(source.get("protocol_sha256") == EXPECTED_PROTOCOL_SHA256,
             "protocol identity drift")
    _require(source.get("core_code_ready_commit") == EXPECTED_CORE_COMMIT,
             "reviewed core commit drift")
    _require(source.get("base_runtime_config") == BASE_RUNTIME_CONFIG_RELATIVE,
             "base E008 runtime config path drift")
    _validate_base_runtime_identity(
        source=source,
        base_config_path=base_config_path,
        synthetic_test_adapter=synthetic_test_adapter,
    )
    _require(source.get("integration_reviewed_commit") ==
             "TO_BE_SET_AFTER_EXACT_COMMIT_REVIEW" and
             source.get("input_packet_sha256") == "TO_BE_LOCKED_FROM_REVIEWED_PACKET",
             "no-training source fields must remain unresolved")
    budget = config.get("budget", {})
    _require(budget == {
        "updates_per_arm": UPDATES_PER_ARM,
        "total_update_cap": TOTAL_UPDATE_CAP,
        "evaluation_updates": list(EVALUATION_UPDATES),
        "unused_budget_transfer": False,
    }, "four-arm budget or evaluation schedule drift")
    data = config.get("data", {})
    _require(data == {"selected_cycles": list(EXPECTED_CYCLES), "batch_size": 1},
             "data support or cycle order drift")
    _require(config.get("model") == {
        "seed": 20261016, "dtype": "float64",
        "initialisation": "one_constructed_model_then_complete_parameter_and_buffer_copy_per_arm",
    }, "model/initialisation contract drift")
    optimisation = config.get("optimisation", {})
    expected_optimisation = {
        "optimizer": "AdamW", "learning_rate": 0.0003,
        "betas": [0.9, 0.999], "epsilon": 1e-8, "weight_decay": 0.0,
        "gradient_epsilon": NORM_EPSILON, "global_clip_norm": GLOBAL_CLIP_NORM,
    }
    _require(optimisation == expected_optimisation, "optimisation contract drift")
    arms = config.get("arms", {})
    _require(tuple(arms) == ARM_ORDER, "arm order drift")
    _require(arms[ARM_REPLAY] == {"rule": "exact_e008_replay", "physics_coefficient": "inherited"},
             "replay arm drift")
    _require(arms[ARM_SCALAR] == {"rule": "scalar_data_only", "physics_coefficient": 0.0},
             "scalar arm drift")
    _require(arms[ARM_ANCHOR_0] == {"rule": "damage_anchor", "beta": 0.0},
             "A0 arm drift")
    _require(arms[ARM_ANCHOR_25] == {"rule": "damage_anchor", "beta": 0.25},
             "A25 arm drift")
    evidence = config.get("evidence", {})
    _require(set(evidence) == {
        "required_per_arm_common", "required_completed_arm_only", "required_shared",
        "termination_receipt_required_fields", "terminal_states",
        "cross_arm_comparison",
    }, "evidence keys drift")
    _require(evidence.get("required_per_arm_common") == [
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "termination_receipt.json",
    ], "common per-arm evidence contract drift")
    _require(evidence.get("required_completed_arm_only") == [
        "checkpoint_update500.pt",
    ], "completed-arm evidence contract drift")
    _require(evidence.get("required_shared") == [
        "config_resolved.json", "input_packet_identity.json", "environment.txt",
        "decision_metrics.json", "decision_table.csv", "decision_figure.png",
        "per_cycle_metrics.csv", "decision.md", "completion_receipt.json",
    ], "shared evidence contract drift")
    _require(evidence.get("termination_receipt_required_fields") ==
             list(TERMINATION_RECEIPT_FIELDS),
             "termination receipt field contract drift")
    _require(evidence.get("terminal_states") == {
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
            "allowed_arms": [ARM_ANCHOR_0, ARM_ANCHOR_25],
            "reason": "ANCHOR_STATIONARY_OR_INAPPLICABLE",
            "stop_location_required": True,
            "update500_checkpoint_required": False,
        },
    }, "terminal-state evidence contract drift")
    _require(evidence.get("cross_arm_comparison") == {
        "requires_shared_identity_pass": True,
        "requires_replay_gate_pass": True,
        "invalid_if_either_fails_even_when_files_exist": True,
    }, "cross-arm comparison validity contract drift")
    _require(config.get("producer") == EXPECTED_PRODUCER,
             "producer contract drift")


def validate_termination_receipt(receipt: Mapping[str, Any]) -> None:
    """Validate one future terminal receipt without writing or stepping anything."""
    _require(set(receipt) == set(TERMINATION_RECEIPT_FIELDS),
             "termination receipt keys drift")
    arm = receipt["arm"]
    state = receipt["terminal_state"]
    _require(arm in ARM_ORDER, "unknown arm in termination receipt")
    _require(state in TERMINAL_STATES, "unknown terminal state")
    steps = receipt["optimizer_steps_completed"]
    logged = receipt["fully_logged_updates"]
    stop_update = receipt["stop_update"]
    evaluations = receipt["evaluation_updates_present"]
    _require(type(steps) is int and 0 <= steps <= UPDATES_PER_ARM,
             "invalid optimizer step count")
    _require(type(logged) is int and 0 <= logged <= steps,
             "invalid fully logged update count")
    _require(type(stop_update) is int and 0 <= stop_update <= UPDATES_PER_ARM,
             "invalid stop update")
    _require(isinstance(evaluations, list) and
             all(type(value) is int and value in EVALUATION_UPDATES for value in evaluations) and
             evaluations == sorted(set(evaluations)),
             "invalid evaluation update record")
    _require(receipt["last_valid_evaluation_update"] ==
             (evaluations[-1] if evaluations else None),
             "last valid evaluation mismatch")
    _require(isinstance(receipt["finite_status"], bool), "finite status must be boolean")
    _require(isinstance(receipt["hard_constraint_counts"], Mapping),
             "hard-constraint counts must be a mapping")
    _require(isinstance(receipt["artifacts"], Mapping), "artifacts must be a mapping")
    hard_counts = receipt["hard_constraint_counts"]
    artifacts = receipt["artifacts"]
    _require(bool(hard_counts) and
             all(type(value) is int and value >= 0 for value in hard_counts.values()),
             "hard-constraint counts must be nonnegative integers")
    _require(all(update <= steps for update in evaluations),
             "evaluation update exceeds completed optimizer steps")
    _require(stop_update >= steps,
             "stop update cannot precede completed optimizer steps")
    checkpoint_present = receipt["update500_checkpoint_present"]
    _require(isinstance(checkpoint_present, bool),
             "checkpoint presence must be boolean")
    if checkpoint_present:
        _require(steps == logged == UPDATES_PER_ARM and
                 EVALUATION_UPDATES[-1] in evaluations,
                 "update-500 checkpoint requires complete update/evaluation state")
        _require(isinstance(artifacts.get("checkpoint_update500.pt"), str) and
                 bool(artifacts["checkpoint_update500.pt"].strip()),
                 "present update-500 checkpoint requires artifact identity")
    else:
        _require("checkpoint_update500.pt" not in artifacts,
                 "absent update-500 checkpoint cannot have artifact identity")

    if state == TERMINAL_COMPLETED:
        _require(steps == logged == stop_update == UPDATES_PER_ARM,
                 "completed arm must contain exactly 500 complete updates")
        _require(evaluations == list(EVALUATION_UPDATES),
                 "completed arm is missing a required evaluation")
        _require(receipt["update500_checkpoint_present"] is True,
                 "completed arm requires the update-500 checkpoint")
        _require(receipt["reason"] is None, "completed arm cannot carry a stop reason")
        _require(receipt["finite_status"] is True,
                 "completed arm must have finite status")
        _require(all(value == 0 for value in hard_counts.values()),
                 "completed arm cannot contain hard-constraint violations")
    elif state == TERMINAL_EXECUTION_FAILED:
        _require(isinstance(receipt["reason"], str) and bool(receipt["reason"].strip()),
                 "failed arm requires an explicit reason")
    else:
        _require(arm in (ARM_ANCHOR_0, ARM_ANCHOR_25),
                 "method-inapplicable state is anchor-only")
        _require(receipt["reason"] == "ANCHOR_STATIONARY_OR_INAPPLICABLE",
                 "method-inapplicable reason drift")
        _require(receipt["update500_checkpoint_present"] is False,
                 "method-inapplicable arm cannot require a final checkpoint")
        _require(receipt["finite_status"] is True,
                 "method-inapplicable arm must remain finite")
        _require(all(value == 0 for value in hard_counts.values()),
                 "method-inapplicable arm cannot contain hard-constraint violations")


def cross_arm_performance_eligible(*, shared_identity_pass: bool,
                                   replay_gate_pass: bool) -> bool:
    """Freeze the two shared preconditions for any cross-arm performance claim."""
    return shared_identity_pass is True and replay_gate_pass is True


def build_schedule(cycles: tuple[int, ...] = EXPECTED_CYCLES) -> tuple[int, ...]:
    _require(cycles == EXPECTED_CYCLES, "noncanonical cycle schedule")
    schedule = tuple(cycles[index % len(cycles)] for index in range(UPDATES_PER_ARM))
    _require(len(schedule) == UPDATES_PER_ARM and schedule[-1] == 4,
             "500-update schedule construction failure")
    return schedule


def _direction_with_damage_reference(model: torch.nn.Module,
                                     losses: Mapping[str, torch.Tensor],
                                     arm: str) -> tuple[torch.Tensor, torch.Tensor, dict[str, Any]]:
    """Build one direction and preserve g_D from the same forward graph.

    The public core helper consumes its graph while building the direction.  A
    runner additionally needs g_D for the actual AdamW displacement diagnostic,
    so the complete objective set is differentiated once here.  Tests require
    this direction to match the reviewed public helper exactly.
    """
    if arm == ARM_REPLAY:
        objectives = {**replay_losses(losses), "L_D_alignment": grouped_losses(losses)["L_D"]}
        vectors, layout = flattened_objective_gradients(model, objectives)
        replay_vectors = [vectors[name] for name in ("J_N", "J_H", "J_P")]
        replay_norms = torch.stack([value.norm() for value in replay_vectors])
        if not torch.isfinite(replay_norms).all():
            raise FloatingPointError("nonfinite norm at frozen replay-merger boundary")
        merged, old = merge_objective_gradients(
            replay_vectors, clip_norm=GLOBAL_CLIP_NORM, eps=NORM_EPSILON)
        diagnostic_names = (
            "raw_norms", "reference_norm", "merged_norm_before_clip",
            "merged_norm_after_clip", "balanced_norms", "projected_norms",
        )
        if (not torch.isfinite(merged).all() or
                any(not torch.isfinite(torch.as_tensor(old[name])).all()
                    for name in diagnostic_names)):
            raise FloatingPointError("nonfinite frozen replay direction or diagnostic")
        return merged, vectors["L_D_alignment"], {
            "arm": arm, "layout": layout, "clip_count_for_complete_direction": 1,
            "exact_replay_merger": old,
        }
    groups = grouped_losses(losses)
    vectors, layout = flattened_objective_gradients(model, groups)
    if arm == ARM_SCALAR:
        merged, diagnostic = scalar_data_direction(vectors)
    else:
        merged, diagnostic = damage_anchor_direction(
            vectors, beta=0.0 if arm == ARM_ANCHOR_0 else 0.25)
    return merged, vectors["L_D"], {**diagnostic, "layout": layout}


@dataclass
class IntegrationBundle:
    base_runtime: Runtime
    arm_runtimes: dict[str, Runtime]
    optimizers: dict[str, torch.optim.AdamW]
    schedule: tuple[int, ...]
    receipt: dict[str, Any]


def build_no_training_integration(*, packet_dir: Path, base_config_path: Path,
                                  integration_config_path: Path,
                                  device: torch.device,
                                  synthetic_test_adapter: bool = False) -> IntegrationBundle:
    """Construct and exercise the full integration without an optimiser step."""
    config = _load_json(integration_config_path)
    validate_integration_config(
        config,
        base_config_path=base_config_path,
        synthetic_test_adapter=synthetic_test_adapter,
    )
    _require(device.type == "cpu", "no-training integration is CPU-only")
    torch.manual_seed(int(config["model"]["seed"]))
    base_runtime = build_runtime(packet_dir=packet_dir, config_path=base_config_path,
                                 device=device, executable=False)
    opt = config["optimisation"]
    models, optimizers, isolation = initialise_arm_states(
        base_runtime.model, learning_rate=opt["learning_rate"],
        betas=tuple(opt["betas"]), optimizer_epsilon=opt["epsilon"],
        weight_decay=opt["weight_decay"])
    for arm in ARM_ORDER:
        model_ids = {id(parameter) for parameter in models[arm].parameters()}
        optimizer_ids = {
            id(parameter) for group in optimizers[arm].param_groups for parameter in group["params"]
        }
        _require(optimizer_ids == model_ids, f"optimizer/model parameter binding mismatch: {arm}")
    isolation["optimizer_parameters_match_arm_models"] = True
    arm_runtimes = {arm: replace(base_runtime, model=model) for arm, model in models.items()}
    before_hashes = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    directions: dict[str, Any] = {}
    for arm in ARM_ORDER:
        runtime = arm_runtimes[arm]
        losses, _ = atomic_losses(runtime, index=0)
        direction, g_d, diagnostic = _direction_with_damage_reference(runtime.model, losses, arm)
        _require(diagnostic["layout"]["parameter_order"] == flattened_parameters(runtime.model)[1],
                 f"parameter order mismatch: {arm}")
        directions[arm] = {
            "direction_sha256": _direction_sha256(direction),
            "damage_gradient_sha256": _direction_sha256(g_d),
            "direction_norm": float(torch.linalg.vector_norm(direction).detach().cpu()),
            "damage_gradient_norm": float(torch.linalg.vector_norm(g_d).detach().cpu()),
            "vector_length": int(direction.numel()),
            "clip_count_for_complete_direction": diagnostic["clip_count_for_complete_direction"],
        }
    after_hashes = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    _require(before_hashes == after_hashes, "direction preflight mutated an arm model")
    _require(all(not optimizer.state for optimizer in optimizers.values()),
             "direction preflight populated an optimizer state")
    schedule = build_schedule()
    schedule_raw = np.asarray(schedule, dtype=np.int64).tobytes()
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
        "schedule_sha256": hashlib.sha256(schedule_raw).hexdigest(),
        "schedule_first_16": list(schedule[:16]),
        "schedule_last_4": list(schedule[-4:]),
        "isolation": isolation,
        "model_hashes_unchanged": before_hashes == after_hashes,
        "optimizer_states_empty_after_direction_preflight": True,
        "directions": directions,
    }
    canonical_json(receipt)
    return IntegrationBundle(base_runtime, arm_runtimes, optimizers, schedule, receipt)


def write_no_training_receipt(bundle: IntegrationBundle, output_path: Path) -> None:
    """Write one local, non-producer receipt after all checks have passed."""
    _require(bundle.receipt.get("execution_authorized") is False,
             "producer-authorised receipt is forbidden here", PermissionError)
    _require(not output_path.exists(), "receipt output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(bundle.receipt))
