"""Producer package for the reviewed S09-E009 four-arm screen.

The module contains the future optimiser loop, producer-only configuration
resolver, frozen evaluator and evidence writer.  Importing it performs no I/O.
Local tests use pure fixtures or mock adapters and never call AdamW.step.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import copy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Protocol

import numpy as np
import torch

from s09_code_identity import current_commit, tracked_execution_files_clean
from s09_e009_four_arm import (
    ARM_ANCHOR_25,
    ARM_ORDER,
    ARM_REPLAY,
    AnchorStationary,
    LOSS_ORDER,
    amplitude_auc,
    classify_a25,
    fixed_support_median,
    flattened_parameters,
    group_amplitude_ratio,
    grouped_losses,
    parameter_displacement_alignment,
    parameter_state_sha256,
)
from s09_e009_runner_integration import (
    EVALUATION_UPDATES,
    EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
    EXPECTED_CYCLES,
    EXPECTED_PROTOCOL_SHA256,
    PLANNED_RUN_ID,
    TERMINAL_COMPLETED,
    TERMINAL_EXECUTION_FAILED,
    TERMINAL_METHOD_INAPPLICABLE,
    TOTAL_UPDATE_CAP,
    UPDATES_PER_ARM,
    _direction_sha256,
    _direction_with_damage_reference,
    _load_json,
    _require,
    build_schedule,
    cross_arm_performance_eligible,
    validate_integration_config,
    validate_termination_receipt,
)
from s09_multiobjective_update import merge_objective_gradients
from s09_stage0a_p1_packet import canonical_json, load_verified_packet, sha256_file
from s09_stage0a_p1_trainer import (
    OBJECTIVE_ORDER,
    Runtime,
    assign_merged_gradient,
    build_runtime,
    gpu_identity,
    gradient_record,
    hard_constraint_report,
    proposal_projection_diagnostics,
    validated_producer_paths,
    validated_staging_path,
)
from s09_stage0a_transition import fixed_judgement_loss


SCHEMA_VERSION = "s09-e009-four-arm-producer-v1"
EXPECTED_INTEGRATION_COMMIT = "efeffbfae4395f95228c56e3f530e323f1ab8f6a"
EXPECTED_INTEGRATION_CONFIG_SHA256 = (
    "7994c8959ae5fc3adaa2b4037ba7be2619ddb28fccb00a9663a8a42009a283fd"
)
EXPECTED_PROTOCOL_CONTRACT_SHA256 = (
    "92e9dfdcd70bf886a0b9f9dd416c9dc123ef75cd999056c4bed44b5bc05fa26f"
)
REPLAY_GRADIENT_PREFIX_SHA256 = (
    "50c746b8f6548f53493c6556b7f7281a4b97d2340c35aad5e9d63c87f9bddfe9"
)
REPLAY_REFERENCE = {
    0: {
        "L_judge": 0.8541368615961056,
        "G": 0.0005017354462152066,
        "persistence": 0.0005017354462152066,
        "F": 0.0,
        "hard_constraint_violations": 0,
    },
    500: {
        "L_judge": 0.6951799249831218,
        "G": 0.0007363939239267219,
        "persistence": 0.0005017354462152066,
        "F": 0.00024147322519653153,
        "hard_constraint_violations": 0,
    },
}
HARD_CONSTRAINT_KEYS = (
    "prestate_f_consistency",
    "damage_irreversibility",
    "damage_upper_bound",
    "alpha_irreversibility",
    "derived_f_identity",
    "f_monotonicity",
    "peak_boundary_lifting",
)
GROWTH_CYCLES = (1, 58, 60, 69, 70)
NEAR_STAGNANT_CYCLES = (3, 4, 71, 72, 73)
RESOLUTION_SOURCE_FIELDS = ("producer_package_reviewed_commit", "training_commit")
PRODUCER_EXECUTION_FILES = (
    "source/s09_e009_four_arm.py",
    "source/s09_e009_runner_integration.py",
    "source/s09_e009_producer.py",
    "scripts/resolve_s09_e009_producer_config.py",
    "scripts/run_s09_e009_producer.py",
)


def _strict_json_bytes(value: Any) -> bytes:
    return canonical_json(value)


def _write_new_bytes(path: Path, payload: bytes) -> None:
    _require(not path.exists(), f"artifact already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def _write_new_json(path: Path, value: Any) -> None:
    _write_new_bytes(path, _strict_json_bytes(value))


def _protocol_contract_sha256_bytes(raw: bytes) -> str:
    """Ignore only the unique status field in the leading YAML front matter."""
    lines = raw.splitlines(keepends=True)
    _require(lines and lines[0].rstrip(b"\r\n") == b"---",
             "protocol front matter is missing")
    try:
        closing = next(index for index, line in enumerate(lines[1:], start=1)
                       if line.rstrip(b"\r\n") == b"---")
    except StopIteration as error:
        raise ValueError("protocol front matter is unterminated") from error
    status_indexes = [index for index in range(1, closing)
                      if lines[index].startswith(b"status: ")]
    _require(len(status_indexes) == 1,
             "protocol front matter must contain exactly one mutable status")
    payload = b"".join(line for index, line in enumerate(lines)
                       if index != status_indexes[0])
    return hashlib.sha256(payload).hexdigest()


def _protocol_contract_sha256(path: Path) -> str:
    return _protocol_contract_sha256_bytes(path.read_bytes())


def _parse_strict_json_bytes(raw: bytes) -> dict[str, Any]:
    return json.loads(
        raw.decode("utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _producer_execution_files_clean(root: Path) -> bool:
    """Bind the future run to all inherited and E009 execution files."""
    if not tracked_execution_files_clean(root):
        return False
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *PRODUCER_EXECUTION_FILES],
        cwd=root,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--",
         *PRODUCER_EXECUTION_FILES],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and not untracked.stdout.strip()


def _environment_snapshot(visible: str) -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": gpu_identity(visible),
        "CUDA_VISIBLE_DEVICES": visible,
    }


def _unresolved_projection(config: Mapping[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(dict(config))
    projected["schema_version"] = "s09-e009-four-arm-no-training-integration-v1"
    projected["status"] = "RUNNER_INTEGRATION_CANDIDATE__NO_TRAINING"
    projected["execution_authorized"] = False
    source = projected["source"]
    source["integration_reviewed_commit"] = "TO_BE_SET_AFTER_EXACT_COMMIT_REVIEW"
    source["input_packet_sha256"] = "TO_BE_LOCKED_FROM_REVIEWED_PACKET"
    for field in RESOLUTION_SOURCE_FIELDS:
        source.pop(field, None)
    projected["producer"]["resolved_environment"] = (
        "TO_BE_LOCKED_BY_FUTURE_READ_ONLY_PREFLIGHT"
    )
    projected.pop("resolution_receipt", None)
    return projected


def validate_resolved_config(
    config: Mapping[str, Any],
    *,
    base_runtime_config_path: Path,
    packet_manifest_sha256: str,
    executable: bool,
) -> None:
    """Validate declared resolution fields and replay the reviewed base check."""
    _require(config.get("schema_version") == SCHEMA_VERSION, "producer schema drift")
    source = config.get("source", {})
    _require(source.get("integration_reviewed_commit") == EXPECTED_INTEGRATION_COMMIT,
             "integration review identity drift")
    for field in RESOLUTION_SOURCE_FIELDS:
        value = source.get(field)
        _require(isinstance(value, str) and len(value) == 40 and
                 all(character in "0123456789abcdef" for character in value),
                 f"invalid resolved source identity: {field}")
    _require(source["producer_package_reviewed_commit"] == source["training_commit"],
             "producer review is not bound to the training commit")
    _require(source.get("input_packet_sha256") == packet_manifest_sha256,
             "resolved packet identity mismatch")
    _require(isinstance(config.get("producer", {}).get("resolved_environment"), Mapping),
             "producer environment is unresolved")
    environment = config["producer"]["resolved_environment"]
    _require(set(environment) == {
        "hostname", "platform", "python", "torch", "cuda", "gpu",
        "CUDA_VISIBLE_DEVICES",
    }, "producer environment fields drift")
    _require(set(environment["gpu"]) == {"uuid", "pci_bus_id", "name"},
             "physical GPU identity fields drift")
    receipt = config.get("resolution_receipt")
    _require(isinstance(receipt, Mapping), "resolution receipt missing")
    _require(receipt.get("integration_config_sha256") ==
             EXPECTED_INTEGRATION_CONFIG_SHA256, "integration config identity drift")
    _require(receipt.get("protocol_contract_sha256") ==
             EXPECTED_PROTOCOL_CONTRACT_SHA256, "protocol contract identity drift")
    _require(receipt.get("base_runtime_config_sha256") ==
             EXPECTED_BASE_RUNTIME_CONFIG_SHA256, "base-runtime identity drift")
    _require(receipt.get("packet_manifest_sha256") == packet_manifest_sha256,
             "resolution receipt packet identity drift")
    _require(receipt.get("optimizer_or_training_step_performed") is False,
             "resolution receipt cannot claim an optimiser step")
    projected = _unresolved_projection(config)
    validate_integration_config(
        projected,
        base_config_path=base_runtime_config_path,
        synthetic_test_adapter=False,
    )
    if executable:
        _require(config.get("status") == "RESOLVED_FOR_FINAL_EXECUTION_GATE",
                 "resolved execution status drift")
        _require(config.get("execution_authorized") is True,
                 "execution is not authorised", PermissionError)
    else:
        _require(config.get("status") == "RESOLVED_FOR_FINAL_EXECUTION_GATE",
                 "resolved config status drift")


def resolve_producer_config(
    *,
    packet_dir: Path,
    integration_config_path: Path,
    base_runtime_config_path: Path,
    protocol_path: Path,
    output_path: Path,
    repo_root: Path,
    approved_producer_commit: str,
    approved_hostname: str,
    approved_gpu_name: str,
    approved_gpu_uuid: str,
    approved_gpu_pci_bus_id: str,
    approved_staging_root: Path,
    authorize_execution: bool,
) -> dict[str, Any]:
    """Resolve live producer identities without constructing an optimiser."""
    _require(sys.platform.startswith("linux"), "config resolution is producer-only",
             PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required for producer resolution",
             RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible,
             "exactly one CUDA_VISIBLE_DEVICES entry is required")
    output_path = validated_staging_path(output_path, approved_staging_root)
    _require(not output_path.exists(), "resolved config output already exists")
    integration_raw = integration_config_path.read_bytes()
    base_raw = base_runtime_config_path.read_bytes()
    protocol_raw = protocol_path.read_bytes()
    _require(hashlib.sha256(integration_raw).hexdigest() ==
             EXPECTED_INTEGRATION_CONFIG_SHA256,
             "integration config differs from reviewed runner candidate")
    _require(hashlib.sha256(base_raw).hexdigest() ==
             EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
             "base runtime config differs from reviewed identity")
    _require(_protocol_contract_sha256_bytes(protocol_raw) ==
             EXPECTED_PROTOCOL_CONTRACT_SHA256,
             "protocol contract differs from reviewed method")
    observed_commit = current_commit(repo_root)
    _require(observed_commit == approved_producer_commit,
             "current commit differs from approved producer package")
    _require(_producer_execution_files_clean(repo_root),
             "tracked execution files are dirty")
    observed_environment = _environment_snapshot(visible)
    _require(observed_environment["hostname"] == approved_hostname,
             "producer hostname differs from approved preflight")
    _require(observed_environment["gpu"] == {
        "uuid": approved_gpu_uuid,
        "pci_bus_id": approved_gpu_pci_bus_id,
        "name": approved_gpu_name,
    }, "physical GPU differs from approved preflight")

    arrays, metadata, packet_identity = load_verified_packet(packet_dir)
    base = _parse_strict_json_bytes(base_raw)
    _require(metadata.get("config_sha256") == EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
             "packet was not exported from the reviewed base runtime config")
    _require(metadata.get("source_p1_verdict") == "P1_CONTRACT_FROZEN" and
             metadata.get("source_hash_verdict") == "FULL_TRAJECTORY_HASH_QUALIFIED" and
             metadata.get("source_decode_verdict") == "FULL_TRAJECTORY_DECODE_QUALIFIED",
             "packet qualification verdict drift")
    _require(np.array_equal(arrays["cycles"], np.asarray(EXPECTED_CYCLES)),
             "packet cycle order drift")
    _require(arrays["d_pre"].shape[0] == len(EXPECTED_CYCLES) and
             arrays["d_pre"].shape[1] == base["data"]["native_nodes"],
             "packet nodal support drift")
    _require(arrays["history_pre"].shape[:2] ==
             (len(EXPECTED_CYCLES), base["data"]["native_q4_elements"]),
             "packet Q4 support drift")

    unresolved = _parse_strict_json_bytes(integration_raw)
    base = _parse_strict_json_bytes(base_raw)
    with tempfile.TemporaryDirectory(prefix="s09-e009-resolution-") as temp_dir:
        snapshot_root = Path(temp_dir)
        integration_snapshot = snapshot_root / "integration.json"
        base_snapshot = snapshot_root / "base.json"
        integration_snapshot.write_bytes(integration_raw)
        base_snapshot.write_bytes(base_raw)
        validate_integration_config(
            unresolved,
            base_config_path=base_snapshot,
            synthetic_test_adapter=False,
        )
    resolved = copy.deepcopy(unresolved)
    resolved["schema_version"] = SCHEMA_VERSION
    resolved["status"] = "RESOLVED_FOR_FINAL_EXECUTION_GATE"
    resolved["execution_authorized"] = bool(authorize_execution)
    resolved["source"]["integration_reviewed_commit"] = EXPECTED_INTEGRATION_COMMIT
    resolved["source"]["producer_package_reviewed_commit"] = approved_producer_commit
    resolved["source"]["training_commit"] = observed_commit
    resolved["source"]["input_packet_sha256"] = packet_identity["manifest_sha256"]
    resolved["producer"]["resolved_environment"] = observed_environment
    resolved["resolution_receipt"] = {
        "integration_config_sha256": hashlib.sha256(integration_raw).hexdigest(),
        "protocol_full_sha256_recorded_in_integration": EXPECTED_PROTOCOL_SHA256,
        "protocol_contract_sha256": _protocol_contract_sha256_bytes(protocol_raw),
        "base_runtime_config_sha256": hashlib.sha256(base_raw).hexdigest(),
        "packet_manifest_sha256": packet_identity["manifest_sha256"],
        "producer_package_reviewed_commit": approved_producer_commit,
        "training_commit": observed_commit,
        "staging_root": str(approved_staging_root.resolve(strict=True)),
        "resolved_config_path": str(output_path),
        "optimizer_or_training_step_performed": False,
    }
    validate_resolved_config(
        resolved,
        base_runtime_config_path=base_runtime_config_path,
        packet_manifest_sha256=packet_identity["manifest_sha256"],
        executable=False,
    )
    _write_new_json(output_path, resolved)
    return resolved


def _weighted_mean(value: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
    return (value * weight).sum() / weight.sum()


def _weighted_correlation(
    left: torch.Tensor, right: torch.Tensor, weight: torch.Tensor,
) -> float | None:
    left = left.reshape(-1)
    right = right.reshape(-1)
    weight = weight.reshape(-1)
    left_mean = _weighted_mean(left, weight)
    right_mean = _weighted_mean(right, weight)
    left_centered = left - left_mean
    right_centered = right - right_mean
    left_ss = _weighted_mean(left_centered.square(), weight)
    right_ss = _weighted_mean(right_centered.square(), weight)
    if left_ss <= 0 or right_ss <= 0:
        return None
    value = _weighted_mean(left_centered * right_centered, weight) / torch.sqrt(
        left_ss * right_ss)
    _require(torch.isfinite(value), "nonfinite weighted spatial correlation",
             FloatingPointError)
    return float(value.detach().cpu())


def _pearson(left: list[float], right: list[float]) -> float | None:
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if left_array.size != right_array.size or left_array.size < 2:
        raise ValueError("correlation inputs must share at least two values")
    if np.ptp(left_array) == 0 or np.ptp(right_array) == 0:
        return None
    value = float(np.corrcoef(left_array, right_array)[0, 1])
    _require(math.isfinite(value), "nonfinite Pearson correlation",
             FloatingPointError)
    return value


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for index in order[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def evaluate_arm(runtime: Runtime, *, update: int) -> dict[str, Any]:
    """Evaluate one checkpoint over the exact fixed 16-example support."""
    _require(type(update) is int and update in EVALUATION_UPDATES,
             "evaluation update is not frozen")
    from s09_e009_four_arm import atomic_losses

    runtime.model.eval()
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    _require(tuple(cycles) == EXPECTED_CYCLES, "runtime cycle order drift")
    growth_cycles = list(runtime.config["data"]["growth_cycles"])
    stagnant_cycles = list(runtime.config["data"]["near_stagnant_cycles"])
    per_cycle: list[dict[str, Any]] = []
    predicted_fields: list[torch.Tensor] = []
    hard_total = {key: 0 for key in HARD_CONSTRAINT_KEYS}
    with torch.no_grad():
        for index, cycle in enumerate(cycles):
            losses, context = atomic_losses(runtime, index)
            output = context["output"]
            target = context["target"]
            d_pre = context["d_pre"]
            report = hard_constraint_report(
                runtime, d_pre, context["history_pre"], output)
            for key in HARD_CONSTRAINT_KEYS:
                hard_total[key] += int(report[key])
            nodal = output["nodal_weight"]
            pred_delta = output["d_peak"] - d_pre
            true_delta = target["d_peak"] - d_pre
            predicted_fields.append(pred_delta.detach().clone())
            predicted_amplitude = _weighted_mean(pred_delta.abs(), nodal)
            true_amplitude = _weighted_mean(true_delta.abs(), nodal)
            damage_mae = _weighted_mean((pred_delta - true_delta).abs(), nodal)
            false_growth = _weighted_mean(torch.relu(pred_delta - true_delta), nodal)
            groups = grouped_losses(losses)
            judgement = fixed_judgement_loss(output, target, runtime.scales)
            spatial = _weighted_correlation(pred_delta, true_delta, nodal)
            per_cycle.append({
                "update": update,
                "cycle": cycle,
                "group": (
                    "growth" if cycle in growth_cycles else
                    "near_stagnant" if cycle in stagnant_cycles else "other"
                ),
                "predicted_damage_increment_abs_mean": float(predicted_amplitude.cpu()),
                "true_damage_increment_abs_mean": float(true_amplitude.cpu()),
                "damage_increment_mae": float(damage_mae.cpu()),
                "false_growth": float(false_growth.cpu()),
                "predicted_target_spatial_correlation": spatial,
                "L_judge": float(judgement.cpu()),
                "atomic_losses": {
                    name: float(losses[name].detach().cpu()) for name in LOSS_ORDER
                },
                "grouped_losses": {
                    name: float(value.detach().cpu()) for name, value in groups.items()
                },
                "projection_counts": proposal_projection_diagnostics(runtime, d_pre, output),
                "hard_constraint_counts": report,
            })

    growth = [row for row in per_cycle if row["group"] == "growth"]
    stagnant = [row for row in per_cycle if row["group"] == "near_stagnant"]
    _require(len(growth) == len(stagnant) == 5,
             "frozen growth/stagnant support drift")
    predicted_amplitudes = [row["predicted_damage_increment_abs_mean"] for row in per_cycle]
    true_amplitudes = [row["true_damage_increment_abs_mean"] for row in per_cycle]
    spatial_records = {
        row["cycle"]: row["predicted_target_spatial_correlation"] for row in per_cycle
    }
    pairwise: list[float] = []
    nodal = torch.as_tensor(runtime.arrays["nodal_weight"], device=runtime.device)
    for left in range(len(predicted_fields)):
        for right in range(left + 1, len(predicted_fields)):
            value = _weighted_correlation(
                predicted_fields[left], predicted_fields[right], nodal)
            if value is not None:
                pairwise.append(value)
    growth_pred = [row["predicted_damage_increment_abs_mean"] for row in growth]
    stagnant_pred = [row["predicted_damage_increment_abs_mean"] for row in stagnant]
    aggregate: dict[str, Any] = {
        "update": update,
        "finite": True,
        "G": float(np.mean([row["damage_increment_mae"] for row in growth])),
        "F": float(np.mean([row["false_growth"] for row in stagnant])),
        "persistence": float(np.mean([
            row["true_damage_increment_abs_mean"] for row in growth
        ])),
        "L_judge": float(np.mean([row["L_judge"] for row in per_cycle])),
        "amplitude_ratio": group_amplitude_ratio(
            float(np.mean(growth_pred)), float(np.mean(stagnant_pred))),
        "amplitude_auc": amplitude_auc(growth_pred, stagnant_pred),
        "amplitude_pearson": _pearson(predicted_amplitudes, true_amplitudes),
        "amplitude_spearman": _pearson(
            _average_ranks(predicted_amplitudes), _average_ranks(true_amplitudes)),
        "spatial": fixed_support_median(spatial_records, EXPECTED_CYCLES),
        "predicted_field_pairwise_correlation": {
            "valid_pair_count": len(pairwise),
            "median": None if not pairwise else float(np.median(pairwise)),
            "minimum": None if not pairwise else float(np.min(pairwise)),
            "maximum": None if not pairwise else float(np.max(pairwise)),
        },
        "hard_constraint_counts": hard_total,
        "hard_constraint_violations": int(sum(hard_total.values())),
    }
    for name in LOSS_ORDER:
        aggregate[name] = float(np.mean([
            row["atomic_losses"][name] for row in per_cycle
        ]))
    for name in ("L_D", "L_U", "L_H", "L_P"):
        aggregate[name] = float(np.mean([
            row["grouped_losses"][name] for row in per_cycle
        ]))
    canonical_json({"aggregate": aggregate, "per_cycle": per_cycle})
    return {"aggregate": aggregate, "per_cycle": per_cycle}


def _replay_direction_with_legacy(
    model: torch.nn.Module, losses: Mapping[str, torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor, dict[str, Any], dict[str, Any]]:
    """Return reviewed R direction, same-forward g_D and exact E008 log schema."""
    from s09_e009_four_arm import replay_losses

    replay = replay_losses(losses)
    objectives = {
        OBJECTIVE_ORDER[0]: replay["J_N"],
        OBJECTIVE_ORDER[1]: replay["J_H"],
        OBJECTIVE_ORDER[2]: replay["J_P"],
        "L_D_alignment": grouped_losses(losses)["L_D"],
    }
    named = list(model.named_parameters())
    vectors: dict[str, torch.Tensor] = {}
    legacy_layout = []
    for objective_index, (objective_name, objective) in enumerate(objectives.items()):
        gradients = torch.autograd.grad(
            objective,
            [parameter for _, parameter in named],
            allow_unused=True,
            retain_graph=objective_index < len(objectives) - 1,
        )
        blocks, unconnected = [], []
        for (name, parameter), gradient in zip(named, gradients):
            if gradient is None:
                gradient = torch.zeros_like(parameter)
                unconnected.append(name)
            _require(gradient.shape == parameter.shape and torch.isfinite(gradient).all(),
                     f"invalid replay gradient block: {objective_name}/{name}",
                     FloatingPointError)
            blocks.append(gradient.reshape(-1))
        vector = torch.cat(blocks)
        vectors[objective_name] = vector
        if objective_name in OBJECTIVE_ORDER:
            legacy_layout.append({
                "objective": objective_name,
                "unconnected_parameters": unconnected,
                "parameter_block_count": len(blocks),
                "vector_length": vector.numel(),
            })
    replay_vectors = [vectors[name] for name in OBJECTIVE_ORDER]
    replay_norms = torch.stack([value.norm() for value in replay_vectors])
    _require(torch.isfinite(replay_norms).all(),
             "nonfinite norm at frozen replay-merger boundary", FloatingPointError)
    merged, diagnostics = merge_objective_gradients(replay_vectors)
    legacy = gradient_record(replay_vectors, merged, diagnostics)
    legacy["layout"] = {
        "parameter_order": [name for name, _ in named],
        "objectives": legacy_layout,
    }
    diagnostic = {
        "arm": ARM_REPLAY,
        "layout": {"parameter_order": [name for name, _ in named]},
        "clip_count_for_complete_direction": 1,
        "exact_replay_merger": diagnostics,
    }
    return merged, vectors["L_D_alignment"], diagnostic, legacy


class ArmAdapter(Protocol):
    """Small interface separating reviewed orchestration from numerical work."""

    packet_manifest_sha256: str
    initial_state_sha256: str
    hard_constraint_counts: dict[str, int]
    optimizer_steps_completed: int

    def evaluate(self, update: int) -> dict[str, Any]: ...
    def step(self, update: int, cycle: int) -> dict[str, Any]: ...
    def save_checkpoint(self, path: Path, update: int) -> None: ...


@dataclass
class ArmRunResult:
    arm: str
    arm_dir: Path
    receipt: dict[str, Any]
    evaluations: dict[int, dict[str, Any]]
    legacy_gradient_prefix_sha256: str | None


def _empty_counts() -> dict[str, int]:
    return {key: 0 for key in HARD_CONSTRAINT_KEYS}


def _artifact_hashes(arm_dir: Path, names: list[str]) -> dict[str, str]:
    return {name: sha256_file(arm_dir / name) for name in names if (arm_dir / name).is_file()}


def _validate_evaluation_record(record: Mapping[str, Any], update: int) -> None:
    """Reject partial or cross-checkpoint scorecards before they reach evidence."""
    _require(set(record) == {"aggregate", "per_cycle"},
             "evaluation record keys drift")
    aggregate = record["aggregate"]
    per_cycle = record["per_cycle"]
    _require(isinstance(aggregate, Mapping) and isinstance(per_cycle, list),
             "evaluation record shape drift")
    _require(aggregate.get("update") == update and aggregate.get("finite") is True,
             "evaluation checkpoint/finite status drift")
    _require(len(per_cycle) == len(EXPECTED_CYCLES) and
             [row.get("cycle") for row in per_cycle] == list(EXPECTED_CYCLES) and
             all(row.get("update") == update for row in per_cycle),
             "evaluation does not cover the fixed 16-cycle support")
    expected_groups = [
        "growth" if cycle in GROWTH_CYCLES else
        "near_stagnant" if cycle in NEAR_STAGNANT_CYCLES else "other"
        for cycle in EXPECTED_CYCLES
    ]
    _require([row.get("group") for row in per_cycle] == expected_groups,
             "evaluation group membership drift")
    row_keys = {
        "update", "cycle", "group", "predicted_damage_increment_abs_mean",
        "true_damage_increment_abs_mean", "damage_increment_mae", "false_growth",
        "predicted_target_spatial_correlation", "L_judge", "atomic_losses",
        "grouped_losses", "projection_counts", "hard_constraint_counts",
    }
    _require(all(set(row) == row_keys for row in per_cycle),
             "per-cycle scorecard keys drift")
    hard = aggregate.get("hard_constraint_counts")
    _require(isinstance(hard, Mapping) and tuple(hard) == HARD_CONSTRAINT_KEYS and
             all(type(value) is int and value >= 0 for value in hard.values()) and
             aggregate.get("hard_constraint_violations") == sum(hard.values()),
             "evaluation hard-constraint record drift")
    required = {
        "G", "F", "persistence", "L_judge", "amplitude_ratio",
        "amplitude_auc", "amplitude_pearson", "amplitude_spearman", "spatial",
        "predicted_field_pairwise_correlation", *LOSS_ORDER,
        "L_D", "L_U", "L_H", "L_P",
    }
    _require(required.issubset(aggregate), "evaluation scorecard is incomplete")
    growth = [row for row in per_cycle if row["group"] == "growth"]
    stagnant = [row for row in per_cycle if row["group"] == "near_stagnant"]
    _require(len(growth) == len(stagnant) == 5, "evaluation group support drift")

    def close(observed: Any, expected: float) -> bool:
        return isinstance(observed, (int, float)) and math.isfinite(float(observed)) and (
            abs(float(observed) - expected) <= 1e-12 + 1e-9 * abs(expected)
        )

    _require(close(aggregate["G"], float(np.mean([
        row["damage_increment_mae"] for row in growth
    ]))) and close(aggregate["F"], float(np.mean([
        row["false_growth"] for row in stagnant
    ]))) and close(aggregate["persistence"], float(np.mean([
        row["true_damage_increment_abs_mean"] for row in growth
    ]))) and close(aggregate["L_judge"], float(np.mean([
        row["L_judge"] for row in per_cycle
    ]))), "aggregate/per-cycle judgement drift")
    for name in LOSS_ORDER:
        _require(close(aggregate[name], float(np.mean([
            row["atomic_losses"][name] for row in per_cycle
        ]))), f"aggregate atomic loss drift: {name}")
    for name in ("L_D", "L_U", "L_H", "L_P"):
        _require(close(aggregate[name], float(np.mean([
            row["grouped_losses"][name] for row in per_cycle
        ]))), f"aggregate grouped loss drift: {name}")
    summed_hard = {name: sum(row["hard_constraint_counts"][name]
                             for row in per_cycle)
                   for name in HARD_CONSTRAINT_KEYS}
    _require(dict(hard) == summed_hard,
             "aggregate/per-cycle hard-constraint drift")
    canonical_json(record)


def run_arm_state_machine(
    *, arm: str, adapter: ArmAdapter, arm_dir: Path,
) -> ArmRunResult:
    """Run one exact 500-update arm through an adapter; tests use a mock."""
    _require(arm in ARM_ORDER, "unknown arm")
    _require(not arm_dir.exists(), "fresh arm directory already exists")
    arm_dir.mkdir(parents=True)
    schedule = build_schedule()
    start_identity = {
        "arm": arm,
        "packet_manifest_sha256": adapter.packet_manifest_sha256,
        "initial_state_sha256": adapter.initial_state_sha256,
        "schedule": list(schedule),
        "updates_per_arm": UPDATES_PER_ARM,
    }
    _write_new_json(arm_dir / "start_identity.json", start_identity)
    evaluations: dict[int, dict[str, Any]] = {}
    legacy_digest = hashlib.sha256() if arm == ARM_REPLAY else None
    steps = logged = 0
    stop_update = 0
    checkpoint_present = False
    state = TERMINAL_EXECUTION_FAILED
    reason: str | None = None
    finite = True
    hard_counts = _empty_counts()
    evaluation_updates: list[int] = []
    train_path = arm_dir / "train_log.jsonl"
    gradient_path = arm_dir / "gradient_diagnostics.jsonl"
    diagnostic_path = arm_dir / "diagnostic_metrics.jsonl"
    checkpoint_path = arm_dir / "checkpoint_update500.pt"
    checkpoint_partial = arm_dir / ".checkpoint_update500.pt.partial"
    try:
        with train_path.open("xb") as train_stream, \
             gradient_path.open("xb") as gradient_stream, \
             diagnostic_path.open("xb") as diagnostic_stream:
            initial = adapter.evaluate(0)
            _validate_evaluation_record(initial, 0)
            evaluations[0] = initial
            hard_counts = dict(initial["aggregate"]["hard_constraint_counts"])
            _require(sum(hard_counts.values()) == 0,
                     "initial hard-constraint violation")
            diagnostic_stream.write(canonical_json(initial))
            diagnostic_stream.flush()
            evaluation_updates.append(0)
            for update, cycle in enumerate(schedule, start=1):
                stop_update = update
                result = adapter.step(update, cycle)
                train_row = result["train_row"]
                gradient_row = result["gradient_row"]
                _require(train_row["update"] == gradient_row["update"] == update and
                         train_row["cycle"] == gradient_row["cycle"] == cycle,
                         "adapter update/cycle record drift")
                train_stream.write(canonical_json(train_row)); train_stream.flush()
                gradient_stream.write(canonical_json(gradient_row)); gradient_stream.flush()
                steps = update
                logged = update
                if arm == ARM_REPLAY:
                    legacy_row = result.get("legacy_gradient_row")
                    _require(isinstance(legacy_row, Mapping),
                             "replay adapter omitted legacy gradient record")
                    legacy_digest.update(canonical_json(legacy_row))
                if update in EVALUATION_UPDATES[1:]:
                    evaluation = adapter.evaluate(update)
                    _validate_evaluation_record(evaluation, update)
                    evaluations[update] = evaluation
                    hard_counts = dict(evaluation["aggregate"]["hard_constraint_counts"])
                    _require(sum(hard_counts.values()) == 0,
                             "evaluation hard-constraint violation")
                    diagnostic_stream.write(canonical_json(evaluation))
                    diagnostic_stream.flush()
                    evaluation_updates.append(update)
        adapter.save_checkpoint(checkpoint_partial, UPDATES_PER_ARM)
        _require(checkpoint_partial.is_file(), "checkpoint adapter produced no file")
        os.replace(checkpoint_partial, checkpoint_path)
        checkpoint_present = True
        state = TERMINAL_COMPLETED
        stop_update = UPDATES_PER_ARM
    except AnchorStationary:
        state = TERMINAL_METHOD_INAPPLICABLE
        reason = "ANCHOR_STATIONARY_OR_INAPPLICABLE"
    except Exception as error:
        state = TERMINAL_EXECUTION_FAILED
        reason = f"{type(error).__name__}: {error}"
        finite = not isinstance(error, FloatingPointError)
    finally:
        checkpoint_partial.unlink(missing_ok=True)

    observed_steps = getattr(adapter, "optimizer_steps_completed", steps)
    _require(type(observed_steps) is int and steps <= observed_steps <= UPDATES_PER_ARM,
             "adapter optimizer-step counter drift")
    steps = observed_steps

    common = [
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl",
    ]
    artifacts = _artifact_hashes(arm_dir, common)
    if checkpoint_present:
        artifacts["checkpoint_update500.pt"] = sha256_file(
            checkpoint_path)
    receipt = {
        "arm": arm,
        "terminal_state": state,
        "stop_update": stop_update,
        "optimizer_steps_completed": steps,
        "fully_logged_updates": logged,
        "evaluation_updates_present": evaluation_updates,
        "last_valid_evaluation_update": (
            evaluation_updates[-1] if evaluation_updates else None),
        "reason": reason,
        "update500_checkpoint_present": checkpoint_present,
        "finite_status": finite,
        "hard_constraint_counts": hard_counts,
        "artifacts": artifacts,
    }
    validate_termination_receipt(receipt)
    _write_new_json(arm_dir / "termination_receipt.json", receipt)
    return ArmRunResult(
        arm=arm,
        arm_dir=arm_dir,
        receipt=receipt,
        evaluations=evaluations,
        legacy_gradient_prefix_sha256=(
            None if legacy_digest is None else legacy_digest.hexdigest()),
    )


class TorchArmAdapter:
    """Future producer adapter. Its step method is never called by local tests."""

    def __init__(self, *, arm: str, runtime: Runtime, optimizer: torch.optim.AdamW,
                 config_sha256: str):
        self.arm = arm
        self.runtime = runtime
        self.optimizer = optimizer
        self.config_sha256 = config_sha256
        self.packet_manifest_sha256 = runtime.packet_identity["manifest_sha256"]
        self.initial_state_sha256 = parameter_state_sha256(runtime.model)
        self.hard_constraint_counts = _empty_counts()
        self.optimizer_steps_completed = 0
        self.cycle_to_index = {
            int(cycle): index for index, cycle in enumerate(runtime.arrays["cycles"].tolist())
        }

    def evaluate(self, update: int) -> dict[str, Any]:
        return evaluate_arm(self.runtime, update=update)

    def step(self, update: int, cycle: int) -> dict[str, Any]:
        from s09_e009_four_arm import atomic_losses

        _require(cycle in self.cycle_to_index, "scheduled cycle missing from runtime")
        index = self.cycle_to_index[cycle]
        self.runtime.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        losses, context = atomic_losses(self.runtime, index)
        legacy = None
        if self.arm == ARM_REPLAY:
            direction, g_d, diagnostic, legacy = _replay_direction_with_legacy(
                self.runtime.model, losses)
        else:
            direction, g_d, diagnostic = _direction_with_damage_reference(
                self.runtime.model, losses, self.arm)
        before, parameter_order = flattened_parameters(self.runtime.model)
        _require(diagnostic["layout"]["parameter_order"] == parameter_order,
                 "per-update parameter order drift")
        assign_merged_gradient(self.runtime.model, direction, parameter_order)
        self.optimizer.step()
        self.optimizer_steps_completed += 1
        after, after_order = flattened_parameters(self.runtime.model)
        _require(after_order == parameter_order, "post-step parameter order drift")
        alignment = parameter_displacement_alignment(g_d, before, after)
        atomic = {name: float(losses[name].detach().cpu()) for name in LOSS_ORDER}
        groups = grouped_losses(losses)
        train_row = {
            "update": update,
            "cycle": cycle,
            "atomic_losses": atomic,
            "grouped_losses": {
                name: float(value.detach().cpu()) for name, value in groups.items()
            },
            "proposal_projection_counts": proposal_projection_diagnostics(
                self.runtime, context["d_pre"], context["output"]),
            "hard_constraint_counts": hard_constraint_report(
                self.runtime, context["d_pre"], context["history_pre"],
                context["output"],
            ),
        }
        direction_norm = torch.linalg.vector_norm(direction)
        damage_norm = torch.linalg.vector_norm(g_d)
        damage_dot = g_d.dot(direction)
        _require(torch.isfinite(direction_norm) and torch.isfinite(damage_norm) and
                 torch.isfinite(damage_dot), "nonfinite damage/direction geometry",
                 FloatingPointError)
        damage_cosine = None if direction_norm <= 1e-12 or damage_norm <= 1e-12 else float(
            (damage_dot / (direction_norm * damage_norm)).detach().cpu())
        gradient_row = {
            "update": update,
            "cycle": cycle,
            "arm": self.arm,
            "layout": diagnostic["layout"],
            "direction_sha256": _direction_sha256(direction),
            "damage_gradient_sha256": _direction_sha256(g_d),
            "direction_norm": float(direction_norm.detach().cpu()),
            "damage_gradient_norm": float(damage_norm.detach().cpu()),
            "damage_direction_dot": float(damage_dot.detach().cpu()),
            "damage_direction_cosine": damage_cosine,
            "clip_count_for_complete_direction":
                diagnostic["clip_count_for_complete_direction"],
            "direction_diagnostics": (
                {"arm": ARM_REPLAY,
                 "clip_count_for_complete_direction": 1,
                 "layout": legacy["layout"],
                 "exact_replay_merger": legacy}
                if legacy is not None else diagnostic
            ),
            "parameter_displacement_alignment": alignment,
        }
        if legacy is not None:
            legacy = {"update": update, "cycle": cycle, **legacy}
        return {
            "train_row": train_row,
            "gradient_row": gradient_row,
            "legacy_gradient_row": legacy,
        }

    def save_checkpoint(self, path: Path, update: int) -> None:
        _require(update == UPDATES_PER_ARM, "checkpoint update drift")
        torch.save({
            "model": self.runtime.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "update": update,
            "arm": self.arm,
            "config_sha256": self.config_sha256,
            "packet_sha256": self.packet_manifest_sha256,
        }, path)


def replay_validity(result: ArmRunResult) -> dict[str, Any]:
    """Apply the exact update-0/update-500 and legacy-log replay contract."""
    clauses: dict[str, bool] = {}
    for update, reference in REPLAY_REFERENCE.items():
        observed = result.evaluations.get(update, {}).get("aggregate", {})
        mapping = {
            "L_judge": observed.get("L_judge"),
            "G": observed.get("G"),
            "persistence": observed.get("persistence"),
            "F": observed.get("F"),
            "hard_constraint_violations": observed.get("hard_constraint_violations"),
        }
        for name, expected in reference.items():
            value = mapping[name]
            if name == "hard_constraint_violations":
                passed = type(value) is int and value == expected
            else:
                passed = isinstance(value, (int, float)) and math.isfinite(float(value)) and (
                    abs(float(value) - float(expected)) <= 1e-12 + 1e-9 * abs(float(expected))
                )
            clauses[f"update_{update}_{name}"] = passed
    clauses["first_500_legacy_gradient_rows_sha256"] = (
        result.legacy_gradient_prefix_sha256 == REPLAY_GRADIENT_PREFIX_SHA256)
    clauses["terminal_completed"] = (
        result.receipt["terminal_state"] == TERMINAL_COMPLETED)
    return {"pass": all(clauses.values()), "clauses": clauses,
            "observed_legacy_gradient_sha256": result.legacy_gradient_prefix_sha256,
            "expected_legacy_gradient_sha256": REPLAY_GRADIENT_PREFIX_SHA256}


def _scorecard(metrics: Mapping[str, Any]) -> dict[str, float]:
    return {
        "G": float(metrics["G"]),
        "F": float(metrics["F"]),
        "AUC": float(metrics["amplitude_auc"]["value"]),
        "L_P": float(metrics["L_P"]),
        "L_judge": float(metrics["L_judge"]),
        **{name: float(metrics[name]) for name in LOSS_ORDER},
    }


def _read_gradient_summary(result: ArmRunResult) -> dict[str, Any]:
    try:
        rows = [
            json.loads(
                line,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            )
            for line in (result.arm_dir / "gradient_diagnostics.jsonl").read_text().splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        _require(result.receipt["terminal_state"] != TERMINAL_COMPLETED,
                 f"{result.arm} completed gradient log is unreadable")
        return {"summary_status": "INVALID_PARTIAL_LOG", "error": str(error)}
    expected = result.receipt["fully_logged_updates"]
    _require(len(rows) == expected and
             [row.get("update") for row in rows] == list(range(1, expected + 1)),
             f"{result.arm} gradient log/update count drift")
    if not rows:
        return {"logged_updates": 0, "clip_applied_count": 0,
                "positive_damage_alignment_count": 0,
                "defined_damage_alignment_cosine_count": 0,
                "median_damage_alignment_cosine": None}
    clip_count = 0
    positive = 0
    cosines: list[float] = []
    for row in rows:
        diagnostic = row["direction_diagnostics"]
        if result.arm == ARM_REPLAY:
            merger = diagnostic["exact_replay_merger"]
            clip_count += merger["merged_norm_before_clip"] > merger["merged_norm_after_clip"]
        else:
            clip_count += bool(diagnostic.get("clip_applied", False))
        alignment = row["parameter_displacement_alignment"]
        positive += alignment["g_D_dot_negative_delta_theta"] > 0
        if alignment["cosine"] is not None:
            cosines.append(float(alignment["cosine"]))
    return {
        "logged_updates": len(rows),
        "clip_applied_count": int(clip_count),
        "positive_damage_alignment_count": int(positive),
        "defined_damage_alignment_cosine_count": len(cosines),
        "median_damage_alignment_cosine": (
            None if not cosines else float(np.median(cosines))
        ),
        "final_direction_diagnostics": rows[-1]["direction_diagnostics"],
    }


def _decision_from_results(
    arm_results: Mapping[str, ArmRunResult],
) -> dict[str, Any]:
    _require(tuple(arm_results) == ARM_ORDER, "arm result order drift")
    receipts = {arm: result.receipt for arm, result in arm_results.items()}
    for receipt in receipts.values():
        validate_termination_receipt(receipt)
    start_records = [json.loads((result.arm_dir / "start_identity.json").read_text())
                     for result in arm_results.values()]
    shared_identity = (
        len({record["packet_manifest_sha256"] for record in start_records}) == 1 and
        len({record["initial_state_sha256"] for record in start_records}) == 1 and
        all(record["schedule"] == list(build_schedule()) for record in start_records)
    )
    replay = replay_validity(arm_results[ARM_REPLAY])
    eligible = cross_arm_performance_eligible(
        shared_identity_pass=shared_identity,
        replay_gate_pass=replay["pass"],
    )
    status: str
    classification = None
    spatial_axis = None
    if any(receipt["terminal_state"] == TERMINAL_EXECUTION_FAILED
           for receipt in receipts.values()):
        status = "EXECUTION_INVALID"
    elif not eligible:
        status = "EXECUTION_INVALID"
    elif receipts[ARM_ANCHOR_25]["terminal_state"] == TERMINAL_METHOD_INAPPLICABLE:
        status = "METHOD_INAPPLICABLE"
    elif receipts[ARM_ANCHOR_25]["terminal_state"] != TERMINAL_COMPLETED:
        status = "EXECUTION_INVALID"
    else:
        replay_final = arm_results[ARM_REPLAY].evaluations[500]["aggregate"]
        candidate_final = arm_results[ARM_ANCHOR_25].evaluations[500]["aggregate"]
        classification = classify_a25(
            _scorecard(candidate_final), _scorecard(replay_final))
        status = classification["status"]
        candidate_spatial = candidate_final["spatial"]
        replay_spatial = replay_final["spatial"]
        if (candidate_spatial["primary_status"] == "NA" or
                replay_spatial["primary_status"] == "NA"):
            spatial_axis = "SPATIAL_COMPARISON_NA"
        elif (candidate_final["amplitude_auc"]["value"] >= 0.80 and
              candidate_spatial["primary_median"] <= replay_spatial["primary_median"]):
            spatial_axis = "AMPLITUDE_SEPARATION_ONLY__TEMPLATE_UNRESOLVED"
        else:
            spatial_axis = "SPATIAL_AXIS_REPORTED"
    return {
        "status": status,
        "cross_arm_performance_eligible": eligible,
        "shared_identity_pass": shared_identity,
        "replay_gate": replay,
        "terminal_states": {arm: receipt["terminal_state"]
                            for arm, receipt in receipts.items()},
        "a25_classification": classification,
        "spatial_axis": spatial_axis,
        "update500_metrics": {
            arm: result.evaluations.get(500, {}).get("aggregate")
            for arm, result in arm_results.items()
        },
        "gradient_summaries": {
            arm: _read_gradient_summary(result)
            for arm, result in arm_results.items()
        },
        "claim_boundary": (
            "development-only four-arm repair screen; no rollout, generalisation, "
            "FEM-truth, full fracture-evolution PINO or real-road claim"
        ),
    }


def write_shared_evidence(
    *, output_dir: Path, config: Mapping[str, Any],
    arm_results: Mapping[str, ArmRunResult], environment: Mapping[str, Any],
    run_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the full shared evaluator/decision package from exact checkpoints."""
    decision = _decision_from_results(arm_results)
    _write_new_json(output_dir / "decision_metrics.json", decision)

    table_path = output_dir / "decision_table.csv"
    with table_path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "arm", "terminal_state", "G", "F", "AUC", "L_P", "L_judge",
            "spatial_primary_median", "spatial_status",
        ])
        writer.writeheader()
        for arm in ARM_ORDER:
            result = arm_results[arm]
            metrics = result.evaluations.get(500, {}).get("aggregate")
            writer.writerow({
                "arm": arm,
                "terminal_state": result.receipt["terminal_state"],
                "G": "" if metrics is None else metrics["G"],
                "F": "" if metrics is None else metrics["F"],
                "AUC": "" if metrics is None else metrics["amplitude_auc"]["value"],
                "L_P": "" if metrics is None else metrics["L_P"],
                "L_judge": "" if metrics is None else metrics["L_judge"],
                "spatial_primary_median": "" if metrics is None else
                    metrics["spatial"]["primary_median"],
                "spatial_status": "" if metrics is None else
                    metrics["spatial"]["primary_status"],
            })

    per_cycle_path = output_dir / "per_cycle_metrics.csv"
    fields = [
        "arm", "update", "cycle", "group",
        "predicted_damage_increment_abs_mean", "true_damage_increment_abs_mean",
        "damage_increment_mae", "false_growth",
        "predicted_target_spatial_correlation", "L_judge",
    ]
    with per_cycle_path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for arm in ARM_ORDER:
            for update in EVALUATION_UPDATES:
                evaluation = arm_results[arm].evaluations.get(update)
                if evaluation is None:
                    continue
                for row in evaluation["per_cycle"]:
                    writer.writerow({"arm": arm, **{name: row[name] for name in fields[1:]}})

    import matplotlib.pyplot as plt
    completed = [arm for arm in ARM_ORDER if 500 in arm_results[arm].evaluations]
    figure_path = output_dir / "decision_figure.png"
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.8))
    labels = [arm.split("_")[0] for arm in completed]
    final_metrics = [arm_results[arm].evaluations[500]["aggregate"] for arm in completed]
    axes[0].bar(labels, [row["G"] for row in final_metrics], color="#4477AA")
    axes[0].axhline(0.0005017354462152066, color="#CC3311", linestyle="--",
                    label="persistence")
    axes[0].set_title("Growth MAE at update 500")
    axes[0].set_ylabel("weighted damage increment MAE")
    axes[0].legend(fontsize=7)
    axes[1].bar(labels, [row["F"] for row in final_metrics], color="#66CCEE")
    axes[1].set_title("Near-stagnant false growth")
    axes[1].set_ylabel("weighted false growth")
    axes[2].bar(labels, [row["amplitude_auc"]["value"] for row in final_metrics],
                color="#228833")
    axes[2].axhline(0.80, color="#CC3311", linestyle="--", label="AUC 0.80")
    axes[2].set_ylim(0, 1)
    axes[2].set_title("Growth/stagnant amplitude AUC")
    axes[2].legend(fontsize=7)
    fig.suptitle(f"{PLANNED_RUN_ID} | development-only | fixed update 500")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)

    decision_text = (
        f"# {PLANNED_RUN_ID} decision\n\n"
        f"Claim verdict: {decision['status']}\n\n"
        "Evidence domain: synthetic development trajectory.\n\n"
        f"Cross-arm performance eligible: {decision['cross_arm_performance_eligible']}\n\n"
        f"Spatial axis: {decision['spatial_axis']}\n\n"
        "The figure and CSV use every completed arm at the one frozen update-500 "
        "checkpoint. No checkpoint selection was performed.\n\n"
        f"Claim boundary: {decision['claim_boundary']}.\n"
    )
    _write_new_bytes(output_dir / "decision.md", decision_text.encode("utf-8"))

    required_common = config["evidence"]["required_per_arm_common"]
    required_completed = config["evidence"]["required_completed_arm_only"]
    missing: list[str] = []
    for arm, result in arm_results.items():
        for name in required_common:
            if not (result.arm_dir / name).is_file():
                missing.append(f"{arm}/{name}")
        if result.receipt["terminal_state"] == TERMINAL_COMPLETED:
            for name in required_completed:
                if not (result.arm_dir / name).is_file():
                    missing.append(f"{arm}/{name}")
    shared_written = {
        "decision_metrics.json", "decision_table.csv", "decision_figure.png",
        "per_cycle_metrics.csv", "decision.md",
    }
    expected_preexisting = {
        "config_resolved.json", "input_packet_identity.json", "environment.txt",
    }
    for name in expected_preexisting:
        if not (output_dir / name).is_file():
            missing.append(name)
    _require(not missing, f"evidence manifest incomplete: {sorted(missing)}")

    completion = {
        "schema_version": SCHEMA_VERSION,
        "run_id": PLANNED_RUN_ID,
        "status": "SUCCEEDED" if all(
            result.receipt["terminal_state"] in
            (TERMINAL_COMPLETED, TERMINAL_METHOD_INAPPLICABLE)
            for result in arm_results.values()) else "PARTIAL_OR_FAILED",
        "total_optimizer_steps_completed": int(sum(
            result.receipt["optimizer_steps_completed"] for result in arm_results.values())),
        "total_update_cap": TOTAL_UPDATE_CAP,
        "arm_receipts": {arm: result.receipt for arm, result in arm_results.items()},
        "decision": decision,
        "producer": dict(environment),
        "run_metadata": dict(run_metadata or {}),
        "shared_artifacts": {
            name: sha256_file(output_dir / name)
            for name in sorted(shared_written | expected_preexisting)
        },
    }
    _write_new_json(output_dir / "completion_receipt.json", completion)
    expected_shared = set(config["evidence"]["required_shared"])
    _require(expected_shared == shared_written | expected_preexisting |
             {"completion_receipt.json"}, "shared evidence declaration drift")
    return completion


