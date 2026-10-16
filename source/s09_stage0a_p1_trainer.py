"""Bounded P1 memorisation runner for the reviewed S09-E008 package."""
from __future__ import annotations

from dataclasses import dataclass
import copy
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
import time
from typing import Any

import numpy as np
import torch

from s09_equilibrium_operator import affine_displacement, build_graph, graph_to_torch
from s09_fem_physics import boundary, equilibrium
from s09_multiobjective_update import merge_objective_gradients
from s09_q4_quadrature import q4_shape_data
from s09_stage0a_p1_packet import canonical_json, load_verified_packet, sha256_file
from s09_stage0a_transition import (
    Stage0ATransitionOperator,
    carrara_f,
    fixed_judgement_loss,
    raw_increment_objectives,
    stage0a_objectives,
)

OBJECTIVE_ORDER = ("nodal_state_plus_raw_nodal_increment",
                   "gp_history_plus_raw_gp_increment", "peak_equilibrium")
DIAGNOSTIC_STEPS = (0, 1, 10, 50, 100, 250, 500, 750, 1000)


def _require(condition: bool, message: str, error=ValueError) -> None:
    if not condition:
        raise error(message)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _finite_scalar(value: torch.Tensor, name: str) -> None:
    _require(value.ndim == 0 and torch.isfinite(value), f"nonfinite/non-scalar {name}", FloatingPointError)


