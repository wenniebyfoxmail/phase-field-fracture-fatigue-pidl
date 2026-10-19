#!/usr/bin/env python3
"""Read-only local-support sensitivity decomposition for frozen S09 states.

The script performs one forward/autograd collection for each unique cycle and
state, then constructs the 25 pair quantities algebraically.  It never calls
an optimiser step and reconstructs the exact next AdamW displacement directly
from the checkpoint state dictionary.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
import csv
import hashlib
import json
import math
from pathlib import Path
import socket
import sys
import time
from typing import Any, Callable, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from s09_e009_four_arm import (  # noqa: E402
    GLOBAL_CLIP_NORM,
    NORM_EPSILON,
    _stable_l2_norm,
    atomic_losses,
    clip_complete_direction,
    flattened_objective_gradients,
    flattened_parameters,
    grouped_losses,
    parameter_state_sha256,
)
from s09_e010_support_amplitude import (  # noqa: E402
    balanced_direction_components,
    support_amplitude_losses,
)
from s09_e011_ranking_objective import (  # noqa: E402
    AMPLITUDE_NORMALISER,
    ARM_CONTROL,
    ARM_RANK,
    BETA,
    OBJECTIVE_ORDER,
    PAIR_ORDER,
    RANK_COEFFICIENT,
    RANK_TEMPERATURE,
    merge_ranking_gradients,
)
from s09_stage0a_p1_trainer import build_runtime  # noqa: E402


RUN_ID = "S09-E012-R001-local-support-sensitivity"
SUPPORT_THRESHOLD = 1.0e-15
USABLE_RELATIVE_CONTRAST = 1.0e-4
HELPFUL_COSINE = 1.0e-3
NODE_DECODER_ENERGY_LIMIT = 1.0e-4
STATE_ORDER = ("S0_B25_start", "C500_control", "R500_ranking")
EXPECTED_INPUT_SHA256 = {
    "start_checkpoint": "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05",
    "control_checkpoint": "7a3f83e23536f4b4ce560ca208c7fd607ab4bea5f7b698b9d288c584cd98b057",
    "ranking_checkpoint": "a3f2f83bd2c86f8bc3a455c899ddc5ea0d5e394b8b6f5930950d4e5dbb024c8d",
    "e010_per_cycle_csv": "2f38ead95c9596418f42a7d8aaaa2050fac938040ebd3804209f196c1ebc247e",
    "e011_per_cycle_csv": "8acc97ba34aa3f936a949b49cb36a7ff4fde35015b06eb9d23868e062c37de52",
    "base_config": "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b",
    "resolved_config": "be399942c28d640da8e61a2f47f680433b546ce502c5791bb88ee7297a9542b4",
}
EXPECTED_PACKET_MANIFEST_SHA256 = (
    "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def local_support_score(
    predicted_increment: torch.Tensor,
    target_increment: torch.Tensor,
    nodal_weight: torch.Tensor,
    *,
    threshold: float = SUPPORT_THRESHOLD,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Return support mean minus background mean using a frozen target mask."""
    _require(
        predicted_increment.shape == target_increment.shape == nodal_weight.shape,
        "local-support field shape drift",
    )
    _require(predicted_increment.ndim == 1, "local-support fields must be vectors")
    _require(math.isfinite(threshold) and threshold >= 0, "invalid support threshold")
    _require(
        torch.isfinite(predicted_increment).all().item()
        and torch.isfinite(target_increment).all().item()
        and torch.isfinite(nodal_weight).all().item(),
        "nonfinite local-support input",
    )
    _require((predicted_increment >= 0).all().item(), "projected increment is negative")
    support = target_increment > threshold
    background = ~support
    support_weight = nodal_weight[support].sum()
    background_weight = nodal_weight[background].sum()
    _require(
        support.any().item() and background.any().item(),
        "support/background partition is empty",
    )
    _require(
        support_weight.item() > 0 and background_weight.item() > 0,
        "support/background weighted area is empty",
    )
    projected = predicted_increment
    local_mean = (projected[support] * nodal_weight[support]).sum() / support_weight
    background_mean = (
        projected[background] * nodal_weight[background]
    ).sum() / background_weight
    score = local_mean - background_mean
    total_weight = nodal_weight.sum()
    predicted_mass = (projected * nodal_weight).sum()
    predicted_support_mass = (projected[support] * nodal_weight[support]).sum()
    target_mass = (target_increment.abs() * nodal_weight).sum()
    support_mass = (target_increment[support].abs() * nodal_weight[support]).sum()
    return score, {
        "support_weight_fraction": float((support_weight / total_weight).detach().cpu()),
        "target_increment_mass_fraction_in_support": float(
            (support_mass / target_mass).detach().cpu()
        ) if target_mass.item() > 0 else 0.0,
        "predicted_increment_mass_fraction_in_support": float(
            (predicted_support_mass / predicted_mass).detach().cpu()
        ) if predicted_mass.item() > 0 else 0.0,
        "local_mean": float(local_mean.detach().cpu()),
        "background_mean": float(background_mean.detach().cpu()),
        "score": float(score.detach().cpu()),
    }


def ranking_gradient_from_margin(
    margin: float,
    margin_gradient: torch.Tensor,
    *,
    normaliser: float = AMPLITUDE_NORMALISER,
    temperature: float = RANK_TEMPERATURE,
) -> tuple[torch.Tensor, float]:
    """Construct d softplus(-margin/(D*tau)) / d theta algebraically."""
    _require(math.isfinite(margin), "nonfinite ranking margin")
    _require(math.isfinite(normaliser) and normaliser > 0, "invalid ranking normaliser")
    _require(math.isfinite(temperature) and temperature > 0, "invalid ranking temperature")
    argument = -margin / (normaliser * temperature)
    coefficient = -float(torch.sigmoid(torch.tensor(argument, dtype=torch.float64))) / (
        normaliser * temperature
    )
    gradient = coefficient * margin_gradient
    _require(torch.isfinite(gradient).all().item(), "nonfinite ranking gradient")
    return gradient, coefficient


def projected_rank_component(
    anchor: torch.Tensor,
    rank_gradient: torch.Tensor,
    *,
    eps: float = NORM_EPSILON,
) -> torch.Tensor:
    """Reproduce the E011 norm-match/conflict projection for the rank term."""
    anchor_norm = _stable_l2_norm(anchor)
    rank_norm = _stable_l2_norm(rank_gradient)
    _require(anchor_norm.item() > eps, "damage anchor is stationary")
    if rank_norm.item() <= eps:
        return torch.zeros_like(rank_gradient)
    balanced = anchor_norm * rank_gradient / rank_norm
    cosine = anchor.dot(balanced) / anchor_norm.square()
    projected = balanced - torch.minimum(cosine, cosine.new_zeros(())) * anchor
    if _stable_l2_norm(projected).item() <= eps:
        return torch.zeros_like(projected)
    return projected