def _execution_preflight(
    *, config: Mapping[str, Any], output_dir: Path, repo_root: Path,
) -> dict[str, Any]:
    _require(sys.platform.startswith("linux"), "E009 training is forbidden off Linux",
             PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible,
             "exactly one CUDA_VISIBLE_DEVICES entry is required")
    observed = _environment_snapshot(visible)
    _require(observed == config["producer"]["resolved_environment"],
             "producer environment differs from resolved preflight")
    _require(current_commit(repo_root) == config["source"]["training_commit"] ==
             config["source"]["producer_package_reviewed_commit"],
             "producer commit identity mismatch")
    _require(_producer_execution_files_clean(repo_root),
             "tracked execution files are dirty")
    output_dir, _ = validated_producer_paths(output_dir, dict(config))
    _require(not output_dir.exists(), "fresh output root already exists")
    _require(shutil.disk_usage(output_dir.parent).free >= 5 * 1024**3,
             "less than 5 GiB free at Taobo run root")
    return observed


def run_producer(
    *, packet_dir: Path, resolved_config_path: Path,
    base_runtime_config_path: Path, output_dir: Path, repo_root: Path,
) -> dict[str, Any]:
    """Execute from one captured config/base snapshot after final authorisation."""
    resolved_config_path = resolved_config_path.resolve(strict=True)
    resolved_raw = resolved_config_path.read_bytes()
    base_raw = base_runtime_config_path.read_bytes()
    _require(hashlib.sha256(base_raw).hexdigest() == EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
             "base runtime config differs from reviewed identity")
    preview = _parse_strict_json_bytes(resolved_raw)
    receipt = preview.get("resolution_receipt", {})
    _require(receipt.get("resolved_config_path") == str(resolved_config_path),
             "resolved config path differs from resolution receipt")
    staging_root = Path(receipt.get("staging_root", ""))
    _require(staging_root.is_absolute() and resolved_config_path.parent == staging_root,
             "resolved config is outside its approved staging root")
    with tempfile.TemporaryDirectory(prefix="run-snapshot-", dir=staging_root) as temp_dir:
        snapshot_root = Path(temp_dir)
        resolved_snapshot = snapshot_root / "config_resolved.json"
        base_snapshot = snapshot_root / "base_runtime.json"
        resolved_snapshot.write_bytes(resolved_raw)
        base_snapshot.write_bytes(base_raw)
        return _run_producer_snapshots(
            packet_dir=packet_dir,
            resolved_config_path=resolved_snapshot,
            base_runtime_config_path=base_snapshot,
            output_dir=output_dir,
            repo_root=repo_root,
        )


