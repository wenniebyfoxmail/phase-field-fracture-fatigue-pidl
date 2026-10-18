"""Bounded two-arm producer for the S09-E011 ranking-objective experiment."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
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
    atomic_losses,
    flattened_objective_gradients,
    flattened_parameters,
    grouped_losses,
    parameter_state_sha256,
)
from s09_e010_producer import evaluate_arm
from s09_e010_support_amplitude import support_amplitude_losses
from s09_e011_ranking_objective import (
    ARM_CONTROL,
    ARM_ORDER,
    ARM_RANK,
    GROWTH_CYCLES,
    NEAR_STAGNANT_CYCLES,
    OBJECTIVE_ORDER,
    PAIR_ORDER,
    UPDATES_PER_ARM,
    classify_e011,
    merge_ranking_gradients,
    pair_mean_objectives,
    pair_schedule,
    ranking_direction,
    ranking_loss,
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


SCHEMA_VERSION = "s09-e011-pairwise-ranking-producer-v1"
RUN_ID = "S09-E011-R001-objective-only-ranking"
EXPECTED_BASE_CONFIG_SHA256 = "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
EXPECTED_PACKET_MANIFEST_SHA256 = "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
EXPECTED_B25_CHECKPOINT_SHA256 = "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05"
EXPECTED_E010_DECISION_SHA256 = "b01cf367381a0fda46a4b1015bf3ea881d2c0c32d27021176c39009eb8cd3b54"
EVALUATION_UPDATES = (0, 16, 64, 128, 256, 496, 500)
PRODUCER_FILES = (
    "source/s09_e011_ranking_objective.py",
    "source/s09_e011_producer.py",
    "scripts/run_s09_e011_producer.py",
    "docs/research/S09/S09-E011/experiment.md",
    "docs/research/S09/S09-E011/run_config.json",
)


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


def _optimizer_state_sha256(optimizer: torch.optim.AdamW) -> str:
    buffer = io.BytesIO()
    torch.save(optimizer.state_dict(), buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _pair_objectives(runtime: Any, growth_index: int, stagnant_index: int):
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
        per_cycle.append((losses, context, objectives, amplitude, addition_record))
    rank, rank_record = ranking_loss(per_cycle[0][3], per_cycle[1][3])
    objectives = pair_mean_objectives(per_cycle[0][2], per_cycle[1][2], rank)
    margin = per_cycle[0][3] - per_cycle[1][3]
    return objectives, margin, rank_record, per_cycle


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


def zero_step_audit(runtime: Any, optimizer: torch.optim.AdamW) -> dict[str, Any]:
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    cycle_to_index = {cycle: index for index, cycle in enumerate(cycles)}
    before_hash = parameter_state_sha256(runtime.model)
    optimizer_hash = _optimizer_state_sha256(optimizer)
    records = []
    for growth_cycle, stagnant_cycle in PAIR_ORDER:
        objectives, margin, rank_record, _ = _pair_objectives(
            runtime, cycle_to_index[growth_cycle], cycle_to_index[stagnant_cycle]
        )
        augmented = OrderedDict(objectives)
        augmented["pair_margin"] = margin
        gradients, layout = flattened_objective_gradients(runtime.model, augmented)
        objective_gradients = OrderedDict(
            (name, gradients[name]) for name in OBJECTIVE_ORDER
        )
        margin_gradient = gradients["pair_margin"]
        arm_records = {}
        for arm in ARM_ORDER:
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
            arm_records[arm] = {
                "merged_descent_margin_derivative": float(
                    (-margin_gradient.dot(direction)).detach().cpu()
                ),
                "predicted_adamw_margin_change": float(
                    margin_gradient.dot(displacement).detach().cpu()
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
                "clip_applied": diagnostic["clip_applied"],
            }
        records.append({
            "growth_cycle": growth_cycle,
            "stagnant_cycle": stagnant_cycle,
            "initial_outcome": "WIN" if rank_record["physical_margin"] > 0 else (
                "LOSS" if rank_record["physical_margin"] < 0 else "TIE"
            ),
            "initial_margin": rank_record["physical_margin"],
            "ranking_loss": float(objectives["L_R"].detach().cpu()),
            "arms": arm_records,
        })
    wrong = [row for row in records if row["initial_outcome"] == "LOSS"]
    correct = [row for row in records if row["initial_outcome"] == "WIN"]
    wrong_positive = sum(
        row["arms"][ARM_RANK]["predicted_adamw_margin_change"] > 0 for row in wrong
    )
    correct_negative = sum(
        row["arms"][ARM_RANK]["predicted_adamw_margin_change"] < 0 for row in correct
    )
    correct_flips = sum(
        row["initial_margin"]
        + row["arms"][ARM_RANK]["predicted_adamw_margin_change"] <= 0
        for row in correct
    )
    wrong_rank = [
        row["arms"][ARM_RANK]["predicted_adamw_margin_change"] for row in wrong
    ]
    wrong_control = [
        row["arms"][ARM_CONTROL]["predicted_adamw_margin_change"] for row in wrong
    ]
    gate = (
        len(wrong) == 8
        and wrong_positive == 8
        and correct_flips <= 3
        and float(np.median(wrong_rank)) > float(np.median(wrong_control))
    )
    _require(parameter_state_sha256(runtime.model) == before_hash,
             "zero-step audit changed model")
    _require(_optimizer_state_sha256(optimizer) == optimizer_hash,
             "zero-step audit changed optimizer")
    return {
        "status": "ZERO_STEP_DIRECTION_READY" if gate else "ZERO_STEP_DIRECTION_STOP",
        "passed": gate,
        "optimizer_steps_performed": 0,
        "initial_model_state_sha256": before_hash,
        "initial_optimizer_state_sha256": optimizer_hash,
        "wrong_pair_count": len(wrong),
        "correct_pair_count": len(correct),
        "ranking_predicted_adamw_increases_wrong_margin_count": int(wrong_positive),
        "ranking_predicted_adamw_decreases_correct_margin_count": int(correct_negative),
        "ranking_predicted_adamw_flips_correct_margin_count": int(correct_flips),
        "median_wrong_margin_change": {
            ARM_CONTROL: float(np.median(wrong_control)),
            ARM_RANK: float(np.median(wrong_rank)),
        },
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
) -> dict[str, Any]:
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
    with (output / "train_log.jsonl").open("xb") as train_stream, \
         (output / "gradient_diagnostics.jsonl").open("xb") as gradient_stream, \
         (output / "diagnostic_metrics.jsonl").open("xb") as diagnostic_stream:
        initial = evaluate_arm(runtime, update=0)
        evaluations[0] = initial
        _append_jsonl(diagnostic_stream, initial)
        for update, (growth_cycle, stagnant_cycle) in enumerate(schedule, 1):
            _require(time.time() < deadline, "WALL_TIME_CAP_REACHED", TimeoutError)
            runtime.model.train()
            optimizer.zero_grad(set_to_none=True)
            objectives, _, rank_record, per_cycle = _pair_objectives(
                runtime, cycle_to_index[growth_cycle], cycle_to_index[stagnant_cycle]
            )
            hard_records = []
            projection_records = []
            for _, context, _, _, _ in per_cycle:
                hard = hard_constraint_report(
                    runtime, context["d_pre"], context["history_pre"], context["output"]
                )
                _require(sum(hard.values()) == 0, "per-update hard-constraint violation")
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
            optimizer.step()
            after, after_order = flattened_parameters(runtime.model)
            _require(after_order == parameter_order, "post-step parameter order drift")
            displacement = after - before
            train_row = {
                "update": update,
                "growth_cycle": growth_cycle,
                "stagnant_cycle": stagnant_cycle,
                "pair_index": (update - 1) % len(PAIR_ORDER),
                "ranking_record": rank_record,
                "objectives": {
                    name: float(value.detach().cpu()) for name, value in objectives.items()
                },
                "hard_constraint_counts": hard_records,
                "proposal_projection_counts": projection_records,
            }
            gradient_row = {
                "update": update,
                "growth_cycle": growth_cycle,
                "stagnant_cycle": stagnant_cycle,
                "direction_sha256": hashlib.sha256(
                    direction.detach().cpu().numpy().tobytes()
                ).hexdigest(),
                "direction_norm": float(torch.linalg.vector_norm(direction).cpu()),
                "parameter_displacement_norm": float(
                    torch.linalg.vector_norm(displacement).cpu()
                ),
                "rank_margin_derivative_along_displacement": float(
                    (gradients["L_R"].dot(displacement)).detach().cpu()
                ),
                "direction_diagnostics": diagnostic,
            }
            _append_jsonl(train_stream, train_row)
            _append_jsonl(gradient_stream, gradient_row)
            if update in EVALUATION_UPDATES[1:]:
                evaluation = evaluate_arm(runtime, update=update)
                evaluations[update] = evaluation
                _append_jsonl(diagnostic_stream, evaluation)
    checkpoint_path = output / "checkpoint_update500.pt"
    torch.save({
        "model": runtime.model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "update": UPDATES_PER_ARM,
        "arm": arm,
        "source_run": RUN_ID,
    }, checkpoint_path)
    artifact_names = (
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "checkpoint_update500.pt",
    )
    receipt = {
        "arm": arm,
        "terminal_state": "COMPLETED",
        "optimizer_steps_completed": UPDATES_PER_ARM,
        "evaluation_updates_present": list(evaluations),
        "finite": True,
        "hard_constraint_violations": 0,
        "artifacts": {name: sha256_file(output / name) for name in artifact_names},
    }
    _write_json(output / "termination_receipt.json", receipt)
    return {"receipt": receipt, "evaluations": evaluations}


def _pair_outcomes(rows: list[dict[str, Any]]) -> dict[tuple[int, int], str]:
    amplitudes = {row["cycle"]: row["predicted_damage_increment_abs_mean"] for row in rows}
    outcomes = {}
    for growth, stagnant in PAIR_ORDER:
        margin = amplitudes[growth] - amplitudes[stagnant]
        outcomes[(growth, stagnant)] = "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"
    return outcomes


def _write_evidence(
    *, output: Path, results: Mapping[str, Any], zero_audit: Mapping[str, Any],
    environment: Mapping[str, Any], source: Mapping[str, Any], elapsed: float,
) -> dict[str, Any]:
    final = {
        arm: results[arm]["evaluations"][500]["aggregate"] for arm in ARM_ORDER
    }
    classification = classify_e011(
        control=final[ARM_CONTROL], ranking=final[ARM_RANK], validity=True
    )
    initial_rows = results[ARM_CONTROL]["evaluations"][0]["per_cycle"]
    control_rows = results[ARM_CONTROL]["evaluations"][500]["per_cycle"]
    ranking_rows = results[ARM_RANK]["evaluations"][500]["per_cycle"]
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
    }
    decision = {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "status": classification["status"],
        "classification": classification,
        "zero_step_audit_status": zero_audit["status"],
        "realized_pair_changes": realized,
        "final_metrics": final,
        "claim_boundary": (
            "objective-only repair on the same exposed 16-cycle synthetic development "
            "trajectory; no holdout, rollout, transfer, FEM-truth or real-road claim"
        ),
    }
    _write_json(output / "decision_metrics.json", decision)
    fields = [
        "arm", "update", "cycle", "group", "predicted_damage_increment_abs_mean",
        "true_damage_increment_abs_mean", "damage_increment_mae", "false_growth",
        "predicted_target_spatial_correlation", "L_judge",
    ]
    with (output / "per_cycle_metrics.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for arm in ARM_ORDER:
            for update in EVALUATION_UPDATES:
                for row in results[arm]["evaluations"][update]["per_cycle"]:
                    writer.writerow({"arm": arm, **{key: row[key] for key in fields[1:]}})
    with (output / "decision_table.csv").open("x", newline="") as stream:
        fields2 = ["arm", "pair_score", "AUC", "G", "F", "L_P", "L_judge", "spatial"]
        writer = csv.DictWriter(stream, fieldnames=fields2)
        writer.writeheader()
        for arm in ARM_ORDER:
            metrics = final[arm]
            auc = metrics["amplitude_auc"]
            writer.writerow({
                "arm": arm, "pair_score": 2 * auc["wins"] + auc["ties"],
                "AUC": auc["value"], "G": metrics["G"], "F": metrics["F"],
                "L_P": metrics["L_P"], "L_judge": metrics["L_judge"],
                "spatial": metrics["spatial"]["primary_median"],
            })
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
        "arms": {arm: results[arm]["receipt"] for arm in ARM_ORDER},
        "shared_artifacts": {},
    }
    for name in ("zero_step_audit.json", "decision_metrics.json", "decision_table.csv",
                 "per_cycle_metrics.csv", "environment.json", "source_identity.json"):
        completion["shared_artifacts"][name] = sha256_file(output / name)
    _write_json(output / "completion_receipt.json", completion)
    return completion


def run_producer(
    *, packet_dir: Path, base_config: Path, initial_checkpoint: Path,
    e010_decision: Path, output_dir: Path, archive_dir: Path, repo_root: Path,
    expected_commit: str,
) -> dict[str, Any]:
    start = time.time()
    deadline = start + 3600.0
    _require(os.name == "posix" and platform.system() == "Linux",
             "S09-E011 producer is Linux-only", PermissionError)
    _require(torch.cuda.is_available(), "CUDA unavailable", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible, "exactly one visible GPU required")
    _require(current_commit(repo_root) == expected_commit, "commit identity mismatch")
    _require(_execution_files_clean(repo_root), "producer files are dirty")
    _require(sha256_file(base_config) == EXPECTED_BASE_CONFIG_SHA256,
             "base config identity mismatch")
    packet_identity = json.loads((packet_dir / "packet_identity.json").read_text())
    _require(packet_identity["manifest_sha256"] == EXPECTED_PACKET_MANIFEST_SHA256,
             "packet identity mismatch")
    _require(sha256_file(initial_checkpoint) == EXPECTED_B25_CHECKPOINT_SHA256,
             "B25 checkpoint identity mismatch")
    _require(sha256_file(e010_decision) == EXPECTED_E010_DECISION_SHA256,
             "E010 reference identity mismatch")
    _require(not output_dir.exists() and not archive_dir.exists(), "fresh roots required")
    _require(str(output_dir).startswith("/mnt/data2/drtao/wennie/"), "invalid output root")
    _require(str(archive_dir).startswith("/mnt/data2/drtao/pidl_archives/"),
             "invalid archive root")
    _require(shutil.disk_usage(output_dir.parent).free >= 5 * 1024**3,
             "less than 5 GiB free")
    environment = _environment(visible)
    device = torch.device("cuda:0")
    runtime = build_runtime(
        packet_dir=packet_dir, config_path=base_config, device=device, executable=False
    )
    checkpoint = torch.load(initial_checkpoint, map_location=device, weights_only=False)
    _require(checkpoint["update"] == 500 and checkpoint["arm"] ==
             "B25_support_amplitude_beta0p25", "checkpoint semantic identity drift")
    runtime.model.load_state_dict(checkpoint["model"], strict=True)
    models, optimizers, initial_identity = _initialise_arms(runtime, checkpoint)
    initial_identity = {
        **initial_identity,
        "source_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256,
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
    }
    audit_runtime = replace(runtime, model=models[ARM_RANK])
    audit = zero_step_audit(audit_runtime, optimizers[ARM_RANK])
    _require(audit["passed"], "ZERO_STEP_DIRECTION_STOP")
    output_dir.mkdir(parents=True)
    archive_dir.mkdir(parents=True)
    _write_json(output_dir / "zero_step_audit.json", audit)
    _write_json(output_dir / "environment.json", environment)
    source = {
        "training_commit": expected_commit,
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "base_config_sha256": EXPECTED_BASE_CONFIG_SHA256,
        "source_B25_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256,
        "source_E010_decision_sha256": EXPECTED_E010_DECISION_SHA256,
        "run_id": RUN_ID,
    }
    _write_json(output_dir / "source_identity.json", source)
    results = {}
    try:
        for arm in ARM_ORDER:
            arm_runtime = replace(runtime, model=models[arm])
            results[arm] = _train_arm(
                arm=arm, runtime=arm_runtime, optimizer=optimizers[arm],
                output=output_dir / arm, initial_identity=initial_identity,
                deadline=deadline,
            )
        completion = _write_evidence(
            output=output_dir, results=results, zero_audit=audit,
            environment=environment, source=source, elapsed=time.time() - start,
        )
        _write_json(archive_dir / "completion_receipt.json", completion)
        return completion
    except BaseException as error:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "run_id": RUN_ID,
            "execution_status": "FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
            "elapsed_seconds": time.time() - start,
            "zero_step_audit_passed": audit["passed"],
            "completed_arms": {
                arm: result["receipt"] for arm, result in results.items()
            },
            "source": source,
            "environment": environment,
        }
        if not (output_dir / "completion_receipt.json").exists():
            _write_json(output_dir / "completion_receipt.json", failure)
        if not (archive_dir / "completion_receipt.json").exists():
            _write_json(archive_dir / "completion_receipt.json", failure)
        raise