def preclip_merge(
    gradients: Mapping[str, torch.Tensor], arm: str
) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor]]:
    """Return exact preclip merge and the projected rank component."""
    _require(tuple(gradients) == OBJECTIVE_ORDER, "objective order drift")
    base = OrderedDict((name, gradients[name]) for name in OBJECTIVE_ORDER[:-1])
    components, _ = balanced_direction_components(base)
    q_rank = projected_rank_component(components["L_D"], gradients["L_R"])
    merged = (
        components["L_D"]
        + components["L_S"]
        + components["L_A"]
        + components["L_U"]
        + components["L_H"]
        + BETA * components["L_P"]
    )
    if arm == ARM_RANK:
        merged = merged + RANK_COEFFICIENT * q_rank
    return merged, q_rank, components


def adamw_displacement_from_state_dict(
    gradient: torch.Tensor,
    named_parameters: list[tuple[str, torch.nn.Parameter]],
    optimizer_state: Mapping[str, Any],
) -> torch.Tensor:
    """Compute the exact next AdamW displacement without constructing an optimiser."""
    groups = optimizer_state["param_groups"]
    _require(len(groups) == 1, "exactly one AdamW group is required")
    group = groups[0]
    _require(group["weight_decay"] == 0.0, "weight decay must be zero")
    _require(not group["amsgrad"] and not group.get("maximize", False), "unsupported AdamW mode")
    parameter_ids = group["params"]
    _require(len(parameter_ids) == len(named_parameters), "optimizer parameter count drift")
    beta1, beta2 = group["betas"]
    lr, eps = float(group["lr"]), float(group["eps"])
    blocks: list[torch.Tensor] = []
    cursor = 0
    for parameter_id, (_, parameter) in zip(parameter_ids, named_parameters):
        count = parameter.numel()
        block = gradient[cursor : cursor + count].reshape_as(parameter)
        cursor += count
        state = optimizer_state["state"][parameter_id]
        exp_avg = state["exp_avg"].to(device=block.device, dtype=block.dtype)
        exp_avg_sq = state["exp_avg_sq"].to(device=block.device, dtype=block.dtype)
        step_raw = state["step"]
        step = int(step_raw.item() if torch.is_tensor(step_raw) else step_raw) + 1
        next_avg = beta1 * exp_avg + (1.0 - beta1) * block
        next_sq = beta2 * exp_avg_sq + (1.0 - beta2) * block.square()
        denominator = next_sq.sqrt() / math.sqrt(1.0 - beta2**step) + eps
        delta = -(lr / (1.0 - beta1**step)) * next_avg / denominator
        blocks.append(delta.reshape(-1))
    _require(cursor == gradient.numel(), "gradient vector length drift")
    displacement = torch.cat(blocks)
    _require(torch.isfinite(displacement).all().item(), "nonfinite AdamW displacement")
    return displacement


def parameter_group(name: str) -> str:
    if "." not in name:
        return "scales"
    prefix = name.split(".", 1)[0]
    return prefix if prefix in {
        "node_encoder", "gp_encoder", "node_fusion", "local_blocks",
        "coarse_block", "node_decoder", "gp_decoder",
    } else "other"


def group_slices(named_parameters: list[tuple[str, torch.nn.Parameter]]) -> dict[str, np.ndarray]:
    indexes: dict[str, list[int]] = {}
    cursor = 0
    for name, parameter in named_parameters:
        count = parameter.numel()
        indexes.setdefault(parameter_group(name), []).extend(range(cursor, cursor + count))
        cursor += count
    return {name: np.asarray(values, dtype=np.int64) for name, values in indexes.items()}


def group_energy(vector: np.ndarray, slices: Mapping[str, np.ndarray]) -> dict[str, float]:
    _require(np.isfinite(vector).all(), "nonfinite group-energy vector")
    scale = float(np.max(np.abs(vector))) if vector.size else 0.0
    if scale == 0:
        return {name: 0.0 for name in slices}
    scaled = vector / scale
    total = float(np.dot(scaled, scaled))
    return {
        name: float(np.dot(scaled[index], scaled[index])) / total
        for name, index in slices.items()
    }


def group_dot(
    contrast: np.ndarray, change: np.ndarray, slices: Mapping[str, np.ndarray]
) -> dict[str, float]:
    _require(np.isfinite(contrast).all() and np.isfinite(change).all(), "nonfinite group-dot vector")
    values = {
        name: float(np.dot(contrast[index], change[index]))
        for name, index in slices.items()
    }
    _require(all(math.isfinite(value) for value in values.values()), "nonfinite group dot")
    return values


def normalise_fraction_map(values: Mapping[str, float]) -> dict[str, float]:
    total = float(sum(values.values()))
    _require(math.isfinite(total) and total > 0, "invalid allocation fraction total")
    return {name: float(value) / total for name, value in values.items()}


def normalised_response(contrast: torch.Tensor, change: torch.Tensor) -> float:
    contrast_norm = _stable_l2_norm(contrast)
    change_norm = _stable_l2_norm(change)
    if contrast_norm.item() == 0 or change_norm.item() == 0:
        return 0.0
    value = float(
        ((contrast / contrast_norm).dot(change / change_norm)).detach().cpu()
    )
    _require(math.isfinite(value), "nonfinite normalised response")
    return value


def margin_outcome(margin: float) -> str:
    _require(math.isfinite(margin), "nonfinite margin outcome")
    return "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"


def next_step_pair_evidence(current_margin: float, change: float) -> dict[str, Any]:
    _require(
        math.isfinite(current_margin) and math.isfinite(change),
        "nonfinite next-step pair evidence",
    )
    next_margin = current_margin + change
    return {
        "adamw_next_global_margin": next_margin,
        "adamw_next_global_outcome": margin_outcome(next_margin),
        "adamw_next_global_crossing": bool(
            current_margin > 0 and next_margin <= 0
        ),
        "adamw_next_global_repair": bool(
            current_margin < 0 and next_margin > 0
        ),
    }


def stable_numpy_norm(vector: np.ndarray) -> float:
    _require(np.isfinite(vector).all(), "nonfinite norm vector")
    scale = float(np.max(np.abs(vector))) if vector.size else 0.0
    if scale == 0:
        return 0.0
    value = scale * float(np.linalg.norm(vector / scale))
    _require(math.isfinite(value), "nonfinite derived norm")
    return value


