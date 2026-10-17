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
    arm_direction,
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


def validate_integration_config(config: Mapping[str, Any], *, base_config_path: Path) -> None:
    """Fail closed on drift from the design-reviewed no-training contract."""
    _require(config.get("schema_version") == SCHEMA_VERSION, "integration schema drift")
    _require(config.get("planned_run_id") == PLANNED_RUN_ID, "planned run identity drift")
    _require(config.get("status") == "RUNNER_INTEGRATION_CANDIDATE__NO_TRAINING",
             "integration status drift")
    _require(config.get("execution_authorized") is False,
             "no-training integration must remain unauthorised", PermissionError)
    source = config.get("source", {})
    _require(source.get("core_code_ready_commit") == EXPECTED_CORE_COMMIT,
             "reviewed core commit drift")
    _require(source.get("base_runtime_config") ==
             "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json",
             "base E008 runtime config path drift")
    _require(source.get("base_runtime_config_sha256") == sha256_file(base_config_path),
             "base E008 runtime config identity drift")
    _require(source.get("integration_reviewed_commit") ==
             "TO_BE_SET_AFTER_EXACT_COMMIT_REVIEW" and
             source.get("input_packet_sha256") == "TO_BE_LOCKED_FROM_REVIEWED_PACKET",
             "no-training source fields must remain unresolved")
    budget = config.get("budget", {})
    _require(budget.get("updates_per_arm") == UPDATES_PER_ARM and
             budget.get("total_update_cap") == TOTAL_UPDATE_CAP,
             "four-arm budget drift")
    _require(tuple(budget.get("evaluation_updates", ())) == EVALUATION_UPDATES,
             "evaluation schedule drift")
    data = config.get("data", {})
    _require(tuple(data.get("selected_cycles", ())) == EXPECTED_CYCLES,
             "cycle order drift")
    _require(data.get("batch_size") == 1, "batch size drift")
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
    _require(all(optimisation.get(key) == value for key, value in expected_optimisation.items()),
             "optimisation contract drift")
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
    _require(evidence.get("required_per_arm") == [
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "checkpoint_update500.pt", "termination_receipt.json",
    ], "per-arm evidence contract drift")
    _require(evidence.get("required_shared") == [
        "config_resolved.json", "input_packet_identity.json", "environment.txt",
        "decision_metrics.json", "decision_table.csv", "decision_figure.png",
        "per_cycle_metrics.csv", "decision.md", "completion_receipt.json",
    ], "shared evidence contract drift")


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
                                  device: torch.device) -> IntegrationBundle:
    """Construct and exercise the full integration without an optimiser step."""
    config = _load_json(integration_config_path)
    validate_integration_config(config, base_config_path=base_config_path)
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
