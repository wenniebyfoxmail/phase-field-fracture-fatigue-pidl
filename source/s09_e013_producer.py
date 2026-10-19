"""Bounded two-arm producer for the S09-E013 local-support ranking experiment."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import time
from typing import Any, Mapping

import numpy as np
import torch

from s09_code_identity import current_commit
from s09_e009_four_arm import (
    LOSS_ORDER,
    NORM_EPSILON,
    _stable_l2_norm,
    atomic_losses,
    flattened_objective_gradients,
    flattened_parameters,
    grouped_losses,
    parameter_state_sha256,
)
from s09_e010_producer import (
    HARD_CONSTRAINT_KEYS,
    PROJECTION_COUNT_KEYS,
    _validate_evaluation_record,
    evaluate_arm,
)
from s09_e010_support_amplitude import support_amplitude_losses
from s09_e013_local_ranking_objective import (
    ARM_GLOBAL,
    ARM_ORDER,
    ARM_LOCAL,
    GROWTH_CYCLES,
    NEAR_STAGNANT_CYCLES,
    OBJECTIVE_ORDER,
    PAIR_ORDER,
    UPDATES_PER_ARM,
    classify_e013,
    merge_ranking_gradients,
    pair_mean_objectives,
    pair_schedule,
    ranking_direction,
    ranking_loss,
    local_support_score,
    weighted_amplitude,
)
from s09_stage0a_p1_packet import canonical_json, sha256_file
from s09_stage0a_p1_trainer import (
    assign_merged_gradient,
    build_runtime,
    gpu_identity,
    hard_constraint_report,
    proposal_projection_diagnostics,
)


SCHEMA_VERSION = "s09-e013-local-ranking-producer-v1"
RUN_ID = "S09-E013-R001-localisation-aware-ranking"
MODULE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BASE_CONFIG_SHA256 = "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
EXPECTED_PACKET_MANIFEST_SHA256 = "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
EXPECTED_B25_CHECKPOINT_SHA256 = "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05"
EXPECTED_E011_DECISION_SHA256 = "520c2e475cd40a9ebe9d9b8c9c666358ca65fd891766edf248610d1e1889e433"
EXPECTED_E011_RANKING_CHECKPOINT_SHA256 = "a3f2f83bd2c86f8bc3a455c899ddc5ea0d5e394b8b6f5930950d4e5dbb024c8d"
EVALUATION_UPDATES = (0, 16, 64, 128, 256, 496, 500)
EXPECTED_HOSTNAME = "GPUServer8"
EXPECTED_CUDA_VISIBLE_DEVICES = "5"
EXPECTED_GPU_UUID = "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
EXPECTED_REMOTE_ROOT = "/mnt/data2/drtao/wennie/S09-E013-R001-localisation-aware-ranking"
EXPECTED_OUTPUT_ROOT = EXPECTED_REMOTE_ROOT + "/run"
EXPECTED_ARCHIVE_ROOT = "/mnt/data2/drtao/pidl_archives/S09-E013-R001-localisation-aware-ranking"
EXPECTED_CODE_ROOT = EXPECTED_REMOTE_ROOT + "/code"
WALL_TIME_CAP_SECONDS = 3600.0
# Filled from the canonical files and checked again by the entry point.
EXPECTED_RUN_CONFIG_SHA256 = "a901780781038000a5a2b514c4946d44d23dede1ab2d091363f9e87922eceb1e"
EXPECTED_PROTOCOL_SHA256 = "bd7d8535d39fab8c8ccab8bc99de0df14797d188c9daf4b18f3208f98439e209"
PRODUCER_FILES = (
    # The complete source tree is a deliberately conservative transitive
    # dependency closure for the runtime/model/physics/evaluator imports.
    "source",
    "scripts/run_s09_e013_producer.py",
    "docs/research/S09/S09-E013/experiment.md",
    "docs/research/S09/S09-E013/run_config.json",
)


@dataclass
class ArmRunResult:
    arm: str
    arm_dir: Path
    receipt: dict[str, Any]
    evaluations: dict[int, dict[str, Any]]


class ArmReceiptCloseError(RuntimeError):
    def __init__(self, message: str, result: ArmRunResult):
        super().__init__(message)
        self.result = result


def _require(condition: bool, message: str, error: type[Exception] = ValueError) -> None:
    if not condition:
        raise error(message)


def _write_new(path: Path, payload: bytes) -> None:
    _require(not path.exists(), f"artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def _write_json(path: Path, value: Any) -> None:
    _write_new(path, canonical_json(value))


def _append_jsonl(stream: io.BufferedWriter, value: Any) -> None:
    stream.write(canonical_json(value))
    stream.flush()


def _append_durable_evaluation(
    stream: io.BufferedWriter,
    evaluations: dict[int, dict[str, Any]],
    update: int,
    evaluation: dict[str, Any],
) -> None:
    """Register an evaluation only after its JSONL row is durably flushed."""
    _append_jsonl(stream, evaluation)
    evaluations[update] = evaluation


def _restore_evaluation_key_order(record: Mapping[str, Any]) -> dict[str, Any]:
    """Restore frozen named-map order after canonical JSON sorts object keys.

    Canonical JSON is retained for deterministic evidence bytes. The inherited
    E010 validator also treats the order of four scientifically named maps as
    part of its schema, so the disk decoder first requires exact memberships and
    then reconstructs those maps in their frozen order.
    """
    _require(set(record) == {"aggregate", "per_cycle"},
             "evaluation record keys drift")
    aggregate_raw = record["aggregate"]
    rows_raw = record["per_cycle"]
    _require(isinstance(aggregate_raw, Mapping) and isinstance(rows_raw, list),
             "evaluation record shape drift")

    def ordered_named_map(value: Any, keys: tuple[str, ...], label: str):
        _require(isinstance(value, Mapping) and set(value) == set(keys),
                 f"{label} membership drift")
        return OrderedDict((key, value[key]) for key in keys)

    aggregate = dict(aggregate_raw)
    aggregate["hard_constraint_counts"] = ordered_named_map(
        aggregate.get("hard_constraint_counts"), HARD_CONSTRAINT_KEYS,
        "aggregate hard-constraint counts",
    )
    rows = []
    for raw in rows_raw:
        _require(isinstance(raw, Mapping), "per-cycle record shape drift")
        row = dict(raw)
        row["atomic_losses"] = ordered_named_map(
            row.get("atomic_losses"), LOSS_ORDER, "per-cycle atomic losses")
        row["grouped_losses"] = ordered_named_map(
            row.get("grouped_losses"), ("L_D", "L_U", "L_H", "L_P"),
            "per-cycle grouped losses",
        )
        row["projection_counts"] = ordered_named_map(
            row.get("projection_counts"), PROJECTION_COUNT_KEYS,
            "per-cycle projection counts",
        )
        row["hard_constraint_counts"] = ordered_named_map(
            row.get("hard_constraint_counts"), HARD_CONSTRAINT_KEYS,
            "per-cycle hard-constraint counts",
        )
        rows.append(row)
    return {"aggregate": aggregate, "per_cycle": rows}


def _optimizer_step_before_deadline(
    optimizer: torch.optim.AdamW, deadline: float, stage: str,
) -> None:
    """Do not begin an avoidable optimizer mutation after the wall cap."""
    _check_deadline(deadline, stage)
    optimizer.step()


def _cleanup_partial_checkpoint(path: Path) -> str | None:
    """Return cleanup failure text so arm progress can still be receipted."""
    try:
        path.unlink(missing_ok=True)
    except BaseException as error:
        return f"CHECKPOINT_CLEANUP_FAILED: {type(error).__name__}: {error}"
    return None


def _load_strict_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _check_deadline(deadline: float, stage: str) -> None:
    _require(time.time() < deadline, f"WALL_TIME_CAP_REACHED:{stage}", TimeoutError)


def _bound_repo_root(repo_root: Path) -> Path:
    observed = repo_root.resolve(strict=True)
    _require(observed == MODULE_ROOT, "repo root differs from executing module")
    return observed


def _canonical_exact_path(path: Path, expected: str, label: str) -> Path:
    _require(path.is_absolute(), f"{label} must be absolute")
    _require(path == Path(os.path.normpath(str(path))), f"{label} is noncanonical")
    _require(path == Path(expected), f"{label} differs from frozen run config")
    parent = path.parent.resolve(strict=True)
    _require(parent == Path(expected).parent, f"{label} parent resolves through a symlink")
    return path


def _environment(visible: str) -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "CUDA_VISIBLE_DEVICES": visible,
        "gpu": gpu_identity(visible),
    }


def _execution_files_clean(root: Path) -> bool:
    tracked = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *PRODUCER_FILES], cwd=root
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *PRODUCER_FILES],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return tracked.returncode == 0 and not untracked.stdout.strip()


def _validate_run_binding(
    *, run_config: Path, protocol: Path, output_dir: Path, archive_dir: Path,
    repo_root: Path, expected_commit: str,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    repo_root = _bound_repo_root(repo_root)
    _require(sha256_file(run_config) == EXPECTED_RUN_CONFIG_SHA256,
             "run config identity mismatch")
    _require(sha256_file(protocol) == EXPECTED_PROTOCOL_SHA256,
             "protocol identity mismatch")
    config = _load_strict_json(run_config)
    _require(run_config.read_bytes() == canonical_json(config),
             "run config is not canonical JSON")
    producer = config.get("producer", {})
    _require(producer.get("hostname") == EXPECTED_HOSTNAME and
             producer.get("CUDA_VISIBLE_DEVICES") == EXPECTED_CUDA_VISIBLE_DEVICES and
             producer.get("gpu_uuid") == EXPECTED_GPU_UUID and
             producer.get("code_root") == EXPECTED_CODE_ROOT and
             producer.get("output_root") == EXPECTED_OUTPUT_ROOT and
             producer.get("archive_root") == EXPECTED_ARCHIVE_ROOT,
             "run config producer binding drift")
    _require(producer.get("wall_time_cap_seconds") == WALL_TIME_CAP_SECONDS,
             "wall-time cap drift")
    _require(str(repo_root) == EXPECTED_CODE_ROOT, "executing code root drift")
    output = _canonical_exact_path(output_dir, EXPECTED_OUTPUT_ROOT, "output root")
    archive = _canonical_exact_path(archive_dir, EXPECTED_ARCHIVE_ROOT, "archive root")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible == EXPECTED_CUDA_VISIBLE_DEVICES,
             "CUDA_VISIBLE_DEVICES differs from frozen binding")
    environment = _environment(visible)
    _require(environment["hostname"] == EXPECTED_HOSTNAME,
             "producer hostname differs from frozen binding")
    _require(environment["gpu"].get("uuid") == EXPECTED_GPU_UUID,
             "physical GPU UUID differs from frozen binding")
    _require(current_commit(repo_root) == expected_commit,
             "commit identity mismatch")
    _require(_execution_files_clean(repo_root), "execution dependency is dirty")
    return config, environment, output, archive


def _optimizer_state_sha256(optimizer: torch.optim.AdamW) -> str:
    buffer = io.BytesIO()
    torch.save(optimizer.state_dict(), buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _pair_objectives(runtime: Any, growth_index: int, stagnant_index: int, arm: str):
    _require(arm in ARM_ORDER, "unknown arm")
    per_cycle = []
    for index in (growth_index, stagnant_index):
        losses, context = atomic_losses(runtime, index)
        additions, addition_record = support_amplitude_losses(
            predicted_peak=context["output"]["d_peak"],
            target_peak=context["target"]["d_peak"],
            damage_pre=context["d_pre"],
            nodal_weight=context["output"]["nodal_weight"],
        )
        groups = grouped_losses(losses)
        objectives = OrderedDict((
            ("L_D", groups["L_D"]),
            ("L_S", additions["L_S"]),
            ("L_A", additions["L_A"]),
            ("L_U", groups["L_U"]),
            ("L_H", groups["L_H"]),
            ("L_P", groups["L_P"]),
        ))
        amplitude = weighted_amplitude(
            context["output"]["d_peak"], context["d_pre"],
            context["output"]["nodal_weight"],
        )
        local_score, local_record = local_support_score(
            context["output"]["d_peak"], context["d_pre"],
            context["target"]["d_peak"], context["output"]["nodal_weight"],
        )
        per_cycle.append((losses, context, objectives, amplitude, addition_record,
                          local_score, local_record))
    selected = 3 if arm == ARM_GLOBAL else 5
    rank, rank_record = ranking_loss(per_cycle[0][selected], per_cycle[1][selected])
    rank_record["observable"] = (
        "global_weighted_absolute_increment" if arm == ARM_GLOBAL
        else "target_support_minus_background_positive_increment"
    )
    objectives = pair_mean_objectives(per_cycle[0][2], per_cycle[1][2], rank)
    global_margin = per_cycle[0][3] - per_cycle[1][3]
    local_margin = per_cycle[0][5] - per_cycle[1][5]
    return objectives, global_margin, local_margin, rank_record, per_cycle


def _adamw_displacement(
    model: torch.nn.Module,
    optimizer: torch.optim.AdamW,
    gradient: torch.Tensor,
    parameter_order: list[str],
) -> torch.Tensor:
    """Predict the exact next AdamW displacement without mutating state."""
    named = list(model.named_parameters())
    _require([name for name, _ in named] == parameter_order, "parameter order drift")
    _require(len(optimizer.param_groups) == 1, "exactly one AdamW group required")
    group = optimizer.param_groups[0]
    _require(group["weight_decay"] == 0.0 and not group["amsgrad"],
             "unsupported AdamW option")
    beta1, beta2 = group["betas"]
    lr, eps = group["lr"], group["eps"]
    blocks = []
    cursor = 0
    for _, parameter in named:
        count = parameter.numel()
        block = gradient[cursor:cursor + count].reshape_as(parameter)
        cursor += count
        state = optimizer.state[parameter]
        step_raw = state["step"]
        step = int(step_raw.item() if torch.is_tensor(step_raw) else step_raw) + 1
        exp_avg = state["exp_avg"]
        exp_avg_sq = state["exp_avg_sq"]
        next_avg = beta1 * exp_avg + (1.0 - beta1) * block
        next_sq = beta2 * exp_avg_sq + (1.0 - beta2) * block.square()
        bias1 = 1.0 - beta1**step
        bias2 = 1.0 - beta2**step
        denominator = next_sq.sqrt() / math.sqrt(bias2) + eps
        delta = -(lr / bias1) * next_avg / denominator
        blocks.append(delta.reshape(-1))
    _require(cursor == gradient.numel(), "gradient length drift")
    displacement = torch.cat(blocks)
    _require(torch.isfinite(displacement).all().item(), "nonfinite AdamW displacement")
    return displacement


def _classify_zero_step_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    wrong = [row for row in records if row["initial_local_outcome"] == "LOSS"]
    correct_global = [row for row in records if row["initial_global_outcome"] == "WIN"]
    expected_wrong = {
        (growth, stagnant) for growth in (58, 60, 69, 70) for stagnant in (3, 4)
    }
    expected_correct_global = set(PAIR_ORDER) - expected_wrong
    observed_wrong = {(row["growth_cycle"], row["stagnant_cycle"]) for row in wrong}
    observed_correct_global = {
        (row["growth_cycle"], row["stagnant_cycle"]) for row in correct_global
    }
    usable_wrong = [row for row in wrong if row["local_contrast_gradient_usable"]]
    wrong_positive = {
        arm: sum(row["arms"][arm]["predicted_adamw_local_margin_change"] > 0
                 for row in wrong)
        for arm in ARM_ORDER
    }
    correct_flips = sum(
        row["initial_global_margin"]
        + row["arms"][ARM_LOCAL]["predicted_adamw_global_margin_change"] <= 0
        for row in correct_global
    )
    wrong_rank = [row["arms"][ARM_LOCAL]["predicted_adamw_local_margin_change"]
                  for row in wrong]
    wrong_control = [row["arms"][ARM_GLOBAL]["predicted_adamw_local_margin_change"]
                     for row in wrong]
    finite = all(math.isfinite(value) for value in wrong_rank + wrong_control)
    gate = (
        len(records) == len(PAIR_ORDER)
        and len(wrong) == 8
        and len(usable_wrong) == 8
        and len(correct_global) == 17
        and observed_wrong == expected_wrong
        and observed_correct_global == expected_correct_global
        and wrong_positive[ARM_LOCAL] >= 1
        and wrong_positive[ARM_LOCAL] > wrong_positive[ARM_GLOBAL]
        and correct_flips <= 3
        and finite
    )
    return {
        "passed": gate,
        "wrong_pair_count": len(wrong),
        "usable_wrong_local_pair_count": len(usable_wrong),
        "correct_global_pair_count": len(correct_global),
        "wrong_local_pair_identity_matches_frozen": observed_wrong == expected_wrong,
        "correct_global_pair_identity_matches_frozen": (
            observed_correct_global == expected_correct_global
        ),
        "predicted_adamw_increases_wrong_local_margin_count": wrong_positive,
        "local_arm_predicted_adamw_flips_correct_global_margin_count": int(correct_flips),
        "wrong_margin_changes_finite": finite,
        "directional_tier": (
            "COMPLETE_8_OF_8" if wrong_positive[ARM_LOCAL] == 8 else
            "STRONG_6_OR_7" if wrong_positive[ARM_LOCAL] >= 6 else
            "DIRECTIONAL_1_TO_5" if wrong_positive[ARM_LOCAL] >= 1 else "NONE"
        ),
        "median_wrong_margin_change": {
            ARM_GLOBAL: None if not wrong_control else float(np.median(wrong_control)),
            ARM_LOCAL: None if not wrong_rank else float(np.median(wrong_rank)),
        },
    }


def zero_step_audit(
    runtime: Any, optimizer: torch.optim.AdamW, *, deadline: float,
    progress_stream: io.BufferedWriter | None = None,
) -> dict[str, Any]:
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    cycle_to_index = {cycle: index for index, cycle in enumerate(cycles)}
    before_hash = parameter_state_sha256(runtime.model)
    optimizer_hash = _optimizer_state_sha256(optimizer)
    records = []
    for growth_cycle, stagnant_cycle in PAIR_ORDER:
        arm_records = {}
        for arm in ARM_ORDER:
            stage = f"zero_step:{growth_cycle}_{stagnant_cycle}:{arm}"
            _check_deadline(deadline, f"{stage}:before")
            objectives, global_margin, local_margin, rank_record, _ = _pair_objectives(
                runtime, cycle_to_index[growth_cycle], cycle_to_index[stagnant_cycle], arm
            )
            augmented = OrderedDict(objectives)
            augmented["global_margin"] = global_margin
            augmented["local_margin"] = local_margin
            gradients, layout = flattened_objective_gradients(runtime.model, augmented)
            objective_gradients = OrderedDict((name, gradients[name]) for name in OBJECTIVE_ORDER)
            direction, diagnostic = merge_ranking_gradients(
                objective_gradients, arm, layout={
                    "parameter_order": layout["parameter_order"],
                    "objectives": {
                        name: layout["objectives"][name] for name in OBJECTIVE_ORDER
                    },
                }
            )
            displacement = _adamw_displacement(
                runtime.model, optimizer, direction, layout["parameter_order"]
            )
            local_gradient_norm = float(
                _stable_l2_norm(gradients["local_margin"]).detach().cpu())
            local_gradient_finite = bool(
                torch.isfinite(gradients["local_margin"]).all().item())
            arm_records[arm] = {
                "selected_observable": rank_record["observable"],
                "initial_global_margin": float(global_margin.detach().cpu()),
                "initial_local_margin": float(local_margin.detach().cpu()),
                "predicted_adamw_global_margin_change": float(
                    gradients["global_margin"].dot(displacement).detach().cpu()
                ),
                "predicted_adamw_local_margin_change": float(
                    gradients["local_margin"].dot(displacement).detach().cpu()
                ),
                "predicted_adamw_L_D_change": float(
                    gradients["L_D"].dot(displacement).detach().cpu()
                ),
                "predicted_adamw_L_P_change": float(
                    gradients["L_P"].dot(displacement).detach().cpu()
                ),
                "predicted_parameter_displacement_norm": float(
                    torch.linalg.vector_norm(displacement).detach().cpu()
                ),
                "direction_norm": float(torch.linalg.vector_norm(direction).cpu()),
                "rank_projected_norm": diagnostic["rank"]["projected_norm"],
                "local_margin_gradient_norm": local_gradient_norm,
                "local_margin_gradient_finite": local_gradient_finite,
                "local_margin_gradient_usable": (
                    local_gradient_finite and local_gradient_norm > NORM_EPSILON
                ),
                "clip_applied": diagnostic["clip_applied"],
            }
            if progress_stream is not None:
                _append_jsonl(progress_stream, {
                    "growth_cycle": growth_cycle,
                    "stagnant_cycle": stagnant_cycle,
                    "arm": arm,
                    "record": arm_records[arm],
                })
            _check_deadline(deadline, f"{stage}:after")
        _require(math.isclose(
            arm_records[ARM_GLOBAL]["initial_global_margin"],
            arm_records[ARM_LOCAL]["initial_global_margin"], rel_tol=0.0, abs_tol=0.0),
            "arm-specific initial global margin drift")
        _require(math.isclose(
            arm_records[ARM_GLOBAL]["initial_local_margin"],
            arm_records[ARM_LOCAL]["initial_local_margin"], rel_tol=0.0, abs_tol=0.0),
            "arm-specific initial local margin drift")
        records.append({
            "growth_cycle": growth_cycle,
            "stagnant_cycle": stagnant_cycle,
            "initial_global_outcome": "WIN" if arm_records[ARM_GLOBAL]["initial_global_margin"] > 0 else "LOSS",
            "initial_local_outcome": "WIN" if arm_records[ARM_GLOBAL]["initial_local_margin"] > 0 else "LOSS",
            "initial_global_margin": arm_records[ARM_GLOBAL]["initial_global_margin"],
            "initial_local_margin": arm_records[ARM_GLOBAL]["initial_local_margin"],
            "local_contrast_gradient_usable": all(
                arm_records[arm]["local_margin_gradient_usable"] for arm in ARM_ORDER
            ),
            "arms": arm_records,
        })
    _check_deadline(deadline, "zero_step:before_admission_publication")
    summary = _classify_zero_step_records(records)
    _require(parameter_state_sha256(runtime.model) == before_hash,
             "zero-step audit changed model")
    _require(_optimizer_state_sha256(optimizer) == optimizer_hash,
             "zero-step audit changed optimizer")
    return {
        "status": "ZERO_STEP_DIRECTION_READY" if summary["passed"] else "ZERO_STEP_DIRECTION_STOP",
        **summary,
        "optimizer_steps_performed": 0,
        "initial_model_state_sha256": before_hash,
        "initial_optimizer_state_sha256": optimizer_hash,
        "records": records,
        "interpretation": (
            "First-order replay of the exact merged/projected direction through the next "
            "AdamW update state; it is not a guarantee of finite-step repair."
        ),
    }


def _initialise_arms(runtime: Any, checkpoint: Mapping[str, Any]):
    models = {arm: copy.deepcopy(runtime.model) for arm in ARM_ORDER}
    optimizers = {}
    for arm, model in models.items():
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=0.0003, betas=(0.9, 0.999), eps=1e-8,
            weight_decay=0.0,
        )
        optimizer.load_state_dict(copy.deepcopy(checkpoint["optimizer"]))
        optimizers[arm] = optimizer
    model_hashes = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    optimizer_hashes = {arm: _optimizer_state_sha256(opt) for arm, opt in optimizers.items()}
    _require(len(set(model_hashes.values())) == 1, "initial model identity drift")
    _require(len(set(optimizer_hashes.values())) == 1, "initial optimizer identity drift")
    return models, optimizers, {
        "model_state_sha256": next(iter(model_hashes.values())),
        "optimizer_state_sha256": next(iter(optimizer_hashes.values())),
    }


def _train_arm(
    *, arm: str, runtime: Any, optimizer: torch.optim.AdamW, output: Path,
    initial_identity: Mapping[str, Any], deadline: float,
) -> ArmRunResult:
    _require(arm in ARM_ORDER, "unknown arm")
    _require(not output.exists(), "arm output exists")
    output.mkdir(parents=True)
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    cycle_to_index = {cycle: index for index, cycle in enumerate(cycles)}
    schedule = pair_schedule()
    start_record = {
        "arm": arm,
        **dict(initial_identity),
        "pair_schedule": [list(pair) for pair in schedule],
        "updates_per_arm": UPDATES_PER_ARM,
    }
    _write_json(output / "start_identity.json", start_record)
    evaluations: dict[int, dict[str, Any]] = {}
    steps = logged = 0
    reason: str | None = None
    terminal_state = "EXECUTION_FAILED"
    finite = True
    checkpoint_present = False
    checkpoint_path = output / "checkpoint_update500.pt"
    checkpoint_partial = output / ".checkpoint_update500.pt.partial"
    try:
        with (output / "train_log.jsonl").open("xb") as train_stream, \
             (output / "gradient_diagnostics.jsonl").open("xb") as gradient_stream, \
             (output / "diagnostic_metrics.jsonl").open("xb") as diagnostic_stream:
            _check_deadline(deadline, f"{arm}:initial_evaluation_before")
            initial = evaluate_arm(runtime, update=0)
            _validate_evaluation_record(initial, 0)
            _check_deadline(deadline, f"{arm}:initial_evaluation_after")
            _append_durable_evaluation(diagnostic_stream, evaluations, 0, initial)
            for update, (growth_cycle, stagnant_cycle) in enumerate(schedule, 1):
                _check_deadline(deadline, f"{arm}:update_{update}_before")
                runtime.model.train()
                optimizer.zero_grad(set_to_none=True)
                objectives, _, _, rank_record, per_cycle = _pair_objectives(
                    runtime, cycle_to_index[growth_cycle], cycle_to_index[stagnant_cycle], arm
                )
                hard_records = []
                projection_records = []
                for _, context, _, _, _, _, _ in per_cycle:
                    hard = hard_constraint_report(
                        runtime, context["d_pre"], context["history_pre"], context["output"]
                    )
                    _require(sum(hard.values()) == 0,
                             "per-update hard-constraint violation")
                    hard_records.append(hard)
                    projection_records.append(proposal_projection_diagnostics(
                        runtime, context["d_pre"], context["output"]
                    ))
                direction, diagnostic, gradients = ranking_direction(
                    runtime.model, objectives, arm
                )
                before, parameter_order = flattened_parameters(runtime.model)
                _require(diagnostic["layout"]["parameter_order"] == parameter_order,
                         "parameter order drift")
                assign_merged_gradient(runtime.model, direction, parameter_order)
                _optimizer_step_before_deadline(
                    optimizer, deadline, f"{arm}:update_{update}_pre_step")
                steps = update
                after, after_order = flattened_parameters(runtime.model)
                _require(after_order == parameter_order,
                         "post-step parameter order drift")
                displacement = after - before
                train_row = {
                    "update": update, "growth_cycle": growth_cycle,
                    "stagnant_cycle": stagnant_cycle,
                    "pair_index": (update - 1) % len(PAIR_ORDER),
                    "ranking_record": rank_record,
                    "objectives": {name: float(value.detach().cpu())
                                   for name, value in objectives.items()},
                    "hard_constraint_counts": hard_records,
                    "proposal_projection_counts": projection_records,
                }
                gradient_row = {
                    "update": update, "growth_cycle": growth_cycle,
                    "stagnant_cycle": stagnant_cycle,
                    "direction_sha256": hashlib.sha256(
                        direction.detach().cpu().numpy().tobytes()).hexdigest(),
                    "direction_norm": float(torch.linalg.vector_norm(direction).cpu()),
                    "parameter_displacement_norm": float(
                        torch.linalg.vector_norm(displacement).cpu()),
                    "ranking_loss_change_along_displacement": float(
                        gradients["L_R"].dot(displacement).detach().cpu()),
                    "direction_diagnostics": diagnostic,
                }
                _append_jsonl(train_stream, train_row)
                _append_jsonl(gradient_stream, gradient_row)
                logged = update
                if update in EVALUATION_UPDATES[1:]:
                    _check_deadline(deadline, f"{arm}:evaluation_{update}_before")
                    evaluation = evaluate_arm(runtime, update=update)
                    _validate_evaluation_record(evaluation, update)
                    _check_deadline(deadline, f"{arm}:evaluation_{update}_after")
                    _append_durable_evaluation(
                        diagnostic_stream, evaluations, update, evaluation)
        _check_deadline(deadline, f"{arm}:checkpoint_before")
        torch.save({
            "model": runtime.model.state_dict(), "optimizer": optimizer.state_dict(),
            "update": UPDATES_PER_ARM, "arm": arm, "source_run": RUN_ID,
        }, checkpoint_partial)
        _require(checkpoint_partial.is_file(), "checkpoint write produced no file")
        os.replace(checkpoint_partial, checkpoint_path)
        checkpoint_present = True
        _check_deadline(deadline, f"{arm}:checkpoint_after")
        terminal_state = "COMPLETED"
    except BaseException as error:
        reason = f"{type(error).__name__}: {error}"
        finite = not isinstance(error, FloatingPointError)
    cleanup_failure = _cleanup_partial_checkpoint(checkpoint_partial)
    if cleanup_failure is not None:
        terminal_state = "EXECUTION_FAILED"
        reason = cleanup_failure if reason is None else f"{reason}; {cleanup_failure}"

    artifact_names = (
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "checkpoint_update500.pt",
    )
    artifacts = {}
    for name in artifact_names:
        path = output / name
        if path.is_file():
            try:
                artifacts[name] = sha256_file(path)
            except OSError as error:
                terminal_state = "EXECUTION_FAILED"
                reason = f"EVIDENCE_CLOSE_FAILED: {type(error).__name__}: {error}"
    if terminal_state == "COMPLETED" and (
        steps != UPDATES_PER_ARM or logged != UPDATES_PER_ARM or
        list(evaluations) != list(EVALUATION_UPDATES) or not checkpoint_present
    ):
        terminal_state = "EXECUTION_FAILED"
        reason = "COMPLETION_COUNTER_DRIFT"
    receipt = {
        "arm": arm, "terminal_state": terminal_state,
        "optimizer_steps_completed": steps, "fully_logged_updates": logged,
        "evaluation_updates_present": list(evaluations),
        "last_valid_evaluation_update": next(reversed(evaluations), None),
        "reason": reason, "update500_checkpoint_present": checkpoint_present,
        "finite": finite, "hard_constraint_violations": 0,
        "artifacts": artifacts,
    }
    result = ArmRunResult(arm, output, receipt, evaluations)
    try:
        _write_json(output / "termination_receipt.json", receipt)
    except BaseException as error:
        failed = dict(receipt)
        failed["terminal_state"] = "EXECUTION_FAILED"
        failed["reason"] = (
            "TERMINATION_RECEIPT_WRITE_FAILED: "
            f"{type(error).__name__}: {error}"
        )
        raise ArmReceiptCloseError(
            f"terminal receipt write failed for {arm}",
            ArmRunResult(arm, output, failed, evaluations),
        ) from error
    return result


def _pair_outcomes(rows: list[dict[str, Any]]) -> dict[tuple[int, int], str]:
    amplitudes = {row["cycle"]: row["predicted_damage_increment_abs_mean"] for row in rows}
    outcomes = {}
    for growth, stagnant in PAIR_ORDER:
        margin = amplitudes[growth] - amplitudes[stagnant]
        outcomes[(growth, stagnant)] = "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"
    return outcomes


def _local_support_metrics(
    fields: Mapping[str, np.ndarray], *, deadline: float, arm: str,
) -> dict[str, Any]:
    values = {}
    rows = []
    with torch.no_grad():
        for index, cycle_raw in enumerate(fields["cycles"]):
            stage = f"endpoint_local_metrics:{arm}:cycle_{int(cycle_raw)}"
            _check_deadline(deadline, f"{stage}:before")
            score, record = local_support_score(
                torch.as_tensor(fields["predicted_peak"][index], dtype=torch.float64).reshape(-1),
                torch.as_tensor(fields["d_pre"][index], dtype=torch.float64).reshape(-1),
                torch.as_tensor(fields["target_peak"][index], dtype=torch.float64).reshape(-1),
                torch.as_tensor(fields["nodal_weight"], dtype=torch.float64).reshape(-1),
            )
            cycle = int(cycle_raw)
            values[cycle] = float(score.detach().cpu())
            rows.append({"cycle": cycle, **record})
            _check_deadline(deadline, f"{stage}:after")
    wins = ties = losses = 0
    outcomes = {}
    for growth, stagnant in PAIR_ORDER:
        margin = values[growth] - values[stagnant]
        outcome = "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"
        outcomes[(growth, stagnant)] = outcome
        wins += outcome == "WIN"; ties += outcome == "TIE"; losses += outcome == "LOSS"
    return {
        "auc": {"value": (wins + 0.5 * ties) / len(PAIR_ORDER),
                "wins": int(wins), "ties": int(ties), "losses": int(losses)},
        "rows": rows,
        "outcomes": outcomes,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("rb") as stream:
        for line in stream:
            _require(line.endswith(b"\n"), f"unterminated JSONL row: {path.name}")
            rows.append(json.loads(
                line.decode("utf-8"),
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            ))
    return rows


def _validate_arm_on_disk(result: ArmRunResult) -> ArmRunResult:
    arm_dir = result.arm_dir
    receipt_path = arm_dir / "termination_receipt.json"
    receipt = _load_strict_json(receipt_path)
    _require(receipt_path.read_bytes() == canonical_json(receipt),
             f"noncanonical termination receipt: {result.arm}")
    _require(receipt_path.read_bytes() == canonical_json(result.receipt),
             f"in-memory/on-disk receipt drift: {result.arm}")
    _require(receipt.get("arm") == result.arm and
             receipt.get("terminal_state") == "COMPLETED" and
             type(receipt.get("optimizer_steps_completed")) is int and
             receipt.get("optimizer_steps_completed") == UPDATES_PER_ARM and
             type(receipt.get("fully_logged_updates")) is int and
             receipt.get("fully_logged_updates") == UPDATES_PER_ARM and
             receipt.get("evaluation_updates_present") == list(EVALUATION_UPDATES) and
             isinstance(receipt.get("evaluation_updates_present"), list) and
             all(type(value) is int
                 for value in receipt.get("evaluation_updates_present", ())) and
             type(receipt.get("last_valid_evaluation_update")) is int and
             receipt.get("last_valid_evaluation_update") == 500 and
             receipt.get("reason") is None and
             receipt.get("update500_checkpoint_present") is True and
             receipt.get("finite") is True and
             type(receipt.get("hard_constraint_violations")) is int and
             receipt.get("hard_constraint_violations") == 0,
             f"invalid completed receipt: {result.arm}")
    required_artifacts = {
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "checkpoint_update500.pt",
    }
    _require(set(receipt.get("artifacts", {})) == required_artifacts,
             f"artifact membership drift: {result.arm}")
    for name, expected in receipt["artifacts"].items():
        _require(sha256_file(arm_dir / name) == expected,
                 f"artifact hash drift: {result.arm}/{name}")
    start = _load_strict_json(arm_dir / "start_identity.json")
    _require(start.get("arm") == result.arm and
             start.get("updates_per_arm") == UPDATES_PER_ARM and
             start.get("pair_schedule") == [list(pair) for pair in pair_schedule()],
             f"start identity drift: {result.arm}")
    train_rows = _read_jsonl(arm_dir / "train_log.jsonl")
    gradient_rows = _read_jsonl(arm_dir / "gradient_diagnostics.jsonl")
    _require(len(train_rows) == len(gradient_rows) == UPDATES_PER_ARM and
             [row.get("update") for row in train_rows] == list(range(1, 501)) and
             [row.get("update") for row in gradient_rows] == list(range(1, 501)),
             f"update log coverage drift: {result.arm}")
    evaluation_rows = _read_jsonl(arm_dir / "diagnostic_metrics.jsonl")
    _require(len(evaluation_rows) == len(EVALUATION_UPDATES),
             f"evaluation row count drift: {result.arm}")
    evaluations = {}
    for update, record in zip(EVALUATION_UPDATES, evaluation_rows):
        record = _restore_evaluation_key_order(record)
        _validate_evaluation_record(record, update)
        _require(record["aggregate"]["hard_constraint_violations"] == 0,
                 f"hard-constraint drift: {result.arm}/{update}")
        evaluations[update] = record
    checkpoint = torch.load(
        arm_dir / "checkpoint_update500.pt", map_location="cpu", weights_only=False)
    _require(set(checkpoint) == {"model", "optimizer", "update", "arm", "source_run"} and
             isinstance(checkpoint.get("model"), Mapping) and
             isinstance(checkpoint.get("optimizer"), Mapping) and
             type(checkpoint.get("update")) is int and
             checkpoint.get("update") == UPDATES_PER_ARM and
             checkpoint.get("arm") == result.arm and
             checkpoint.get("source_run") == RUN_ID,
             f"checkpoint semantic identity drift: {result.arm}")
    return ArmRunResult(result.arm, arm_dir, receipt, evaluations)


def _require_nested_exact(left: Any, right: Any, label: str) -> None:
    if torch.is_tensor(left) or torch.is_tensor(right):
        _require(torch.is_tensor(left) and torch.is_tensor(right)
                 and left.dtype == right.dtype and left.shape == right.shape
                 and torch.equal(left.cpu(), right.cpu()), f"{label} tensor drift")
    elif isinstance(left, Mapping) or isinstance(right, Mapping):
        _require(isinstance(left, Mapping) and isinstance(right, Mapping)
                 and list(left) == list(right), f"{label} mapping drift")
        for key in left:
            _require_nested_exact(left[key], right[key], f"{label}.{key}")
    elif isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        _require(type(left) is type(right) and len(left) == len(right),
                 f"{label} sequence drift")
        for index, (lvalue, rvalue) in enumerate(zip(left, right)):
            _require_nested_exact(lvalue, rvalue, f"{label}[{index}]")
    else:
        _require(type(left) is type(right) and left == right, f"{label} scalar drift")


def _verify_global_replay(
    *, result: ArmRunResult, e011_ranking_checkpoint: Path,
) -> dict[str, Any]:
    _require(result.arm == ARM_GLOBAL, "global replay verification arm drift")
    result = _validate_arm_on_disk(result)
    _require(sha256_file(e011_ranking_checkpoint) ==
             EXPECTED_E011_RANKING_CHECKPOINT_SHA256,
             "E011 ranking checkpoint identity mismatch")
    observed_path = result.arm_dir / "checkpoint_update500.pt"
    observed = torch.load(observed_path, map_location="cpu", weights_only=False)
    reference = torch.load(
        e011_ranking_checkpoint, map_location="cpu", weights_only=False)
    _require(reference.get("update") == 500
             and reference.get("arm") == "R25_pairwise_ranking_beta0p25"
             and reference.get("source_run") == "S09-E011-R001-objective-only-ranking",
             "E011 ranking checkpoint semantic drift")
    _require_nested_exact(observed["model"], reference["model"], "global_replay.model")
    _require_nested_exact(
        observed["optimizer"], reference["optimizer"], "global_replay.optimizer")
    return {
        "status": "EXACT_E011_REPLAY_CONFIRMED",
        "model_state_exact": True,
        "optimizer_state_exact": True,
        "observed_checkpoint_sha256": sha256_file(observed_path),
        "reference_checkpoint_sha256": EXPECTED_E011_RANKING_CHECKPOINT_SHA256,
    }


def _e011_reference_summary(decision: Mapping[str, Any]) -> dict[str, Any]:
    realized = decision.get("realized_pair_changes", {})
    summary = {
        "status": decision.get("status"),
        "continuation_repairs": realized.get("control_repairs_of_initially_wrong"),
        "continuation_losses": realized.get("control_losses_of_initially_correct"),
        "ranking_repairs": realized.get("ranking_repairs_of_initially_wrong"),
        "ranking_losses": realized.get("ranking_losses_of_initially_correct"),
    }
    _require(summary["status"] == "NO_REALISED_RANKING_REPAIR"
             and all(isinstance(summary[name], list) for name in summary if name != "status")
             and len(summary["continuation_repairs"]) == 8
             and len(summary["continuation_losses"]) == 5
             and len(summary["ranking_repairs"]) == 0
             and len(summary["ranking_losses"]) == 0,
             "E011 reference result drift")
    return summary


def _collect_fields(
    runtime: Any, *, deadline: float, arm: str,
) -> dict[str, np.ndarray]:
    predicted = []
    runtime.model.eval()
    with torch.no_grad():
        for index in range(len(runtime.arrays["cycles"])):
            cycle = int(runtime.arrays["cycles"][index])
            stage = f"endpoint_field_replay:{arm}:cycle_{cycle}"
            _check_deadline(deadline, f"{stage}:before")
            _, context = atomic_losses(runtime, index)
            predicted.append(context["output"]["d_peak"].detach().cpu().numpy())
            _check_deadline(deadline, f"{stage}:after")
    return {
        "predicted_peak": np.stack(predicted),
        "d_pre": np.asarray(runtime.arrays["d_pre"]),
        "target_peak": np.asarray(runtime.arrays["d_peak"]),
        "cycles": np.asarray(runtime.arrays["cycles"]),
        "xy": np.asarray(runtime.arrays["xy"]),
        "nodal_weight": np.asarray(runtime.arrays["nodal_weight"]),
    }


def _reconstruct_saved_endpoint(
    *, result: ArmRunResult, runtime: Any, deadline: float,
) -> dict[str, np.ndarray]:
    """Load the validated update-500 checkpoint before any endpoint decision."""
    arm = result.arm
    _check_deadline(deadline, f"checkpoint_endpoint_replay:{arm}:before")
    checkpoint = torch.load(
        result.arm_dir / "checkpoint_update500.pt",
        map_location="cpu",
        weights_only=False,
    )
    _require(set(checkpoint) == {"model", "optimizer", "update", "arm", "source_run"}
             and checkpoint["update"] == UPDATES_PER_ARM
             and checkpoint["arm"] == arm
             and checkpoint["source_run"] == RUN_ID,
             f"checkpoint endpoint-replay structure drift: {arm}")
    runtime.model.load_state_dict(checkpoint["model"], strict=True)
    _check_deadline(deadline, f"checkpoint_endpoint_replay:{arm}:loaded")
    fields = _collect_fields(runtime, deadline=deadline, arm=arm)
    _check_deadline(deadline, f"checkpoint_endpoint_replay:{arm}:after")
    return fields


def _validate_endpoint_amplitudes(
    *, fields: Mapping[str, np.ndarray], result: ArmRunResult,
) -> None:
    weights = np.asarray(fields["nodal_weight"]).reshape(-1)
    _require(np.all(np.isfinite(weights)) and np.all(weights >= 0) and weights.sum() > 0,
             f"field reconstruction weight drift: {result.arm}")
    reconstructed = []
    for predicted, pre in zip(fields["predicted_peak"], fields["d_pre"]):
        increment = np.abs(np.asarray(predicted).reshape(-1) - np.asarray(pre).reshape(-1))
        _require(len(increment) == len(weights),
                 f"field reconstruction node-count drift: {result.arm}")
        reconstructed.append(float(np.dot(increment, weights) / weights.sum()))
    recorded = [
        row["predicted_damage_increment_abs_mean"]
        for row in result.evaluations[500]["per_cycle"]
    ]
    _require(np.allclose(reconstructed, recorded, rtol=1e-9, atol=1e-12),
             f"checkpoint/evaluation amplitude drift: {result.arm}")


def _write_required_figures(
    *, output: Path, results: Mapping[str, ArmRunResult],
    fields: Mapping[str, Mapping[str, np.ndarray]], deadline: float,
) -> tuple[str, ...]:
    _check_deadline(deadline, "figures_before")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    common = fields[ARM_GLOBAL]
    _require(np.array_equal(common["cycles"], fields[ARM_LOCAL]["cycles"]) and
             np.array_equal(common["d_pre"], fields[ARM_LOCAL]["d_pre"]) and
             np.array_equal(common["target_peak"], fields[ARM_LOCAL]["target_peak"]) and
             np.array_equal(common["nodal_weight"], fields[ARM_LOCAL]["nodal_weight"]) and
             np.array_equal(common["xy"], fields[ARM_LOCAL]["xy"]),
             "field reconstruction support drift")
    arrays_path = output / "field_arrays_update500.npz"
    with arrays_path.open("xb") as stream:
        np.savez_compressed(
            stream, cycles=common["cycles"], xy=common["xy"],
            nodal_weight=common["nodal_weight"], d_pre=common["d_pre"],
            target_peak=common["target_peak"],
            control_peak=fields[ARM_GLOBAL]["predicted_peak"],
            ranking_peak=fields[ARM_LOCAL]["predicted_peak"],
        )

    cycles = [int(value) for value in common["cycles"]]
    fig, ax = plt.subplots(figsize=(10.5, 5.4), constrained_layout=True)
    truth = results[ARM_GLOBAL].evaluations[500]["per_cycle"]
    ax.plot(cycles, [row["true_damage_increment_abs_mean"] for row in truth],
            "o-", label="FEM reference", color="#111111")
    for arm, color, label in (
        (ARM_GLOBAL, "#377eb8", "global-amplitude ranking replay"),
        (ARM_LOCAL, "#e41a1c", "local-support contrast ranking"),
    ):
        rows = results[arm].evaluations[500]["per_cycle"]
        ax.plot(cycles, [row["predicted_damage_increment_abs_mean"] for row in rows],
                "o-", label=label, color=color)
    ax.set(xlabel="cycle", ylabel="weighted mean |Δd|",
           title="S09-E013 update-500 damage-increment amplitudes")
    ax.grid(alpha=.25); ax.legend()
    fig.savefig(output / "amplitude_trajectory.png", dpi=180, facecolor="white")
    plt.close(fig)

    reference = common["target_peak"] - common["d_pre"]
    control = fields[ARM_GLOBAL]["predicted_peak"] - common["d_pre"]
    ranking = fields[ARM_LOCAL]["predicted_peak"] - common["d_pre"]
    vmin = float(min(reference.min(), control.min(), ranking.min()))
    vmax = float(max(reference.max(), control.max(), ranking.max()))
    _require(math.isfinite(vmin) and math.isfinite(vmax) and vmax > vmin,
             "invalid shared field colour range")
    xy = common["xy"]
    fig, axes = plt.subplots(
        len(cycles), 3, figsize=(12, 2.15 * len(cycles)), constrained_layout=True)
    image = None
    for row, cycle in enumerate(cycles):
        _check_deadline(deadline, f"field_figure:cycle_{cycle}:before")
        for column, (array, title) in enumerate((
            (reference, "FEM reference Δd"),
            (control, "global-amplitude ranking replay Δd"),
            (ranking, "local-support contrast ranking Δd"),
        )):
            axis = axes[row, column]
            image = axis.tripcolor(
                xy[:, 0], xy[:, 1], array[row], shading="gouraud",
                cmap="viridis", vmin=vmin, vmax=vmax)
            axis.set_title(f"cycle {cycle}: {title}", fontsize=8)
            axis.set_aspect("equal"); axis.set_xticks([]); axis.set_yticks([])
        _check_deadline(deadline, f"field_figure:cycle_{cycle}:after")
    fig.colorbar(image, ax=axes.ravel().tolist(), shrink=.35,
                 label=f"Δd, shared physical scale [{vmin:.3e}, {vmax:.3e}]")
    fig.savefig(output / "delta_d_fields_all_cycles.png", dpi=150, facecolor="white")
    plt.close(fig)
    _check_deadline(deadline, "figures_after")
    return (
        "field_arrays_update500.npz", "amplitude_trajectory.png",
        "delta_d_fields_all_cycles.png",
    )


def _write_evidence(
    *, output: Path, results: Mapping[str, ArmRunResult],
    runtimes: Mapping[str, Any], zero_audit: Mapping[str, Any],
    environment: Mapping[str, Any], source: Mapping[str, Any], elapsed: float,
    deadline: float, e011_reference: Mapping[str, Any],
    replay_verification: Mapping[str, Any],
) -> dict[str, Any]:
    _check_deadline(deadline, "shared_evidence_before_validation")
    validated = {arm: _validate_arm_on_disk(results[arm]) for arm in ARM_ORDER}
    fields = {
        arm: _reconstruct_saved_endpoint(
            result=validated[arm], runtime=runtimes[arm], deadline=deadline)
        for arm in ARM_ORDER
    }
    for arm in ARM_ORDER:
        _validate_endpoint_amplitudes(fields=fields[arm], result=validated[arm])
    local_metrics = {
        arm: _local_support_metrics(fields[arm], deadline=deadline, arm=arm)
        for arm in ARM_ORDER
    }
    final = {}
    for arm in ARM_ORDER:
        final[arm] = dict(validated[arm].evaluations[500]["aggregate"])
        final[arm]["local_support_auc"] = local_metrics[arm]["auc"]
    classification = classify_e013(
        global_ranking=final[ARM_GLOBAL], local_ranking=final[ARM_LOCAL], validity=True
    )
    initial_rows = validated[ARM_GLOBAL].evaluations[0]["per_cycle"]
    control_rows = validated[ARM_GLOBAL].evaluations[500]["per_cycle"]
    ranking_rows = validated[ARM_LOCAL].evaluations[500]["per_cycle"]
    initial_outcomes = _pair_outcomes(initial_rows)
    control_outcomes = _pair_outcomes(control_rows)
    ranking_outcomes = _pair_outcomes(ranking_rows)
    initially_wrong = [pair for pair, outcome in initial_outcomes.items() if outcome == "LOSS"]
    initially_correct = [pair for pair, outcome in initial_outcomes.items() if outcome == "WIN"]
    realized = {
        "initially_wrong_pairs": [list(pair) for pair in initially_wrong],
        "ranking_repairs_of_initially_wrong": [
            list(pair) for pair in initially_wrong if ranking_outcomes[pair] == "WIN"
        ],
        "control_repairs_of_initially_wrong": [
            list(pair) for pair in initially_wrong if control_outcomes[pair] == "WIN"
        ],
        "ranking_losses_of_initially_correct": [
            list(pair) for pair in initially_correct if ranking_outcomes[pair] != "WIN"
        ],
        "control_losses_of_initially_correct": [
            list(pair) for pair in initially_correct if control_outcomes[pair] != "WIN"
        ],
        "initially_wrong_local_pairs": [
            [row["growth_cycle"], row["stagnant_cycle"]]
            for row in zero_audit["records"] if row["initial_local_outcome"] == "LOSS"
        ],
        "local_arm_repairs_of_initially_wrong_local": [
            list(pair) for pair, outcome in local_metrics[ARM_LOCAL]["outcomes"].items()
            if next(row for row in zero_audit["records"] if
                    (row["growth_cycle"], row["stagnant_cycle"]) == pair)["initial_local_outcome"] == "LOSS"
            and outcome == "WIN"
        ],
        "global_arm_repairs_of_initially_wrong_local": [
            list(pair) for pair, outcome in local_metrics[ARM_GLOBAL]["outcomes"].items()
            if next(row for row in zero_audit["records"] if
                    (row["growth_cycle"], row["stagnant_cycle"]) == pair)["initial_local_outcome"] == "LOSS"
            and outcome == "WIN"
        ],
        "local_arm_losses_of_initially_correct_local": [
            list(pair) for pair, outcome in local_metrics[ARM_LOCAL]["outcomes"].items()
            if next(row for row in zero_audit["records"] if
                    (row["growth_cycle"], row["stagnant_cycle"]) == pair)["initial_local_outcome"] == "WIN"
            and outcome != "WIN"
        ],
        "global_arm_losses_of_initially_correct_local": [
            list(pair) for pair, outcome in local_metrics[ARM_GLOBAL]["outcomes"].items()
            if next(row for row in zero_audit["records"] if
                    (row["growth_cycle"], row["stagnant_cycle"]) == pair)["initial_local_outcome"] == "WIN"
            and outcome != "WIN"
        ],
    }
    decision = {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "status": classification["status"],
        "classification": classification,
        "zero_step_audit_status": zero_audit["status"],
        "realized_pair_changes": realized,
        "final_metrics": final,
        "local_support_per_cycle": {
            arm: local_metrics[arm]["rows"] for arm in ARM_ORDER
        },
        "global_replay_verification": dict(replay_verification),
        "prior_E011_reference": dict(e011_reference),
        "claim_boundary": (
            "objective-only repair on the same exposed 16-cycle synthetic development "
            "trajectory; no holdout, rollout, transfer, FEM-truth or real-road claim"
        ),
    }
    _write_json(output / "decision_metrics.json", decision)
    csv_fields = [
        "arm", "update", "cycle", "group", "predicted_damage_increment_abs_mean",
        "true_damage_increment_abs_mean", "damage_increment_mae", "false_growth",
        "predicted_target_spatial_correlation", "L_judge",
    ]
    with (output / "per_cycle_metrics.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields)
        writer.writeheader()
        for arm in ARM_ORDER:
            for update in EVALUATION_UPDATES:
                for row in validated[arm].evaluations[update]["per_cycle"]:
                    writer.writerow({"arm": arm, **{
                        key: row[key] for key in csv_fields[1:]
                    }})
    with (output / "decision_table.csv").open("x", newline="") as stream:
        fields2 = ["arm", "global_pair_score", "global_AUC", "local_pair_score",
                   "local_AUC", "G", "F", "L_P", "L_judge", "spatial"]
        writer = csv.DictWriter(stream, fieldnames=fields2)
        writer.writeheader()
        for arm in ARM_ORDER:
            metrics = final[arm]
            auc = metrics["amplitude_auc"]
            writer.writerow({
                "arm": arm, "global_pair_score": 2 * auc["wins"] + auc["ties"],
                "global_AUC": auc["value"],
                "local_pair_score": 2 * metrics["local_support_auc"]["wins"] + metrics["local_support_auc"]["ties"],
                "local_AUC": metrics["local_support_auc"]["value"],
                "G": metrics["G"], "F": metrics["F"],
                "L_P": metrics["L_P"], "L_judge": metrics["L_judge"],
                "spatial": metrics["spatial"]["primary_median"],
            })
    figure_artifacts = _write_required_figures(
        output=output, results=validated, fields=fields, deadline=deadline)
    _check_deadline(deadline, "shared_evidence_before_completion")
    completion = {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "execution_status": "SUCCEEDED",
        "retrieval_status": "PENDING",
        "scientific_status": classification["status"],
        "total_optimizer_steps_completed": 2 * UPDATES_PER_ARM,
        "total_update_cap": 2 * UPDATES_PER_ARM,
        "elapsed_seconds": elapsed,
        "environment": dict(environment),
        "source": dict(source),
        "zero_step_audit_passed": zero_audit["passed"],
        "arms": {arm: validated[arm].receipt for arm in ARM_ORDER},
        "shared_artifacts": {},
    }
    for name in ("zero_step_audit.json", "zero_step_progress.jsonl",
                 "decision_metrics.json", "decision_table.csv",
                 "per_cycle_metrics.csv", "environment.json", "source_identity.json",
                 "global_replay_verification.json",
                 *figure_artifacts):
        completion["shared_artifacts"][name] = sha256_file(output / name)
    _check_deadline(deadline, "shared_evidence_after_hashes")
    return completion


def run_producer(
    *, packet_dir: Path, base_config: Path, initial_checkpoint: Path,
    e011_decision: Path, e011_ranking_checkpoint: Path,
    output_dir: Path, archive_dir: Path, repo_root: Path,
    expected_commit: str, run_config: Path, protocol: Path,
) -> dict[str, Any]:
    start = time.time()
    deadline = start + WALL_TIME_CAP_SECONDS
    _require(os.name == "posix" and platform.system() == "Linux",
             "S09-E013 producer is Linux-only", PermissionError)
    _require(torch.cuda.is_available(), "CUDA unavailable", RuntimeError)
    config, environment, output_dir, archive_dir = _validate_run_binding(
        run_config=run_config, protocol=protocol, output_dir=output_dir,
        archive_dir=archive_dir, repo_root=repo_root,
        expected_commit=expected_commit,
    )
    _require(not output_dir.exists() and not archive_dir.exists(), "fresh roots required")
    _require(shutil.disk_usage(output_dir.parent).free >= 5 * 1024**3,
             "less than 5 GiB free")
    output_dir.mkdir(parents=True)
    archive_dir.mkdir(parents=True)
    _write_json(output_dir / "environment.json", environment)
    source = {
        "training_commit": expected_commit,
        "run_config_sha256": EXPECTED_RUN_CONFIG_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "base_config_sha256": EXPECTED_BASE_CONFIG_SHA256,
        "source_B25_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256,
        "source_E011_decision_sha256": EXPECTED_E011_DECISION_SHA256,
        "source_E011_ranking_checkpoint_sha256": EXPECTED_E011_RANKING_CHECKPOINT_SHA256,
        "run_id": RUN_ID,
    }
    _write_json(output_dir / "source_identity.json", source)
    _write_json(output_dir / "attempt_started.json", {
        "run_id": RUN_ID, "execution_status": "ADMISSION_STARTED",
        "total_update_cap": 2 * UPDATES_PER_ARM,
        "wall_time_cap_seconds": WALL_TIME_CAP_SECONDS,
        "run_config": config,
    })
    results: dict[str, ArmRunResult] = {}
    audit: dict[str, Any] | None = None
    replay_verification: dict[str, Any] | None = None
    try:
        _check_deadline(deadline, "input_identity_before")
        _require(sha256_file(base_config) == EXPECTED_BASE_CONFIG_SHA256,
                 "base config identity mismatch")
        packet_identity = _load_strict_json(packet_dir / "packet_identity.json")
        _require(packet_identity["manifest_sha256"] == EXPECTED_PACKET_MANIFEST_SHA256,
                 "packet identity mismatch")
        _require(sha256_file(initial_checkpoint) == EXPECTED_B25_CHECKPOINT_SHA256,
                 "B25 checkpoint identity mismatch")
        _require(sha256_file(e011_decision) == EXPECTED_E011_DECISION_SHA256,
                 "E011 reference identity mismatch")
        e011_reference = _e011_reference_summary(_load_strict_json(e011_decision))
        _require(sha256_file(e011_ranking_checkpoint) ==
                 EXPECTED_E011_RANKING_CHECKPOINT_SHA256,
                 "E011 ranking checkpoint identity mismatch")
        _check_deadline(deadline, "runtime_build_before")
        device = torch.device("cuda:0")
        runtime = build_runtime(
            packet_dir=packet_dir, config_path=base_config,
            device=device, executable=False)
        checkpoint = torch.load(
            initial_checkpoint, map_location=device, weights_only=False)
        _require(checkpoint["update"] == 500 and checkpoint["arm"] ==
                 "B25_support_amplitude_beta0p25",
                 "checkpoint semantic identity drift")
        runtime.model.load_state_dict(checkpoint["model"], strict=True)
        models, optimizers, initial_identity = _initialise_arms(runtime, checkpoint)
        initial_identity = {
            **initial_identity,
            "source_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256,
            "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        }
        runtimes = {arm: replace(runtime, model=models[arm]) for arm in ARM_ORDER}
        _check_deadline(deadline, "zero_step_before")
        with (output_dir / "zero_step_progress.jsonl").open("xb") as progress_stream:
            audit = zero_step_audit(
                runtimes[ARM_LOCAL], optimizers[ARM_LOCAL], deadline=deadline,
                progress_stream=progress_stream,
            )
        _write_json(output_dir / "zero_step_audit.json", audit)
        _check_deadline(deadline, "zero_step_after")
        _require(audit["passed"], "ZERO_STEP_DIRECTION_STOP")
        for arm in ARM_ORDER:
            try:
                result = _train_arm(
                    arm=arm, runtime=runtimes[arm], optimizer=optimizers[arm],
                    output=output_dir / arm, initial_identity=initial_identity,
                    deadline=deadline)
            except ArmReceiptCloseError as error:
                results[arm] = error.result
                raise
            results[arm] = result
            _require(result.receipt["terminal_state"] == "COMPLETED",
                     f"ARM_EXECUTION_FAILED:{arm}")
            if arm == ARM_GLOBAL:
                replay_verification = _verify_global_replay(
                    result=result,
                    e011_ranking_checkpoint=e011_ranking_checkpoint,
                )
                _write_json(
                    output_dir / "global_replay_verification.json",
                    replay_verification,
                )
        _require(replay_verification is not None,
                 "global replay verification missing")
        completion = _write_evidence(
            output=output_dir, results=results, runtimes=runtimes,
            zero_audit=audit, environment=environment, source=source,
            elapsed=time.time() - start, deadline=deadline,
            e011_reference=e011_reference,
            replay_verification=replay_verification,
        )
        completion["elapsed_seconds"] = time.time() - start
        _check_deadline(deadline, "archive_success_before")
        _write_json(archive_dir / "completion_receipt.json", completion)
        _check_deadline(deadline, "archive_success_after")
        _write_json(output_dir / "completion_receipt.json", completion)
        _check_deadline(deadline, "output_success_after")
        return completion
    except BaseException as error:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "run_id": RUN_ID,
            "execution_status": "FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
            "elapsed_seconds": time.time() - start,
            "zero_step_audit_passed": None if audit is None else audit["passed"],
            "total_optimizer_steps_completed": sum(
                result.receipt["optimizer_steps_completed"]
                for result in results.values()),
            "completed_arms": {
                arm: result.receipt for arm, result in results.items()
            },
            "source": source,
            "environment": environment,
            "authoritative_precedence": (
                "failure_receipt.json supersedes any completion_receipt.json "
                "left by an interrupted close"
            ),
        }
        for root in (output_dir, archive_dir):
            path = root / "failure_receipt.json"
            if not path.exists():
                try:
                    _write_json(path, failure)
                except BaseException:
                    pass
        raise