def _run_producer_snapshots(
    *, packet_dir: Path, resolved_config_path: Path,
    base_runtime_config_path: Path, output_dir: Path, repo_root: Path,
) -> dict[str, Any]:
    """Internal runner whose config inputs are immutable task-owned snapshots."""
    config = _load_json(resolved_config_path)
    packet_identity = json.loads((packet_dir / "packet_identity.json").read_text())
    validate_resolved_config(
        config,
        base_runtime_config_path=base_runtime_config_path,
        packet_manifest_sha256=packet_identity["manifest_sha256"],
        executable=True,
    )
    output_dir, archive_dir = validated_producer_paths(output_dir, config)
    _require(not archive_dir.exists(), "fresh archive root already exists")
    archive_dir.mkdir(parents=False)
    start = time.time()
    try:
        environment = _execution_preflight(
            config=config, output_dir=output_dir, repo_root=repo_root)
        device = torch.device("cuda:0")
        torch.manual_seed(int(config["model"]["seed"]))
        torch.cuda.manual_seed_all(int(config["model"]["seed"]))
        base_runtime = build_runtime(
            packet_dir=packet_dir,
            config_path=base_runtime_config_path,
            device=device,
            executable=False,
        )
        from s09_e009_four_arm import initialise_arm_states
        options = config["optimisation"]
        models, optimizers, isolation = initialise_arm_states(
            base_runtime.model,
            learning_rate=options["learning_rate"],
            betas=tuple(options["betas"]),
            optimizer_epsilon=options["epsilon"],
            weight_decay=options["weight_decay"],
        )
        _require(isolation["parameter_objects_disjoint"] and
                 isolation["optimizer_states_empty"], "arm isolation failure")
        output_dir.mkdir(parents=False)
        _write_new_bytes(output_dir / "config_resolved.json",
                         resolved_config_path.read_bytes())
        _write_new_json(output_dir / "input_packet_identity.json", packet_identity)
        _write_new_bytes(output_dir / "environment.txt", (
            json.dumps(environment, indent=2, sort_keys=True) + "\n").encode())
        config_sha = sha256_file(resolved_config_path)
        arm_results: dict[str, ArmRunResult] = {}
        for arm in ARM_ORDER:
            runtime = replace(base_runtime, model=models[arm])
            adapter = TorchArmAdapter(
                arm=arm, runtime=runtime, optimizer=optimizers[arm],
                config_sha256=config_sha)
            arm_results[arm] = run_arm_state_machine(
                arm=arm, adapter=adapter, arm_dir=output_dir / arm)
            if arm == ARM_REPLAY and not replay_validity(arm_results[arm])["pass"]:
                raise RuntimeError("REPLAY_VALIDITY_GATE_FAILED")
        completion = write_shared_evidence(
            output_dir=output_dir, config=config,
            arm_results=arm_results, environment=environment,
            run_metadata={"elapsed_seconds_before_evidence_close": time.time() - start,
                          "config_sha256": config_sha})
        _write_new_json(archive_dir / "completion_receipt.json", completion)
        return completion
    except BaseException as error:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "run_id": config.get("planned_run_id"),
            "status": "FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
            "elapsed_seconds": time.time() - start,
            "training_commit": config.get("source", {}).get("training_commit"),
            "expected_packet_manifest_sha256":
                config.get("source", {}).get("input_packet_sha256"),
        }
        _write_new_json(archive_dir / "completion_receipt.json", failure)
        raise