def require_finite_payload(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for name, child in value.items():
            require_finite_payload(child, f"{path}.{name}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            require_finite_payload(child, f"{path}[{index}]")
    elif isinstance(value, (float, np.floating)):
        _require(math.isfinite(float(value)), f"nonfinite evidence: {path}")
    elif isinstance(value, np.ndarray):
        _require(np.isfinite(value).all(), f"nonfinite evidence array: {path}")


def relative_pair_contrast(
    contrast: np.ndarray, left_row: np.ndarray, right_row: np.ndarray
) -> float:
    left_norm = stable_numpy_norm(left_row)
    right_norm = stable_numpy_norm(right_row)
    row_rms = math.hypot(left_norm, right_norm) / math.sqrt(2.0)
    _require(
        math.isfinite(row_rms) and row_rms > 0,
        "undefined local-contrast normaliser",
    )
    value = stable_numpy_norm(contrast) / row_rms
    _require(math.isfinite(value), "nonfinite relative local contrast")
    return value


def collect_state(
    runtime: Any,
    checkpoint_path: Path,
    expected_arm: str,
    *,
    state_name: str,
    deadline_check: Callable[[str], None],
    progress: dict[str, Any],
) -> dict[str, Any]:
    payload = torch.load(checkpoint_path, map_location=runtime.device, weights_only=True)
    _require(payload["update"] == 500, "checkpoint update mismatch")
    _require(payload["arm"] == expected_arm, "checkpoint arm mismatch")
    runtime.model.load_state_dict(payload["model"], strict=True)
    runtime.model.eval()
    before = parameter_state_sha256(runtime.model)
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    values: dict[str, list[float]] = {"global": [], "local": []}
    gradients: dict[str, list[np.ndarray]] = {
        name: [] for name in ("global", "local", *OBJECTIVE_ORDER[:-1])
    }
    support_records: list[dict[str, float]] = []
    parameter_order: list[str] | None = None
    for index, cycle in enumerate(cycles):
        deadline_check(f"{state_name}_cycle_{cycle}_before_forward")
        progress["current_state"] = state_name
        progress["current_cycle"] = cycle
        atomic, context = atomic_losses(runtime, index)
        additions, _ = support_amplitude_losses(
            predicted_peak=context["output"]["d_peak"],
            target_peak=context["target"]["d_peak"],
            damage_pre=context["d_pre"],
            nodal_weight=context["output"]["nodal_weight"],
        )
        groups = grouped_losses(atomic)
        predicted_increment = context["output"]["d_peak"] - context["d_pre"]
        target_increment = context["target"]["d_peak"] - context["d_pre"]
        nodal_weight = context["output"]["nodal_weight"]
        global_value = (predicted_increment.abs() * nodal_weight).sum() / nodal_weight.sum()
        local_value, support = local_support_score(
            predicted_increment, target_increment, nodal_weight
        )
        objectives = OrderedDict((
            ("global", global_value),
            ("local", local_value),
            ("L_D", groups["L_D"]),
            ("L_S", additions["L_S"]),
            ("L_A", additions["L_A"]),
            ("L_U", groups["L_U"]),
            ("L_H", groups["L_H"]),
            ("L_P", groups["L_P"]),
        ))
        vectors, layout = flattened_objective_gradients(runtime.model, objectives)
        if parameter_order is None:
            parameter_order = list(layout["parameter_order"])
        _require(parameter_order == list(layout["parameter_order"]), "parameter order drift")
        values["global"].append(float(global_value.detach().cpu()))
        values["local"].append(float(local_value.detach().cpu()))
        for name in gradients:
            gradients[name].append(vectors[name].detach().cpu().numpy().copy())
        support_records.append({"cycle": cycle, **support})
        progress["cycles_completed_by_state"][state_name] = index + 1
        progress["unique_cycle_autograd_evaluations_completed"] += 1
        deadline_check(f"{state_name}_cycle_{cycle}_after_autograd")
    _require(parameter_state_sha256(runtime.model) == before, "analysis changed parameters")
    model_vector, _ = flattened_parameters(runtime.model)
    return {
        "cycles": cycles,
        "values": {name: np.asarray(rows) for name, rows in values.items()},
        "gradients": {name: np.stack(rows) for name, rows in gradients.items()},
        "support": support_records,
        "parameter_order": parameter_order,
        "model_vector": model_vector.detach().cpu().numpy().copy(),
        "optimizer": payload["optimizer"],
        "checkpoint_sha256": sha256(checkpoint_path),
        "parameter_state_sha256": before,
    }


def analyse_pairs(
    state_name: str,
    data: Mapping[str, Any],
    named_parameters: list[tuple[str, torch.nn.Parameter]],
    slices: Mapping[str, np.ndarray],
    start_outcomes: Mapping[tuple[int, int], str] | None = None,
) -> list[dict[str, Any]]:
    cycle_index = {cycle: index for index, cycle in enumerate(data["cycles"])}
    rows: list[dict[str, Any]] = []
    device = named_parameters[0][1].device
    for growth, stagnant in PAIR_ORDER:
        gi, si = cycle_index[growth], cycle_index[stagnant]
        global_margin = float(data["values"]["global"][gi] - data["values"]["global"][si])
        local_margin = float(data["values"]["local"][gi] - data["values"]["local"][si])
        global_contrast_np = data["gradients"]["global"][gi] - data["gradients"]["global"][si]
        local_contrast_np = data["gradients"]["local"][gi] - data["gradients"]["local"][si]
        relative_local_contrast = relative_pair_contrast(
            local_contrast_np,
            data["gradients"]["local"][gi],
            data["gradients"]["local"][si],
        )
        global_contrast = torch.as_tensor(global_contrast_np, device=device)
        local_contrast = torch.as_tensor(local_contrast_np, device=device)
        rank_gradient, rank_coefficient = ranking_gradient_from_margin(
            global_margin, global_contrast
        )
        pair_gradients = OrderedDict()
        for name in OBJECTIVE_ORDER[:-1]:
            pair_gradients[name] = torch.as_tensor(
                (data["gradients"][name][gi] + data["gradients"][name][si]) / 2.0,
                device=device,
            )
        pair_gradients["L_R"] = rank_gradient
        raw_rank_descent = -rank_gradient
        arm_metrics: dict[str, Any] = {}
        for arm in (ARM_CONTROL, ARM_RANK):
            preclip, q_rank, _ = preclip_merge(pair_gradients, arm)
            postclip, diagnostic = merge_ranking_gradients(pair_gradients, arm)
            independently_clipped, _ = clip_complete_direction(
                preclip, limit=GLOBAL_CLIP_NORM
            )
            _require(
                torch.equal(independently_clipped, postclip),
                "preclip/core postclip chain mismatch",
            )
            displacement = adamw_displacement_from_state_dict(
                postclip, named_parameters, data["optimizer"]
            )
            adamw_global_change = float(
                global_contrast.dot(displacement).detach().cpu()
            )
            next_step = next_step_pair_evidence(
                global_margin, adamw_global_change
            )
            arm_metrics[arm] = {
                "projected_rank_local_derivative": float(
                    local_contrast.dot(-q_rank).detach().cpu()
                ),
                "projected_rank_global_derivative": float(
                    global_contrast.dot(-q_rank).detach().cpu()
                ),
                "projected_rank_local_cosine": normalised_response(
                    local_contrast, -q_rank
                ),
                "projected_rank_global_cosine": normalised_response(
                    global_contrast, -q_rank
                ),
                "preclip_local_derivative": float(
                    local_contrast.dot(-preclip).detach().cpu()
                ),
                "preclip_global_derivative": float(
                    global_contrast.dot(-preclip).detach().cpu()
                ),
                "preclip_local_cosine": normalised_response(
                    local_contrast, -preclip
                ),
                "preclip_global_cosine": normalised_response(
                    global_contrast, -preclip
                ),
                "postclip_local_derivative": float(
                    local_contrast.dot(-postclip).detach().cpu()
                ),
                "postclip_global_derivative": float(
                    global_contrast.dot(-postclip).detach().cpu()
                ),
                "postclip_local_cosine": normalised_response(
                    local_contrast, -postclip
                ),
                "postclip_global_cosine": normalised_response(
                    global_contrast, -postclip
                ),
                "adamw_local_change": float(
                    local_contrast.dot(displacement).detach().cpu()
                ),
                "adamw_local_cosine": normalised_response(
                    local_contrast, displacement
                ),
                "adamw_global_change": adamw_global_change,
                "adamw_global_cosine": normalised_response(
                    global_contrast, displacement
                ),
                **next_step,
                "clip_applied": bool(diagnostic["clip_applied"]),
                "clip_scale": (
                    float(diagnostic["norm_after_clip"] / diagnostic["norm_before_clip"])
                    if diagnostic["norm_before_clip"] > 0 else 1.0
                ),
                "preclip_norm": float(_stable_l2_norm(preclip).detach().cpu()),
                "postclip_norm": float(_stable_l2_norm(postclip).detach().cpu()),
                "projected_rank_norm": float(_stable_l2_norm(q_rank).detach().cpu()),
                "projected_rank_group_energy": group_energy(
                    q_rank.detach().cpu().numpy(), slices
                ),
                "projected_rank_group_local_dot": group_dot(
                    local_contrast_np, (-q_rank).detach().cpu().numpy(), slices
                ),
                "projected_rank_group_global_dot": group_dot(
                    global_contrast_np, (-q_rank).detach().cpu().numpy(), slices
                ),
                "preclip_group_energy": group_energy(
                    preclip.detach().cpu().numpy(), slices
                ),
                "preclip_group_local_dot": group_dot(
                    local_contrast_np, (-preclip).detach().cpu().numpy(), slices
                ),
                "preclip_group_global_dot": group_dot(
                    global_contrast_np, (-preclip).detach().cpu().numpy(), slices
                ),
                "postclip_group_energy": group_energy(
                    postclip.detach().cpu().numpy(), slices
                ),
                "postclip_group_local_dot": group_dot(
                    local_contrast_np, (-postclip).detach().cpu().numpy(), slices
                ),
                "postclip_group_global_dot": group_dot(
                    global_contrast_np, (-postclip).detach().cpu().numpy(), slices
                ),
                "adamw_group_energy": group_energy(
                    displacement.detach().cpu().numpy(), slices
                ),
                "adamw_group_local_dot": group_dot(
                    local_contrast_np, displacement.detach().cpu().numpy(), slices
                ),
                "adamw_group_global_dot": group_dot(
                    global_contrast_np, displacement.detach().cpu().numpy(), slices
                ),
            }
        outcome = margin_outcome(global_margin)
        initial_outcome = outcome if start_outcomes is None else start_outcomes[(growth, stagnant)]
        rows.append({
            "state": state_name,
            "growth_cycle": growth,
            "stagnant_cycle": stagnant,
            "initial_outcome": initial_outcome,
            "current_global_outcome": outcome,
            "global_margin": global_margin,
            "local_margin": local_margin,
            "global_contrast_norm": stable_numpy_norm(global_contrast_np),
            "local_contrast_norm": stable_numpy_norm(local_contrast_np),
            "local_contrast_to_row_rms": relative_local_contrast,
            "local_contrast_node_decoder_energy_fraction": group_energy(
                local_contrast_np, slices
            ).get("node_decoder", 0.0),
            "rank_loss_gradient_coefficient": rank_coefficient,
            "raw_rank_norm": float(_stable_l2_norm(raw_rank_descent).detach().cpu()),
            "raw_rank_local_derivative": float(
                local_contrast.dot(raw_rank_descent).detach().cpu()
            ),
            "raw_rank_global_derivative": float(
                global_contrast.dot(raw_rank_descent).detach().cpu()
            ),
            "raw_rank_local_cosine": normalised_response(
                local_contrast, raw_rank_descent
            ),
            "raw_rank_global_cosine": normalised_response(
                global_contrast, raw_rank_descent
            ),
            "raw_rank_group_energy": group_energy(
                raw_rank_descent.detach().cpu().numpy(), slices
            ),
            "raw_rank_group_local_dot": group_dot(
                local_contrast_np, raw_rank_descent.detach().cpu().numpy(), slices
            ),
            "raw_rank_group_global_dot": group_dot(
                global_contrast_np, raw_rank_descent.detach().cpu().numpy(), slices
            ),
            "arms": arm_metrics,
        })
    return rows


def flatten_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for row in rows:
        nested_base = {
            name: value for name, value in row.items()
            if "_group_" in name
        }
        base = {
            name: value for name, value in row.items()
            if name != "arms" and name not in nested_base
        }
        for name, values in nested_base.items():
            for group, value in values.items():
                base[f"{name}_{group}"] = value
        for arm, metrics in row["arms"].items():
            nested = {
                name: value for name, value in metrics.items()
                if "_group_" in name
            }
            scalar = {name: value for name, value in metrics.items() if name not in nested}
            for name, values in nested.items():
                for group, value in values.items():
                    scalar[f"{name}_{group}"] = value
            flat.append({**base, "arm": arm, **scalar})
    return flat


def frozen_amplitudes(path: Path, arm: str, update: int = 500) -> dict[int, float]:
    rows: dict[int, float] = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["arm"] == arm and int(row["update"]) == update:
                cycle = int(row["cycle"])
                _require(cycle not in rows, f"duplicate frozen amplitude row: {arm}/{cycle}")
                value = float(row["predicted_damage_increment_abs_mean"])
                _require(math.isfinite(value), f"nonfinite frozen amplitude: {arm}/{cycle}")
                rows[cycle] = value
    _require(len(rows) == 16, f"frozen amplitude coverage drift: {arm}")
    return rows


def amplitude_replay_error(data: Mapping[str, Any], frozen: Mapping[int, float]) -> float:
    _require(set(frozen) == set(data["cycles"]), "frozen amplitude cycle-set drift")
    differences = []
    for cycle, value in zip(data["cycles"], data["values"]["global"]):
        observed = float(value)
        _require(math.isfinite(observed), f"nonfinite replayed amplitude: {cycle}")
        difference = abs(observed - frozen[cycle])
        _require(math.isfinite(difference), f"nonfinite amplitude replay difference: {cycle}")
        differences.append(difference)
    return max(differences)


def observed_changes(
    start: Mapping[str, Any], endpoint: Mapping[str, Any], arm: str
) -> list[dict[str, Any]]:
    cycle_index = {cycle: index for index, cycle in enumerate(start["cycles"])}
    displacement = endpoint["model_vector"] - start["model_vector"]
    rows = []
    for growth, stagnant in PAIR_ORDER:
        gi, si = cycle_index[growth], cycle_index[stagnant]
        start_global = float(start["values"]["global"][gi] - start["values"]["global"][si])
        start_local = float(start["values"]["local"][gi] - start["values"]["local"][si])
        end_global = float(endpoint["values"]["global"][gi] - endpoint["values"]["global"][si])
        end_local = float(endpoint["values"]["local"][gi] - endpoint["values"]["local"][si])
        global_contrast = start["gradients"]["global"][gi] - start["gradients"]["global"][si]
        local_contrast = start["gradients"]["local"][gi] - start["gradients"]["local"][si]
        linearised_global_change = float(np.dot(global_contrast, displacement))
        linearised_local_change = float(np.dot(local_contrast, displacement))
        linearised_global_margin = start_global + linearised_global_change
        rows.append({
            "arm": arm,
            "growth_cycle": growth,
            "stagnant_cycle": stagnant,
            "initial_outcome": "WIN" if start_global > 0 else "LOSS" if start_global < 0 else "TIE",
            "global_margin_change": end_global - start_global,
            "local_margin_change": end_local - start_local,
            "linearised_global_change_along_finite_displacement": linearised_global_change,
            "linearised_local_change_along_finite_displacement": linearised_local_change,
            "linearised_global_margin": linearised_global_margin,
            "linearised_finite_displacement_global_crossing": bool(
                start_global > 0 and linearised_global_margin <= 0
            ),
            "endpoint_global_outcome": margin_outcome(end_global),
            "endpoint_local_margin": end_local,
        })
    return rows


def choose_route(state_rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_state: dict[str, Any] = {}
    for state in STATE_ORDER:
        rows = [row for row in state_rows if row["state"] == state]
        wrong = [row for row in rows if row["initial_outcome"] == "LOSS"]
        _require(len(wrong) == 8 and len(rows) == 25, "frozen pair accounting drift")
        usable_wrong = sum(
            row["local_contrast_to_row_rms"] >= USABLE_RELATIVE_CONTRAST
            for row in wrong
        )
        raw_helpful = sum(
            row["raw_rank_local_cosine"] >= HELPFUL_COSINE for row in wrong
        )
        projected_helpful = sum(
            row["arms"][ARM_RANK]["projected_rank_local_cosine"] >= HELPFUL_COSINE
            for row in wrong
        )
        merged_helpful = sum(
            row["arms"][ARM_RANK]["postclip_local_cosine"] >= HELPFUL_COSINE
            for row in wrong
        )
        adamw_helpful = sum(
            row["arms"][ARM_RANK]["adamw_local_cosine"] >= HELPFUL_COSINE
            for row in wrong
        )
        labels: list[str] = []
        reasons: dict[str, str] = {}
        if usable_wrong == 8 and raw_helpful < 8:
            labels.append("RAW_OBSERVABLE_MISMATCH")
            reasons["RAW_OBSERVABLE_MISMATCH"] = (
                f"usable wrong pairs 8/8; raw helpful {raw_helpful}/8"
            )
        lost_stages = [
            name for name, count in (
                ("projected_rank", projected_helpful),
                ("complete_postclip_merge", merged_helpful),
                ("saved_state_adamw", adamw_helpful),
            ) if count < 8
        ]
        if usable_wrong == 8 and raw_helpful == 8 and lost_stages:
            labels.append("DOWNSTREAM_DIRECTION_LOSS")
            reasons["DOWNSTREAM_DIRECTION_LOSS"] = (
                "first lost stage: " + lost_stages[0]
            )
        negligible_all = all(
            row["local_contrast_to_row_rms"] < USABLE_RELATIVE_CONTRAST
            for row in rows
        )
        decoder_weak_all = all(
            row["local_contrast_node_decoder_energy_fraction"]
            < NODE_DECODER_ENERGY_LIMIT for row in rows
        )
        if negligible_all and decoder_weak_all:
            labels.append("WEAK_LOCAL_PARAMETERISATION")
            reasons["WEAK_LOCAL_PARAMETERISATION"] = (
                "all 25 contrasts negligible and node-decoder allocation below limit"
            )
        per_state[state] = {
            "mechanism_labels": labels,
            "reasons": reasons,
            "usable_wrong_pair_count": usable_wrong,
            "raw_rank_locally_helpful_count": raw_helpful,
            "projected_rank_locally_helpful_count": projected_helpful,
            "merged_rank_locally_helpful_count": merged_helpful,
            "adamw_rank_locally_helpful_count": adamw_helpful,
        }
    action_candidates: list[str] = []
    if "DOWNSTREAM_DIRECTION_LOSS" in per_state[STATE_ORDER[0]]["mechanism_labels"]:
        action_candidates.append("MERGER_OR_PRECONDITIONER_REPAIR_PROBE")
    mismatch_states = sum(
        "RAW_OBSERVABLE_MISMATCH" in per_state[state]["mechanism_labels"]
        for state in STATE_ORDER
    )
    if (
        "RAW_OBSERVABLE_MISMATCH" in per_state[STATE_ORDER[0]]["mechanism_labels"]
        or mismatch_states >= 2
    ):
        action_candidates.append("LOCALISATION_AWARE_OBJECTIVE_PROBE")
    if all(
        "WEAK_LOCAL_PARAMETERISATION" in per_state[state]["mechanism_labels"]
        for state in STATE_ORDER
    ):
        action_candidates.append("FACTORIZED_HEAD_PROBE")
    priority = (
        "MERGER_OR_PRECONDITIONER_REPAIR_PROBE",
        "LOCALISATION_AWARE_OBJECTIVE_PROBE",
        "FACTORIZED_HEAD_PROBE",
    )
    selected_action = next(
        (candidate for candidate in priority if candidate in action_candidates),
        "NO_ACTIONABLE_SIGNAL",
    )
    return {
        "route": selected_action,
        "selected_action": selected_action,
        "action_candidates": action_candidates,
        "selection_basis": (
            "fixed minimum-change and discriminability priority; not an exclusive causal verdict"
        ),
        "thresholds": {
            "usable_relative_contrast_ge": USABLE_RELATIVE_CONTRAST,
            "locally_helpful_cosine_ge": HELPFUL_COSINE,
            "node_decoder_energy_fraction_lt": NODE_DECODER_ENERGY_LIMIT,
        },
        "per_state": per_state,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _require(bool(rows), "cannot write empty CSV")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_decision(
    output: Path,
    state_rows: list[dict[str, Any]],
    observed: list[dict[str, Any]],
    allocation: Mapping[str, Mapping[str, float]],
    route: Mapping[str, Any],
) -> None:
    colors = {STATE_ORDER[0]: "#4C78A8", STATE_ORDER[1]: "#59A14F", STATE_ORDER[2]: "#E15759"}
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.0), constrained_layout=True)
    ax = axes[0, 0]
    for state in STATE_ORDER:
        subset = [row for row in state_rows if row["state"] == state]
        ax.scatter(
            [row["global_margin"] for row in subset],
            [row["local_margin"] for row in subset],
            label=state, s=34, alpha=0.8, color=colors[state],
        )
    ax.axhline(0, color="black", lw=0.7); ax.axvline(0, color="black", lw=0.7)
    ax.set_xlabel("global amplitude margin"); ax.set_ylabel("local-minus-background margin")
    ax.set_title("A. Frozen pair margins"); ax.legend(fontsize=8)

    ax = axes[0, 1]
    wrong = [row for row in state_rows if row["state"] == STATE_ORDER[0] and row["initial_outcome"] == "LOSS"]
    labels = [f"{r['growth_cycle']}>{r['stagnant_cycle']}" for r in wrong]
    stages = {
        "raw -gR": [r["raw_rank_local_derivative"] for r in wrong],
        "projected -qR": [r["arms"][ARM_RANK]["projected_rank_local_derivative"] for r in wrong],
        "merged/clipped": [r["arms"][ARM_RANK]["postclip_local_derivative"] for r in wrong],
        "AdamW delta": [r["arms"][ARM_RANK]["adamw_local_change"] for r in wrong],
    }
    matrix = np.asarray(list(stages.values()))
    scale = np.maximum(np.max(np.abs(matrix), axis=1, keepdims=True), np.finfo(float).tiny)
    image = ax.imshow(matrix / scale, aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=55, ha="right", fontsize=8)
    ax.set_yticks(range(len(stages)), list(stages), fontsize=8)
    ax.set_title("B. Wrong-pair local effect by stage\n(each row scaled by its own max |value|)")
    fig.colorbar(image, ax=ax, shrink=0.8, label="signed row-normalised effect")

    ax = axes[1, 0]
    for arm, marker, color in ((ARM_CONTROL, "o", "#59A14F"), (ARM_RANK, "^", "#E15759")):
        subset = [row for row in observed if row["arm"] == arm]
        edge = ["#B22222" if row["initial_outcome"] == "LOSS" else "white" for row in subset]
        ax.scatter(
            [row["global_margin_change"] for row in subset],
            [row["local_margin_change"] for row in subset],
            marker=marker, color=color, edgecolor=edge, linewidth=1.0, label=arm, alpha=0.85,
        )
    ax.axhline(0, color="black", lw=0.7); ax.axvline(0, color="black", lw=0.7)
    ax.set_xlabel("realised global-margin change"); ax.set_ylabel("realised local-margin change")
    ax.set_title("C. Finite S0→endpoint changes (red edge = original loss)")
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    groups = list(next(iter(allocation.values())))
    x = np.arange(len(allocation)); bottom = np.zeros(len(allocation))
    palette = plt.get_cmap("tab10")
    for index, group in enumerate(groups):
        values = [allocation[name].get(group, 0.0) for name in allocation]
        ax.bar(x, values, bottom=bottom, label=group, color=palette(index % 10))
        bottom += np.asarray(values)
    ax.set_xticks(x, list(allocation), rotation=30, ha="right", fontsize=8)
    ax.set_ylim(0, 1); ax.set_ylabel("squared-norm fraction")
    ax.set_title("D. Parameter-group allocation")
    ax.legend(fontsize=7, ncol=2)
    fig.suptitle(f"S09-E012 local-support diagnostic — route: {route['route']}", fontsize=14)
    fig.savefig(output / "decision_figure.png", dpi=220, facecolor="white")
    fig.savefig(output / "decision_figure.pdf", facecolor="white")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--resolved-config", type=Path, required=True)
    parser.add_argument("--start-checkpoint", type=Path, required=True)
    parser.add_argument("--control-checkpoint", type=Path, required=True)
    parser.add_argument("--ranking-checkpoint", type=Path, required=True)
    parser.add_argument("--e010-per-cycle-csv", type=Path, required=True)
    parser.add_argument("--e011-per-cycle-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--wall-seconds", type=float, default=900.0)
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    started = time.monotonic()
    args._failure_stage = "initialising"
    args._states_completed = []
    args._progress = {
        "current_state": None,
        "current_cycle": None,
        "cycles_completed_by_state": {state: 0 for state in STATE_ORDER},
        "unique_cycle_autograd_evaluations_completed": 0,
    }
    def require_deadline(stage: str) -> None:
        _require(
            time.monotonic() - started <= args.wall_seconds,
            f"wall-time cap reached at {stage}",
        )

    _require(
        math.isfinite(args.wall_seconds) and 0 < args.wall_seconds <= 900.0,
        "wall-time limit must be finite, positive, and at most 900 seconds",
    )
    _require(args.device == "cuda:0", "producer diagnostic requires cuda:0")
    _require(torch.cuda.is_available(), "producer diagnostic requires CUDA")
    _require(torch.cuda.device_count() == 1, "exactly one visible GPU is required")
    _require(socket.gethostname() == "GPUServer8", "producer host identity mismatch")
    _require(not args.output_dir.exists(), "output directory must be fresh")
    input_paths = {
        "start_checkpoint": args.start_checkpoint,
        "control_checkpoint": args.control_checkpoint,
        "ranking_checkpoint": args.ranking_checkpoint,
        "e010_per_cycle_csv": args.e010_per_cycle_csv,
        "e011_per_cycle_csv": args.e011_per_cycle_csv,
        "base_config": args.base_config,
        "resolved_config": args.resolved_config,
    }
    for name, path in input_paths.items():
        _require(path.is_file(), f"missing frozen input: {name}")
        _require(sha256(path) == EXPECTED_INPUT_SHA256[name], f"input identity drift: {name}")
    args.output_dir.mkdir(parents=True)
    config = json.loads(args.base_config.read_text())
    resolved_config = json.loads(args.resolved_config.read_text())
    _require(
        resolved_config.get("planned_run_id")
        == "S09-E010-R001-support-amplitude-three-arm",
        "resolved E010 config identity drift",
    )
    torch.manual_seed(int(config["model"]["seed"]))
    device = torch.device(args.device)
    runtime = build_runtime(
        packet_dir=args.packet_dir,
        config_path=args.base_config,
        device=device,
        executable=False,
    )
    _require(
        runtime.packet_identity["manifest_sha256"] == EXPECTED_PACKET_MANIFEST_SHA256,
        "packet identity drift",
    )
    checkpoints = OrderedDict((
        (STATE_ORDER[0], (args.start_checkpoint, "B25_support_amplitude_beta0p25")),
        (STATE_ORDER[1], (args.control_checkpoint, ARM_CONTROL)),
        (STATE_ORDER[2], (args.ranking_checkpoint, ARM_RANK)),
    ))
    states: dict[str, Any] = {}
    for name, (path, arm) in checkpoints.items():
        args._failure_stage = f"{name}_collection"
        require_deadline(f"{name}_before_collection")
        states[name] = collect_state(
            runtime,
            path,
            arm,
            state_name=name,
            deadline_check=require_deadline,
            progress=args._progress,
        )
        args._states_completed.append(name)
        require_deadline(f"{name}_after_collection")
    frozen_by_state = {
        STATE_ORDER[0]: frozen_amplitudes(
            args.e010_per_cycle_csv, "B25_support_amplitude_beta0p25"
        ),
        STATE_ORDER[1]: frozen_amplitudes(args.e011_per_cycle_csv, ARM_CONTROL),
        STATE_ORDER[2]: frozen_amplitudes(args.e011_per_cycle_csv, ARM_RANK),
    }
    replay_errors = {
        state: amplitude_replay_error(states[state], frozen_by_state[state])
        for state in STATE_ORDER
    }
    _require(max(replay_errors.values()) <= 1.0e-12, "frozen amplitude replay mismatch")
    named_parameters = list(runtime.model.named_parameters())
    _require(
        [name for name, _ in named_parameters] == states[STATE_ORDER[0]]["parameter_order"],
        "named parameter order drift",
    )
    slices = group_slices(named_parameters)
    start_outcomes: dict[tuple[int, int], str] = {}
    start_index = {cycle: index for index, cycle in enumerate(states[STATE_ORDER[0]]["cycles"])}
    for growth, stagnant in PAIR_ORDER:
        margin = (
            states[STATE_ORDER[0]]["values"]["global"][start_index[growth]]
            - states[STATE_ORDER[0]]["values"]["global"][start_index[stagnant]]
        )
        start_outcomes[(growth, stagnant)] = "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"
    state_rows: list[dict[str, Any]] = []
    for state_name in STATE_ORDER:
        args._failure_stage = f"{state_name}_pair_algebra"
        require_deadline(f"{state_name}_before_pair_algebra")
        state_rows.extend(
            analyse_pairs(
                state_name, states[state_name], named_parameters, slices, start_outcomes
            )
        )
        require_deadline(f"{state_name}_after_pair_algebra")
    require_finite_payload(state_rows, "state_rows")
    observed = observed_changes(states[STATE_ORDER[0]], states[STATE_ORDER[1]], ARM_CONTROL)
    observed += observed_changes(states[STATE_ORDER[0]], states[STATE_ORDER[2]], ARM_RANK)
    require_finite_payload(observed, "observed_endpoint_changes")
    route = choose_route(state_rows)
    start_local_contrasts = []
    for growth, stagnant in PAIR_ORDER:
        gi, si = start_index[growth], start_index[stagnant]
        start_local_contrasts.append(
            states[STATE_ORDER[0]]["gradients"]["local"][gi]
            - states[STATE_ORDER[0]]["gradients"]["local"][si]
        )
    mean_local_allocation = normalise_fraction_map({
        group: float(np.mean([
            group_energy(vector, slices)[group]
            for vector in start_local_contrasts
        ]))
        for group in slices
    })
    allocation: dict[str, dict[str, float]] = {
        "mean local Jdiff": mean_local_allocation,
        "control displacement": group_energy(
            states[STATE_ORDER[1]]["model_vector"] - states[STATE_ORDER[0]]["model_vector"], slices
        ),
        "ranking displacement": group_energy(
            states[STATE_ORDER[2]]["model_vector"] - states[STATE_ORDER[0]]["model_vector"], slices
        ),
    }
    flat = flatten_rows(state_rows)
    write_csv(args.output_dir / "pair_direction_decomposition.csv", flat)
    write_csv(args.output_dir / "observed_endpoint_changes.csv", observed)
    write_csv(
        args.output_dir / "support_definition.csv",
        [dict(state=state, **row) for state in STATE_ORDER for row in states[state]["support"]],
    )
    require_deadline("before_figure")
    args._failure_stage = "decision_figure"
    plot_decision(args.output_dir, state_rows, observed, allocation, route)
    require_deadline("after_figure")
    correct = [row for row in observed if row["initial_outcome"] == "WIN"]
    wrong = [row for row in observed if row["initial_outcome"] == "LOSS"]
    pair_accounting = {
        "original_wrong_pairs": 8,
        "original_correct_pairs": 17,
        "control_wrong_pairs_repaired": sum(
            row["endpoint_global_outcome"] == "WIN" for row in wrong if row["arm"] == ARM_CONTROL
        ),
        "control_correct_pairs_lost": sum(
            row["endpoint_global_outcome"] != "WIN" for row in correct if row["arm"] == ARM_CONTROL
        ),
        "ranking_wrong_pairs_repaired": sum(
            row["endpoint_global_outcome"] == "WIN" for row in wrong if row["arm"] == ARM_RANK
        ),
        "ranking_correct_pairs_lost": sum(
            row["endpoint_global_outcome"] != "WIN" for row in correct if row["arm"] == ARM_RANK
        ),
        "control_correct_pairs_finite_displacement_crossings": sum(
            row["linearised_finite_displacement_global_crossing"]
            for row in correct if row["arm"] == ARM_CONTROL
        ),
        "ranking_correct_pairs_finite_displacement_crossings": sum(
            row["linearised_finite_displacement_global_crossing"]
            for row in correct if row["arm"] == ARM_RANK
        ),
    }
    _require(
        {name: pair_accounting[name] for name in (
            "original_wrong_pairs", "original_correct_pairs",
            "control_wrong_pairs_repaired", "control_correct_pairs_lost",
            "ranking_wrong_pairs_repaired", "ranking_correct_pairs_lost",
        )} == {
            "original_wrong_pairs": 8,
            "original_correct_pairs": 17,
            "control_wrong_pairs_repaired": 8,
            "control_correct_pairs_lost": 5,
            "ranking_wrong_pairs_repaired": 0,
            "ranking_correct_pairs_lost": 0,
        },
        "frozen realised-pair accounting drift",
    )
    sign_accounting = {}
    for arm in (ARM_CONTROL, ARM_RANK):
        arm_rows = [row for row in observed if row["arm"] == arm]
        sign_accounting[arm] = {
            initial: {
                endpoint: sum(
                    row["initial_outcome"] == initial
                    and row["endpoint_global_outcome"] == endpoint
                    for row in arm_rows
                )
                for endpoint in ("WIN", "TIE", "LOSS")
            }
            for initial in ("WIN", "TIE", "LOSS")
        }
    next_adamw_accounting: dict[str, Any] = {}
    for state in STATE_ORDER:
        next_adamw_accounting[state] = {}
        state_subset = [row for row in state_rows if row["state"] == state]
        for arm in (ARM_CONTROL, ARM_RANK):
            next_adamw_accounting[state][arm] = {
                "original_wrong_pairs": sum(
                    row["initial_outcome"] == "LOSS" for row in state_subset
                ),
                "original_correct_pairs": sum(
                    row["initial_outcome"] == "WIN" for row in state_subset
                ),
                "current_wrong_pairs": sum(
                    row["current_global_outcome"] != "WIN"
                    for row in state_subset
                    if row["initial_outcome"] == "LOSS"
                ),
                "current_correct_pairs_already_lost": sum(
                    row["current_global_outcome"] != "WIN"
                    for row in state_subset
                    if row["initial_outcome"] == "WIN"
                ),
                "next_adamw_wrong_pair_repairs": sum(
                    row["arms"][arm]["adamw_next_global_repair"]
                    for row in state_subset
                    if row["initial_outcome"] == "LOSS"
                ),
                "next_adamw_correct_pair_crossings": sum(
                    row["arms"][arm]["adamw_next_global_crossing"]
                    for row in state_subset
                    if row["initial_outcome"] == "WIN"
                ),
                "next_outcome_counts": {
                    outcome: sum(
                        row["arms"][arm]["adamw_next_global_outcome"] == outcome
                        for row in state_subset
                    )
                    for outcome in ("WIN", "TIE", "LOSS")
                },
            }
    require_finite_payload(pair_accounting, "pair_accounting")
    require_finite_payload(sign_accounting, "sign_accounting")
    require_finite_payload(next_adamw_accounting, "next_adamw_accounting")
    for name, path in input_paths.items():
        _require(
            sha256(path) == EXPECTED_INPUT_SHA256[name],
            f"input identity changed during analysis: {name}",
        )
    _require(
        runtime.packet_identity["manifest_sha256"] == EXPECTED_PACKET_MANIFEST_SHA256,
        "packet identity changed during analysis",
    )
    readme = f"""# S09-E012 analysis

This is a read-only diagnostic on three frozen exposed-development states.  It
performed no optimiser step, FEM solve, or fresh-holdout access.

Selected exploratory action: `{route['selected_action']}`.

The selection follows a frozen minimum-change priority.  It is not an exclusive
causal verdict; all per-state mechanism labels and all matched action candidates
remain in `completion_receipt.json`.

The local observable uses the frozen target-derived mask
`true damage increment > 1e-15`.  It is a diagnostic oracle mask and cannot be
used as an inference or deployment input.  The finite-displacement linearised
responses and exact endpoint observable changes are separate columns in
`observed_endpoint_changes.csv`.

The original 8 wrong and 17 correct pairs are retained.  Control repair and
protection loss are reported together; no subset was selected after inspection.
"""
    (args.output_dir / "README_analysis.md").write_text(readme)
    receipt = {
        "schema_version": "s09-e012-local-support-sensitivity-v1",
        "run_id": RUN_ID,
        "status": "COMPLETED",
        "route": route,
        "support": {
            "definition": "target_damage_increment > 1e-15",
            "role": "exposed-development diagnostic oracle; not a deployable input",
            "threshold": SUPPORT_THRESHOLD,
        },
        "execution": {
            "unique_cycle_autograd_evaluations": 3 * len(states[STATE_ORDER[0]]["cycles"]),
            "pairwise_autograd_evaluations": 0,
            "optimizer_constructed": False,
            "optimizer_steps_performed": 0,
            "fresh_holdout_accessed": False,
            "elapsed_seconds": time.monotonic() - started,
            "wall_seconds_limit": args.wall_seconds,
            "device": str(device),
            "hostname": socket.gethostname(),
            "device_name": (
                torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu"
            ),
        },
        "analysis_script": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "inputs": {
            "base_config": {
                "path": str(args.base_config),
                "sha256": sha256(args.base_config),
                "role": "executable P1 architecture, data, and normaliser contract",
            },
            "resolved_config": {
                "path": str(args.resolved_config),
                "sha256": sha256(args.resolved_config),
                "role": "frozen E010 arm and execution provenance",
            },
            "packet_manifest_sha256": runtime.packet_identity["manifest_sha256"],
        },
        "checkpoints": {
            state: {
                "path": str(checkpoints[state][0]),
                "sha256": states[state]["checkpoint_sha256"],
                "parameter_state_sha256": states[state]["parameter_state_sha256"],
            } for state in STATE_ORDER
        },
        "frozen_amplitude_replay": {
            "maximum_absolute_error_by_state": replay_errors,
            "tolerance": 1.0e-12,
            "e010_csv": {"path": str(args.e010_per_cycle_csv), "sha256": sha256(args.e010_per_cycle_csv)},
            "e011_csv": {"path": str(args.e011_per_cycle_csv), "sha256": sha256(args.e011_per_cycle_csv)},
        },
        "pair_accounting": pair_accounting,
        "endpoint_sign_accounting": sign_accounting,
        "next_adamw_pair_accounting": next_adamw_accounting,
        "parameter_group_allocation": allocation,
        "artifacts": {},
    }
    for name in (
        "pair_direction_decomposition.csv", "observed_endpoint_changes.csv",
        "support_definition.csv", "decision_figure.png", "decision_figure.pdf",
        "README_analysis.md",
    ):
        receipt["artifacts"][name] = {"sha256": sha256(args.output_dir / name)}
    require_deadline("before_completion_receipt")
    args._failure_stage = "completion_receipt"
    (args.output_dir / "completion_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(json.dumps({"status": "COMPLETED", "route": route, "output": str(args.output_dir)}))


def main() -> None:
    args = parse_args()
    try:
        run(args)
    except Exception as exc:
        failure_path = args.output_dir.parent / f"{args.output_dir.name}.failure.json"
        failure = {
            "schema_version": "s09-e012-local-support-sensitivity-failure-v1",
            "run_id": RUN_ID,
            "status": "FAILED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_stage": getattr(args, "_failure_stage", "argument_or_preflight"),
            "states_completed": getattr(args, "_states_completed", []),
            "progress": getattr(args, "_progress", {}),
            "completed_unique_cycle_autograd_evaluations": getattr(
                args, "_progress", {}
            ).get("unique_cycle_autograd_evaluations_completed", 0),
            "optimizer_constructed": False,
            "optimizer_steps_performed": 0,
            "fresh_holdout_accessed": False,
            "retry_authorised": False,
        }
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        with failure_path.open("x") as stream:
            stream.write(json.dumps(failure, indent=2, sort_keys=True) + "\n")
        raise


if __name__ == "__main__":
    main()