def current_commit(root: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


@dataclass
class Runtime:
    arrays: dict[str, np.ndarray]
    metadata: dict[str, Any]
    packet_identity: dict[str, Any]
    config: dict[str, Any]
    graph: dict[str, torch.Tensor]
    conn: torch.Tensor
    shape: torch.Tensor
    dshape: torch.Tensor
    det: torch.Tensor
    model: Stage0ATransitionOperator
    scales: dict[str, torch.Tensor]
    equilibrium_scale: float
    device: torch.device


def resolve_execution_config(*, packet_dir: Path, base_config_path: Path,
                             output_path: Path, repo_root: Path,
                             authorize_execution: bool) -> dict[str, Any]:
    """Resolve producer identities before training; never starts an optimiser."""
    _require(sys.platform.startswith("linux"), "config resolution is producer-only", PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required for producer resolution", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible, "exactly one CUDA_VISIBLE_DEVICES entry is required")
    _require(not output_path.exists(), "resolved config output already exists")
    arrays, metadata, packet_identity = load_verified_packet(packet_dir)
    config = _json(base_config_path)
    _validate_reviewed_config(config, metadata, packet_identity, executable=False)
    _require(arrays["d_pre"].shape == (16, config["data"]["native_nodes"]),
             "packet nodal support differs from config")
    _require(arrays["history_pre"].shape ==
             (16, config["data"]["native_q4_elements"],
              config["data"]["gauss_points_per_element"], 4),
             "packet GP support differs from config")
    _require(np.array_equal(arrays["cycles"], np.asarray(config["data"]["selected_cycles"], dtype=np.int64)),
             "packet cycle values/order differ from config")
    _require(np.array_equal(arrays["path"], np.asarray(config["data"]["prescribed_path"], dtype=np.float64)),
             "packet prescribed path differs from config")
    device = torch.device("cuda:0")
    _verify_packet_states_before_model(arrays, config, device=device)
    _verify_static_geometry(arrays, device=device)
    equilibrium_scale = compute_equilibrium_normaliser(arrays, device=device)

    resolved = copy.deepcopy(config)
    resolved["status"] = "RESOLVED_FOR_FINAL_EXECUTION_GATE"
    resolved["execution_authorized"] = bool(authorize_execution)
    resolved["source"]["training_commit"] = current_commit(repo_root)
    resolved["source"]["input_packet_sha256"] = packet_identity["manifest_sha256"]
    resolved["producer"]["gpu_id"] = visible
    resolved["normalisers"]["equilibrium"] = equilibrium_scale

    # This construction occurs only after the equilibrium scale is frozen.
    model = Stage0ATransitionOperator(
        resolved["normalisers"]["damage_increment"],
        resolved["normalisers"]["history_increment"][:3],
        resolved["normalisers"]["displacement"],
        width=resolved["model"]["width"], rank=resolved["model"]["rank"],
    ).to(device=device, dtype=torch.float64)
    resolved["optimisation"]["gradient_vector_contract"]["resolved_parameter_order"] = [
        name for name, _ in model.named_parameters()
    ]
    resolved["resolution_receipt"] = {
        "base_config_sha256": sha256_file(base_config_path),
        "packet_manifest_sha256": packet_identity["manifest_sha256"],
        "training_commit": resolved["source"]["training_commit"],
        "CUDA_VISIBLE_DEVICES": visible,
        "equilibrium_frozen_before_model_construction": True,
        "optimizer_or_training_step_performed": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as stream:
        stream.write(canonical_json(resolved))
    return resolved


def _validate_reviewed_config(config: dict[str, Any], metadata: dict[str, Any],
                              packet_identity: dict[str, Any], *, executable: bool) -> None:
    _require(config["schema_version"] == "s09-e008-p1-run-package-v2", "config schema drift")
    _require(config["planned_run_id"] == "S09-E008-P1-R001-stage0a-memorisation", "run identity drift")
    _require(config["data"]["selected_cycles"] == metadata["selected_cycles"], "packet/config cycle drift")
    _require(config["data"]["history_order"] == metadata["history_order"], "packet/config channel drift")
    _require(config["optimisation"]["objectives_in_fixed_order"] == list(OBJECTIVE_ORDER), "objective order drift")
    _require(config["optimisation"]["updates"] == 1000 and config["data"]["batch_size"] == 1,
             "budget drift")
    _require(config["model"]["dtype"] == "float64" and config["model"]["seed"] == 20261016,
             "dtype/seed drift")
    _require(config["source"]["static_sha256"] == metadata["source_static_sha256"], "static drift")
    _require(config["source"]["capability_receipt_sha256"] == metadata["source_capability_receipt_sha256"],
             "capability receipt drift")
    packet_sha = config["source"]["input_packet_sha256"]
    if executable:
        _require(config["execution_authorized"] is True, "execution is not authorised", PermissionError)
        _require(packet_sha == packet_identity["manifest_sha256"], "resolved packet identity mismatch")
        for field in ("training_commit", "input_packet_sha256"):
            _require("TO_BE_" not in str(config["source"][field]), f"unresolved source field: {field}")
        _require(isinstance(config["normalisers"]["equilibrium"], (int, float)),
                 "equilibrium normaliser is unresolved")
        _require("TO_BE_" not in str(config["producer"]["gpu_id"]), "GPU ID is unresolved")
    else:
        _require(config["execution_authorized"] is False, "no-training build requires unresolved config")


def _verify_static_geometry(arrays: dict[str, np.ndarray], *, device: torch.device):
    xy = torch.as_tensor(arrays["xy"], dtype=torch.float64, device=device)
    conn = torch.as_tensor(arrays["conn"], dtype=torch.long, device=device)
    shape, dshape, det = q4_shape_data(xy, conn)
    torch.testing.assert_close(shape, torch.as_tensor(arrays["shape"], device=device), rtol=0, atol=1e-14)
    g = 1.0 / math.sqrt(3.0)
    reference = []
    for xi, eta in ((g, g), (-g, g), (g, -g), (-g, -g)):
        reference.append([
            [-.25 * (1 - eta), .25 * (1 - eta), .25 * (1 + eta), -.25 * (1 + eta)],
            [-.25 * (1 - xi), -.25 * (1 + xi), .25 * (1 + xi), .25 * (1 - xi)],
        ])
    torch.testing.assert_close(
        torch.as_tensor(arrays["reference_derivative"], device=device),
        xy.new_tensor(reference), rtol=0, atol=1e-14,
    )
    gp = torch.as_tensor(arrays["gp_weight"], dtype=torch.float64, device=device)
    gauss_weight = torch.as_tensor(arrays["gauss_weight"], dtype=torch.float64, device=device)
    thickness = float(arrays["thickness"][0])
    _require(np.isfinite(thickness) and thickness > 0, "invalid inferred thickness")
    _require(torch.isfinite(gauss_weight).all() and torch.all(gauss_weight > 0),
             "invalid Gauss weights")
    _require(thickness == 1.0 and torch.equal(gauss_weight, torch.ones_like(gauss_weight)),
             "current reviewed equilibrium implementation requires unit thickness/Gauss weights")
    torch.testing.assert_close(gp, det * gauss_weight[None] * thickness,
                               rtol=1e-12, atol=1e-14)
    nodal = det.new_zeros(len(xy))
    local = torch.einsum("gn,eg->en", shape, gp)
    nodal.index_add_(0, conn.reshape(-1), local.reshape(-1))
    torch.testing.assert_close(nodal, torch.as_tensor(arrays["nodal_weight"], device=device), rtol=1e-12, atol=1e-14)
    return xy, conn, shape, dshape, det


def compute_equilibrium_normaliser(arrays: dict[str, np.ndarray], *, device: torch.device) -> float:
    """Mean teacher-damage affine-BC free-DOF force MSE."""
    xy, conn, shape, dshape, det = _verify_static_geometry(arrays, device=device)
    affine = affine_displacement(xy, float(arrays["path"][4]))
    free = boundary(xy)
    values = []
    for damage in arrays["d_peak"]:
        d = torch.as_tensor(damage, dtype=torch.float64, device=device)
        force, _ = equilibrium(affine, d, conn, shape, dshape, det,
                               young=1.0, nu=0.3, eta=0.0)
        values.append(force[free].square().mean())
    result = torch.stack(values).mean()
    _finite_scalar(result, "equilibrium normaliser")
    value = float(result.detach().cpu())
    _require(value > 0, "equilibrium normaliser must be positive")
    return value


def _verify_packet_states_before_model(arrays: dict[str, np.ndarray],
                                       config: dict[str, Any], *, device: torch.device) -> None:
    """Recheck teacher state semantics before constructing any model parameters."""
    d_pre = torch.as_tensor(arrays["d_pre"], dtype=torch.float64, device=device)
    d_peak = torch.as_tensor(arrays["d_peak"], dtype=torch.float64, device=device)
    h_pre = torch.as_tensor(arrays["history_pre"], dtype=torch.float64, device=device)
    h_peak = torch.as_tensor(arrays["history_peak"], dtype=torch.float64, device=device)
    _require(torch.all((d_pre >= 0) & (d_pre <= 1)) and
             torch.all((d_peak >= d_pre) & (d_peak <= 1)),
             "teacher damage bounds/irreversibility failure")
    _require(torch.all(h_peak[..., 1] >= h_pre[..., 1]),
             "teacher alpha irreversibility failure")
    contract = config["model"]["hard_constraint_contract"]
    for label, history in (("pre", h_pre), ("peak", h_peak)):
        expected = carrara_f(history[..., 1])
        tolerance = contract["prestate_f_consistency"] if label == "pre" else contract["derived_f_identity"]
        _require(torch.all(torch.abs(history[..., 3] - expected) <=
                           tolerance["atol"] + tolerance["rtol"] * expected.abs()),
                 f"teacher {label} f/alpha consistency failure")
    tolerance = contract["f_monotonicity"]
    _require(torch.all((h_peak[..., 3] - h_pre[..., 3]) <=
                       tolerance["atol"] + tolerance["rtol"] * h_pre[..., 3].abs()),
             "teacher f monotonicity failure")


def build_runtime(*, packet_dir: Path, config_path: Path, device: torch.device,
                  executable: bool = False) -> Runtime:
    arrays, metadata, packet_identity = load_verified_packet(packet_dir)
    config = _json(config_path)
    _validate_reviewed_config(config, metadata, packet_identity, executable=executable)
    _require(arrays["d_pre"].shape == (16, config["data"]["native_nodes"]),
             "packet nodal support differs from config")
    _require(arrays["history_pre"].shape ==
             (16, config["data"]["native_q4_elements"],
              config["data"]["gauss_points_per_element"], 4),
             "packet GP support differs from config")
    _require(np.array_equal(arrays["cycles"], np.asarray(config["data"]["selected_cycles"], dtype=np.int64)),
             "packet cycle values/order differ from config")
    _require(np.array_equal(arrays["path"], np.asarray(config["data"]["prescribed_path"], dtype=np.float64)),
             "packet prescribed path differs from config")
    _verify_packet_states_before_model(arrays, config, device=device)
    xy, conn, shape, dshape, det = _verify_static_geometry(arrays, device=device)
    observed_equilibrium = compute_equilibrium_normaliser(arrays, device=device)
    if executable:
        _require(float(config["normalisers"]["equilibrium"]) == observed_equilibrium,
                 "resolved equilibrium normaliser mismatch")
    graph_np = build_graph(arrays["xy"], arrays["conn"], arrays["nodal_weight"], bins=24)
    graph = graph_to_torch(graph_np, device, dtype=torch.float64)
    torch.testing.assert_close(graph["area"], torch.as_tensor(arrays["nodal_weight"], device=device), rtol=0, atol=0)
    normal = config["normalisers"]
    model = Stage0ATransitionOperator(
        normal["damage_increment"], normal["history_increment"][:3],
        normal["displacement"], width=config["model"]["width"],
        rank=config["model"]["rank"],
    ).to(device=device, dtype=torch.float64)
    parameter_order = [name for name, _ in model.named_parameters()]
    if executable:
        resolved_order = config["optimisation"]["gradient_vector_contract"].get(
            "resolved_parameter_order")
        _require(resolved_order == parameter_order,
                 "resolved parameter order missing or differs from constructed model")
    _require(model.damage_increment_scale.item() == normal["damage_increment"], "damage scale rounding")
    _require(model.history_increment_scale.tolist() == normal["history_increment"][:3], "history scale rounding")
    _require(model.displacement_scale.tolist() == normal["displacement"], "displacement scale rounding")
    scales = {
        "d": torch.tensor(normal["damage_increment"], dtype=torch.float64, device=device),
        "history": torch.tensor(normal["history_increment"], dtype=torch.float64, device=device),
        "u": torch.tensor(normal["displacement"], dtype=torch.float64, device=device),
    }
    return Runtime(arrays, metadata, packet_identity, config, graph, conn, shape,
                   dshape, det, model, scales, observed_equilibrium, device)


def _example(runtime: Runtime, index: int):
    a, device = runtime.arrays, runtime.device
    inputs = (
        torch.as_tensor(a["d_pre"][index], dtype=torch.float64, device=device),
        torch.as_tensor(a["history_pre"][index], dtype=torch.float64, device=device),
        torch.as_tensor(a["path"], dtype=torch.float64, device=device),
    )
    target = {
        "d_peak": torch.as_tensor(a["d_peak"][index], dtype=torch.float64, device=device),
        "history_peak": torch.as_tensor(a["history_peak"][index], dtype=torch.float64, device=device),
        "u_peak": torch.as_tensor(a["u_peak"][index], dtype=torch.float64, device=device),
    }
    return inputs, target


def hard_constraint_report(runtime: Runtime, d_pre: torch.Tensor,
                           history_pre: torch.Tensor, output: dict[str, torch.Tensor]) -> dict[str, int]:
    contract = runtime.config["model"]["hard_constraint_contract"]
    expected_pre = carrara_f(history_pre[..., 1])
    pre_tol = contract["prestate_f_consistency"]
    derived_tol = contract["derived_f_identity"]
    mono_tol = contract["f_monotonicity"]
    bc_tol = contract["peak_boundary_lifting"]
    expected_peak = carrara_f(output["history_peak"][..., 1])
    affine = affine_displacement(runtime.graph["xy"], output["u_peak"].new_tensor(runtime.arrays["path"][4]))
    mask = runtime.graph["boundary"]
    counts = {
        "prestate_f_consistency": int((torch.abs(history_pre[..., 3] - expected_pre) >
            pre_tol["atol"] + pre_tol["rtol"] * expected_pre.abs()).sum().item()),
        "damage_irreversibility": int((output["d_peak"] < d_pre).sum().item()),
        "damage_upper_bound": int((output["d_peak"] > 1).sum().item()),
        "alpha_irreversibility": int((output["history_peak"][..., 1] < history_pre[..., 1]).sum().item()),
        "derived_f_identity": int((torch.abs(output["history_peak"][..., 3] - expected_peak) >
            derived_tol["atol"] + derived_tol["rtol"] * expected_peak.abs()).sum().item()),
        "f_monotonicity": int(((output["history_peak"][..., 3] - history_pre[..., 3]) >
            mono_tol["atol"] + mono_tol["rtol"] * history_pre[..., 3].abs()).sum().item()),
        "peak_boundary_lifting": int((torch.abs(output["u_peak"][mask] - affine[mask]) >
            bc_tol["atol"] + bc_tol["rtol"] * affine[mask].abs()).sum().item()),
    }
    _require(sum(counts.values()) == 0, f"hard-constraint violation: {counts}")
    return counts


def _objectives(runtime: Runtime, index: int):
    inputs, target = _example(runtime, index)
    d_pre, history_pre, path = inputs
    output = runtime.model(d_pre, history_pre, path, runtime.graph, runtime.conn,
                           runtime.shape, runtime.det)
    hard_constraint_report(runtime, d_pre, history_pre, output)
    base = stage0a_objectives(
        output, target, runtime.scales, conn=runtime.conn, shape=runtime.shape,
        dshape=runtime.dshape, det=runtime.det, xy=runtime.graph["xy"],
        equilibrium_scale=runtime.equilibrium_scale,
    )
    raw = raw_increment_objectives(output, target, d_pre, history_pre, runtime.model)
    objectives = (
        base["nodal_state"] + raw["raw_nodal_increment"],
        base["gp_history"] + raw["raw_gp_increment"],
        base["equilibrium"],
    )
    for name, value in zip(OBJECTIVE_ORDER, objectives):
        _finite_scalar(value, name)
    return output, target, objectives, base, raw


def full_objective_gradients(model: torch.nn.Module, objectives) -> tuple[list[torch.Tensor], dict[str, Any]]:
    named = list(model.named_parameters())
    _require(named and len({name for name, _ in named}) == len(named), "invalid parameter order")
    vectors, records = [], []
    for objective_index, (objective_name, objective) in enumerate(zip(OBJECTIVE_ORDER, objectives)):
        grads = torch.autograd.grad(objective, [p for _, p in named], allow_unused=True,
                                    retain_graph=objective_index < len(objectives) - 1)
        blocks, unconnected = [], []
        for (name, parameter), gradient in zip(named, grads):
            if gradient is None:
                gradient = torch.zeros_like(parameter)
                unconnected.append(name)
            _require(gradient.shape == parameter.shape and torch.isfinite(gradient).all(),
                     f"invalid gradient block: {objective_name}/{name}", FloatingPointError)
            blocks.append(gradient.reshape(-1))
        vector = torch.cat(blocks)
        vectors.append(vector)
        records.append({"objective": objective_name, "unconnected_parameters": unconnected,
                        "parameter_block_count": len(blocks), "vector_length": vector.numel()})
    _require(len({record["vector_length"] for record in records}) == 1,
             "objective vector length mismatch")
    return vectors, {"parameter_order": [name for name, _ in named], "objectives": records}


def assign_merged_gradient(model: torch.nn.Module, merged: torch.Tensor, parameter_order: list[str]) -> None:
    named = list(model.named_parameters())
    _require([name for name, _ in named] == parameter_order, "parameter order changed")
    cursor = 0
    for _, parameter in named:
        count = parameter.numel()
        block = merged[cursor:cursor + count]
        _require(block.numel() == count, "missing merged gradient block")
        parameter.grad = block.reshape_as(parameter).clone()
        cursor += count
    _require(cursor == merged.numel() and torch.isfinite(merged).all(), "merged gradient length/finiteness failure")


def gradient_record(vectors: list[torch.Tensor], merged: torch.Tensor,
                    diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Bind objective geometry and the exact effective direction without a huge JSON vector."""
    eps = float(diagnostics["norm_epsilon"])
    pairwise = {}
    for left in range(len(vectors)):
        for right in range(left + 1, len(vectors)):
            denominator = vectors[left].norm() * vectors[right].norm()
            value = None if denominator <= eps * eps else float(
                (vectors[left].dot(vectors[right]) / denominator).detach().cpu())
            pairwise[f"{OBJECTIVE_ORDER[left]}__{OBJECTIVE_ORDER[right]}"] = value
    merged_bytes = np.ascontiguousarray(merged.detach().cpu().numpy()).tobytes()
    return {
        "raw_norms": [float(x) for x in diagnostics["raw_norms"].detach().cpu()],
        "pairwise_raw_cosines": pairwise,
        "reference_norm": float(diagnostics["reference_norm"].detach().cpu()),
        "conflict_projection_count": diagnostics["conflict_projection_count"],
        "zero_gradient_count": diagnostics["zero_gradient_count"],
        "merged_norm_before_clip": float(diagnostics["merged_norm_before_clip"].detach().cpu()),
        "merged_norm_after_clip": float(diagnostics["merged_norm_after_clip"].detach().cpu()),
        "effective_merged_direction": {
            "dtype": str(merged.detach().cpu().numpy().dtype),
            "vector_length": merged.numel(),
            "sha256": hashlib.sha256(merged_bytes).hexdigest(),
        },
    }


def proposal_projection_diagnostics(runtime: Runtime, d_pre: torch.Tensor,
                                    output: dict[str, torch.Tensor]) -> dict[str, int]:
    raw_d_increment = output["raw_node"][:, 0] * runtime.model.damage_increment_scale
    raw_alpha_increment = output["raw_history"][..., 1] * runtime.model.history_increment_scale[1]
    raw_damage = d_pre + raw_d_increment
    return {
        "damage_lower_projection_count": int((raw_damage < d_pre).sum().item()),
        "damage_upper_projection_count": int((raw_damage > 1).sum().item()),
        "alpha_relu_saturation_count": int((raw_alpha_increment < 0).sum().item()),
    }


def evaluate(runtime: Runtime) -> dict[str, Any]:
    runtime.model.eval()
    judge, damage_mae, false_growth, violations = [], [], [], 0
    nodal = torch.as_tensor(runtime.arrays["nodal_weight"], device=runtime.device)
    denominator = nodal.sum()
    with torch.no_grad():
        for index in range(16):
            inputs, target = _example(runtime, index)
            output = runtime.model(*inputs, runtime.graph, runtime.conn, runtime.shape, runtime.det)
            report = hard_constraint_report(runtime, inputs[0], inputs[1], output)
            violations += sum(report.values())
            judge.append(fixed_judgement_loss(output, target, runtime.scales))
            pred_delta = output["d_peak"] - inputs[0]
            true_delta = target["d_peak"] - inputs[0]
            damage_mae.append(((pred_delta - true_delta).abs() * nodal).sum() / denominator)
            false_growth.append((torch.relu(pred_delta - true_delta) * nodal).sum() / denominator)
    cycles = runtime.arrays["cycles"].tolist()
    growth = [cycles.index(value) for value in runtime.config["data"]["growth_cycles"]]
    stagnant = [cycles.index(value) for value in runtime.config["data"]["near_stagnant_cycles"]]
    persistence = []
    for index in growth:
        delta = torch.as_tensor(runtime.arrays["d_peak"][index] - runtime.arrays["d_pre"][index], device=runtime.device)
        persistence.append((delta.abs() * nodal).sum() / denominator)
    return {
        "L_judge": float(torch.stack(judge).mean().cpu()),
        "growth_damage_increment_mae": float(torch.stack([damage_mae[i] for i in growth]).mean().cpu()),
        "growth_persistence_baseline": float(torch.stack(persistence).mean().cpu()),
        "near_stagnant_false_growth": float(torch.stack([false_growth[i] for i in stagnant]).mean().cpu()),
        "hard_constraint_violations": violations,
        "finite": True,
    }


def _execution_preflight(runtime: Runtime, *, config_path: Path, packet_dir: Path,
                         output_dir: Path, repo_root: Path) -> None:
    _require(sys.platform.startswith("linux"), "P1 training is forbidden off Linux", PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible, "exactly one CUDA_VISIBLE_DEVICES entry is required")
    _require(str(runtime.config["producer"]["gpu_id"]) == visible, "GPU ID/config mismatch")
    _require(output_dir == Path(runtime.config["producer"]["remote_root"]), "output root differs from resolved config")
    _require(str(output_dir).startswith("/mnt/data2/drtao/wennie/"), "invalid Taobo output root")
    _require(not output_dir.exists(), "fresh output root already exists")
    _require(current_commit(repo_root) == runtime.config["source"]["training_commit"], "trainer commit mismatch")
    _require(packet_dir.is_dir(), "packet directory missing")
    free = shutil.disk_usage(output_dir.parent).free
    _require(free >= 5 * 1024**3, "less than 5 GiB free at Taobo run root")


def run_training(*, packet_dir: Path, config_path: Path, output_dir: Path,
                 repo_root: Path) -> dict[str, Any]:
    """Execute the reviewed 1,000-update run after all final gates resolve."""
    _require(sys.platform.startswith("linux"), "P1 training is forbidden off Linux", PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required", RuntimeError)
    device = torch.device("cuda:0")
    config = _json(config_path)
    torch.manual_seed(config["model"]["seed"])
    torch.cuda.manual_seed_all(config["model"]["seed"])
    runtime = build_runtime(packet_dir=packet_dir, config_path=config_path,
                            device=device, executable=True)
    _execution_preflight(runtime, config_path=config_path, packet_dir=packet_dir,
                         output_dir=output_dir, repo_root=repo_root)
    output_dir.mkdir(parents=False)
    start = time.time()
    try:
        initial = evaluate(runtime)
        (output_dir / "judgement_initial.json").write_bytes(canonical_json(initial))
        optimizer = torch.optim.AdamW(
            runtime.model.parameters(), lr=config["optimisation"]["learning_rate"],
            betas=tuple(config["optimisation"]["betas"]), eps=config["optimisation"]["epsilon"],
            weight_decay=config["optimisation"]["weight_decay"],
        )
        train_rows, gradient_rows, diagnostics = [], [], {"0": initial}
        order = config["data"]["selected_cycles"]
        cycles = runtime.arrays["cycles"].tolist()
        for update in range(1, 1001):
            index = cycles.index(order[(update - 1) % len(order)])
            runtime.model.train()
            optimizer.zero_grad(set_to_none=True)
            output, _, objectives, base, raw = _objectives(runtime, index)
            d_pre = torch.as_tensor(runtime.arrays["d_pre"][index], dtype=torch.float64,
                                    device=runtime.device)
            vectors, layout = full_objective_gradients(runtime.model, objectives)
            merged, grad_diag = merge_objective_gradients(
                vectors, clip_norm=config["optimisation"]["global_clip_norm"],
                eps=config["optimisation"]["gradient_epsilon"])
            assign_merged_gradient(runtime.model, merged, layout["parameter_order"])
            optimizer.step()
            train_rows.append({
                "update": update, "cycle": cycles[index],
                "scaled_combined_objectives": {
                    name: float(value.detach().cpu()) for name, value in zip(OBJECTIVE_ORDER, objectives)},
                "scaled_projected_output_objectives": {
                    name: float(value.detach().cpu()) for name, value in base.items()},
                "raw_increment_objectives": {
                    name: float(value.detach().cpu()) for name, value in raw.items()},
                "proposal_projection_diagnostics": proposal_projection_diagnostics(
                    runtime, d_pre, output),
            })
            gradient_rows.append({
                "update": update, "cycle": cycles[index], "layout": layout,
                **gradient_record(vectors, merged, grad_diag),
            })
            if update in DIAGNOSTIC_STEPS:
                diagnostics[str(update)] = evaluate(runtime)
        final = evaluate(runtime)
        _require(len(train_rows) == 1000 and train_rows[-1]["cycle"] == 46, "update schedule mismatch")
        capacity = final["L_judge"] <= 0.20 * initial["L_judge"]
        growth = final["growth_damage_increment_mae"] < final["growth_persistence_baseline"]
        stagnant = final["near_stagnant_false_growth"] <= 0.25 * runtime.config["normalisers"]["damage_increment"]
        validity = final["finite"] and final["hard_constraint_violations"] == 0
        decision = {
            "formal_p1_pass": bool(capacity and growth and stagnant and validity),
            "clauses": {"capacity": bool(capacity), "growth": bool(growth),
                        "near_stagnant": bool(stagnant), "validity": bool(validity)},
            "initial": initial, "final": final,
            "claim_boundary": "development-only bounded memorisation; no rollout/generalisation/FEM-truth/teacher-validity/PINO-benefit claim",
        }
        (output_dir / "judgement_final.json").write_bytes(canonical_json(final))
        (output_dir / "decision_metrics.json").write_bytes(canonical_json(decision))
        with (output_dir / "train_log.jsonl").open("w") as stream:
            for row in train_rows: stream.write(canonical_json(row).decode())
        with (output_dir / "gradient_diagnostics.jsonl").open("w") as stream:
            for row in gradient_rows: stream.write(canonical_json(row).decode())
        torch.save({"model": runtime.model.state_dict(), "optimizer": optimizer.state_dict(),
                    "update": 1000, "config_sha256": sha256_file(config_path),
                    "packet_sha256": runtime.packet_identity["manifest_sha256"]},
                   output_dir / "checkpoint_final.pt")
        (output_dir / "config_resolved.json").write_bytes(config_path.read_bytes())
        (output_dir / "input_packet_identity.json").write_bytes(
            canonical_json(runtime.packet_identity))
        environment = {
            "hostname": socket.gethostname(), "platform": platform.platform(),
            "python": sys.version, "torch": torch.__version__,
            "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
            "CUDA_VISIBLE_DEVICES": os.environ["CUDA_VISIBLE_DEVICES"],
            "commit": current_commit(repo_root),
        }
        (output_dir / "environment.txt").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.4, 3.8))
        ax.plot([row["update"] for row in train_rows],
                [sum(row["scaled_combined_objectives"].values()) for row in train_rows], linewidth=0.8)
        ax.set(xlabel="successful update", ylabel="sum of three training objectives",
               title="S09-E008 P1 bounded memorisation diagnostic")
        ax.set_yscale("log"); fig.tight_layout(); fig.savefig(output_dir / "decision_figure.png", dpi=180); plt.close(fig)
        readme = (
            "# S09-E008 P1 analysis\n\n"
            "Question: can the fixed Stage-0A operator memorise the 16 development examples under the frozen multi-objective update?\n\n"
            "Read decision_metrics.json first, then judgement_initial.json and judgement_final.json, followed by the loss/gradient logs and decision_figure.png.\n\n"
            f"Formal verdict: {'PASS' if decision['formal_p1_pass'] else 'FAIL'} under the predeclared conjunction.\n\n"
            "Allowed conclusion: bounded development-set capacity and per-bucket diagnostics only.\n"
            "Blocked conclusions: rollout, generalisation, FEM truth, teacher validity, capture neutrality and PINO benefit.\n"
        )
        (output_dir / "README_analysis.md").write_text(readme)
        receipt = {
            "status": "SUCCEEDED", "run_id": config["planned_run_id"],
            "successful_updates": 1000, "elapsed_seconds": time.time() - start,
            "commit": current_commit(repo_root), "config_sha256": sha256_file(config_path),
            "packet_manifest_sha256": runtime.packet_identity["manifest_sha256"],
            "producer": environment, "decision": decision,
        }
        (output_dir / "run_receipt.json").write_bytes(canonical_json(receipt))
        missing = set(config["minimum_outputs"]) - {p.name for p in output_dir.iterdir()}
        _require(not missing, f"minimum outputs missing: {sorted(missing)}")
        return receipt
    except BaseException as error:
        failure = {"status": "FAILED", "error_type": type(error).__name__,
                   "error": str(error), "elapsed_seconds": time.time() - start}
        (output_dir / "run_receipt.json").write_bytes(canonical_json(failure))
        raise
