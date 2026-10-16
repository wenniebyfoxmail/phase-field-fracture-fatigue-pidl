"""Bounded P1 memorisation runner for the reviewed S09-E008 package."""
from __future__ import annotations

from dataclasses import dataclass, replace
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
from s09_stage0a_capability import S09_E008_CONTEXT
from s09_code_identity import current_commit, require_approved_code, tracked_execution_files_clean
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
REVIEWED_BASE_CONFIG_SHA256 = "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
REVIEWED_BASE_CONFIG_CANONICAL_SHA256 = "dc9a85f1c5949c8081f7efe91d56c0d5ecfbb2b5df10b23acd1f88587c446db2"


def _require(condition: bool, message: str, error=ValueError) -> None:
    if not condition:
        raise error(message)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _finite_scalar(value: torch.Tensor, name: str) -> None:
    _require(value.ndim == 0 and torch.isfinite(value), f"nonfinite/non-scalar {name}", FloatingPointError)


def _tracked_execution_files_clean(root: Path) -> bool:
    return tracked_execution_files_clean(root)


def gpu_identity(visible: str) -> dict[str, str]:
    """Return a stable physical identity, not just a model name or ordinal."""
    result = subprocess.run(
        ["nvidia-smi", f"--id={visible}", "--query-gpu=uuid,pci.bus_id,name",
         "--format=csv,noheader,nounits"], check=True, capture_output=True, text=True)
    rows = [row.strip() for row in result.stdout.splitlines() if row.strip()]
    _require(len(rows) == 1, "visible GPU does not resolve to exactly one physical identity")
    parts = [part.strip() for part in rows[0].split(",", 2)]
    _require(len(parts) == 3 and all(parts), "incomplete physical GPU identity")
    return {"uuid": parts[0], "pci_bus_id": parts[1], "name": parts[2]}


def _resolved_config_base_projection(config: dict[str, Any]) -> dict[str, Any]:
    """Reverse only the declared resolution fields to recover the reviewed base config."""
    projected = copy.deepcopy(config)
    projected["status"] = "PACKAGE_SPEC_REVISED_AFTER_CODE_REVIEW_ROUND1"
    projected["execution_authorized"] = False
    projected["source"]["training_commit"] = "TO_BE_LOCKED_AS_CANDIDATE_BEFORE_EXACT_COMMIT_CODE_REVIEW"
    projected["source"]["input_packet_sha256"] = "TO_BE_LOCKED_AFTER_REVIEWED_PACKET_EXPORT"
    projected["source"]["code_ready_approved_commit"] = "TO_BE_SET_FROM_CODE_READY_VERDICT"
    projected["producer"]["gpu_id"] = "TO_BE_LOCKED_AFTER_READ_ONLY_AVAILABILITY_CHECK"
    projected["producer"]["resolved_environment"] = "TO_BE_LOCKED_BY_READ_ONLY_TAOBO_PREFLIGHT"
    projected["normalisers"]["equilibrium"] = (
        "freeze_before_model_initialisation_as_mean_selected_teacher-damage_affine-BC_free-DOF_force_MSE"
    )
    projected["optimisation"]["gradient_vector_contract"].pop("resolved_parameter_order", None)
    projected.pop("resolution_receipt", None)
    return projected


def _validate_complete_base_invariants(config: dict[str, Any]) -> None:
    observed = hashlib.sha256(canonical_json(_resolved_config_base_projection(config))).hexdigest()
    _require(observed == REVIEWED_BASE_CONFIG_CANONICAL_SHA256,
             "resolved config contains non-resolution drift from reviewed base")


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
                             approved_code_commit: str,
                             approved_hostname: str, approved_gpu_name: str,
                             approved_gpu_uuid: str, approved_gpu_pci_bus_id: str,
                             approved_staging_root: Path,
                             authorize_execution: bool) -> dict[str, Any]:
    """Resolve producer identities before training; never starts an optimiser."""
    _require(sys.platform.startswith("linux"), "config resolution is producer-only", PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required for producer resolution", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible, "exactly one CUDA_VISIBLE_DEVICES entry is required")
    output_path = validated_staging_path(output_path, approved_staging_root)
    _require(not output_path.exists(), "resolved config output already exists")
    _require(socket.gethostname() == approved_hostname, "producer hostname differs from approved preflight")
    observed_gpu = gpu_identity(visible)
    _require(observed_gpu == {"uuid": approved_gpu_uuid,
                              "pci_bus_id": approved_gpu_pci_bus_id,
                              "name": approved_gpu_name},
             "physical GPU differs from approved preflight")
    _require(sha256_file(base_config_path) == REVIEWED_BASE_CONFIG_SHA256,
             "base config differs from Code Ready candidate")
    require_approved_code(repo_root, approved_code_commit)
    arrays, metadata, packet_identity = load_verified_packet(packet_dir)
    config = _json(base_config_path)
    _validate_reviewed_config(config, metadata, packet_identity, executable=False)
    _require(metadata.get("exporter_code_commit") == approved_code_commit,
             "packet exporter code differs from approved Code Ready commit")
    _require(metadata.get("config_sha256") == REVIEWED_BASE_CONFIG_SHA256,
             "packet is not bound to reviewed base config")
    _require(metadata.get("source_p1_verdict") == "P1_CONTRACT_FROZEN" and
             metadata.get("source_hash_verdict") == "FULL_TRAJECTORY_HASH_QUALIFIED" and
             metadata.get("source_decode_verdict") == "FULL_TRAJECTORY_DECODE_QUALIFIED",
             "packet qualification verdict drift")
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
    resolved["source"]["code_ready_approved_commit"] = approved_code_commit
    resolved["source"]["input_packet_sha256"] = packet_identity["manifest_sha256"]
    resolved["producer"]["gpu_id"] = visible
    resolved["producer"]["resolved_environment"] = {
        "hostname": socket.gethostname(), "platform": platform.platform(),
        "python": sys.version, "torch": torch.__version__, "cuda": torch.version.cuda,
        "gpu": observed_gpu, "CUDA_VISIBLE_DEVICES": visible,
    }
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
        "code_ready_approved_commit": approved_code_commit,
        "CUDA_VISIBLE_DEVICES": visible,
        "physical_gpu": observed_gpu,
        "staging_root": str(approved_staging_root.resolve(strict=True)),
        "resolved_config_path": str(output_path),
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
    _require(config["data"]["selected_cycles"] ==
             [1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73],
             "selected cycle drift")
    _require(config["data"]["prescribed_path"] ==
             [0.0, 0.031249875, 0.062499875, 0.093749875, 0.124999875, 0.0],
             "prescribed path drift")
    _require(config["data"]["history_order"] == ["H", "alpha_bar", "q_prev", "f"],
             "history channel drift")
    _require(config["data"]["selected_cycles"] == metadata["selected_cycles"], "packet/config cycle drift")
    _require(config["data"]["history_order"] == metadata["history_order"], "packet/config channel drift")
    _require(config["optimisation"]["objectives_in_fixed_order"] == list(OBJECTIVE_ORDER), "objective order drift")
    _require(config["optimisation"]["updates"] == 1000 and config["data"]["batch_size"] == 1,
             "budget drift")
    _require(config["model"]["dtype"] == "float64" and config["model"]["seed"] == 20261016,
             "dtype/seed drift")
    _require({key: config["model"][key] for key in ("width", "rank", "local_blocks", "coarse_blocks")} ==
             {"width": 32, "rank": 8, "local_blocks": 2, "coarse_blocks": 1},
             "model architecture drift")
    _require(config["data"]["growth_cycles"] == [1, 58, 60, 69, 70] and
             config["data"]["near_stagnant_cycles"] == [3, 4, 71, 72, 73],
             "judgement group drift")
    _require(config["data"]["detectable_growth_scale_D"] == 0.00016864539921617467 and
             config["data"]["near_stagnant_selection_limit"] == 8.432269960808734e-06,
             "P1 selection threshold drift")
    expected_scales = {
        "damage_increment": 0.006896013386826084,
        "history_increment": [96.63136736963305, 0.00614771012425793,
                              0.0059082164580187314, 0.004071375747189726],
        "displacement": [0.00904670012757536, 0.08381964836377313],
    }
    _require(all(config["normalisers"][key] == value for key, value in expected_scales.items()),
             "frozen scale drift")
    expected_optimisation = {
        "optimizer": "AdamW", "learning_rate": 0.0003,
        "betas": [0.9, 0.999], "epsilon": 1e-08, "weight_decay": 0.0,
        "updates": 1000, "gradient_epsilon": 1e-12, "global_clip_norm": 1.0,
    }
    _require(all(config["optimisation"][key] == value
                 for key, value in expected_optimisation.items()), "optimisation method drift")
    _require(config["source"]["static_sha256"] == metadata["source_static_sha256"], "static drift")
    _require(config["source"]["capability_receipt_sha256"] == metadata["source_capability_receipt_sha256"],
             "capability receipt drift")
    _require(config["producer"]["alias"] == "Taobo GPU" and
             config["producer"]["forbidden_fallback"] == "CSD3" and
             config["producer"]["remote_root"] ==
             "/mnt/data2/drtao/wennie/S09-E008-P1-R001-stage0a-memorisation" and
             config["producer"]["archive_root"] ==
             "/mnt/data2/drtao/pidl_archives/S09-E008-P1-R001-stage0a-memorisation",
             "producer/root contract drift")
    for key in ("growth_cycles", "near_stagnant_cycles", "detectable_growth_scale_D",
                "near_stagnant_selection_limit"):
        _require(metadata[key] == config["data"][key], f"packet/config {key} drift")
    packet_sha = config["source"]["input_packet_sha256"]
    if executable:
        _validate_complete_base_invariants(config)
        _require((config["data"]["native_nodes"], config["data"]["native_q4_elements"],
                  config["data"]["gauss_points_per_element"]) == (86756, 86408, 4),
                 "native support drift")
        _require(config["execution_authorized"] is True, "execution is not authorised", PermissionError)
        _require(packet_sha == packet_identity["manifest_sha256"], "resolved packet identity mismatch")
        for field in ("training_commit", "input_packet_sha256"):
            _require("TO_BE_" not in str(config["source"][field]), f"unresolved source field: {field}")
        _require(isinstance(config["normalisers"]["equilibrium"], (int, float)),
                 "equilibrium normaliser is unresolved")
        _require("TO_BE_" not in str(config["producer"]["gpu_id"]), "GPU ID is unresolved")
        _require(config["source"]["code_ready_approved_commit"] == config["source"]["training_commit"],
                 "Code Ready approval is not bound to training commit")
        _require(metadata.get("exporter_code_commit") == config["source"]["training_commit"],
                 "packet exporter code is not bound to approved training commit")
        _require(config["resolution_receipt"]["base_config_sha256"] == REVIEWED_BASE_CONFIG_SHA256,
                 "reviewed base config identity mismatch")
        _require(isinstance(config["producer"]["resolved_environment"], dict),
                 "producer environment is unresolved")
        _require(metadata.get("config_sha256") == REVIEWED_BASE_CONFIG_SHA256,
                 "packet was not exported from reviewed base config")
        _require(metadata.get("source_p1_verdict") == "P1_CONTRACT_FROZEN" and
                 metadata.get("source_hash_verdict") == "FULL_TRAJECTORY_HASH_QUALIFIED" and
                 metadata.get("source_decode_verdict") == "FULL_TRAJECTORY_DECODE_QUALIFIED",
                 "packet qualification verdict drift")
        _require(metadata.get("normalisers") == expected_scales,
                 "packet frozen normaliser metadata drift")
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
    _require(torch.all(h_pre[..., 1] >= 0) and torch.all(h_peak[..., 1] >= 0),
             "teacher alpha must be nonnegative")
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
    cycles = arrays["cycles"].tolist()
    growth = config["data"]["growth_cycles"]
    stagnant = config["data"]["near_stagnant_cycles"]
    _require(growth and stagnant and all(value in cycles for value in growth + stagnant),
             "empty or invalid judgement group")
    nodal = torch.as_tensor(arrays["nodal_weight"], dtype=torch.float64, device=device)
    growth_values = []
    for cycle in growth:
        index = cycles.index(cycle)
        growth_values.append(((d_peak[index] - d_pre[index]).abs() * nodal).sum() / nodal.sum())
    baseline = torch.stack(growth_values).mean()
    _require(torch.isfinite(baseline) and baseline > 0,
             "growth persistence baseline must be finite and positive")


def build_runtime(*, packet_dir: Path, config_path: Path, device: torch.device,
                  executable: bool = False) -> Runtime:
    config = _json(config_path)
    context = S09_E008_CONTEXT if executable else replace(
        S09_E008_CONTEXT, expected_nodes=config["data"]["native_nodes"],
        expected_elements=config["data"]["native_q4_elements"])
    arrays, metadata, packet_identity = load_verified_packet(packet_dir, context=context)
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
    required = ("d_peak", "history_peak", "u_peak", "raw_node", "raw_history",
                "gp_weight", "nodal_weight")
    _require(all(name in output for name in required), "projected output record is incomplete")
    _require(all(torch.isfinite(output[name]).all() for name in required),
             "nonfinite projected/raw output or support weight", FloatingPointError)
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
    objectives = {
        OBJECTIVE_ORDER[0]: base["nodal_state"] + raw["raw_nodal_increment"],
        OBJECTIVE_ORDER[1]: base["gp_history"] + raw["raw_gp_increment"],
        OBJECTIVE_ORDER[2]: base["equilibrium"],
    }
    for name, value in objectives.items():
        _finite_scalar(value, name)
    return output, target, objectives, base, raw


def full_objective_gradients(model: torch.nn.Module, objectives) -> tuple[list[torch.Tensor], dict[str, Any]]:
    _require(isinstance(objectives, dict) and tuple(objectives) == OBJECTIVE_ORDER,
             "exactly three named ordered objective records are required")
    named = list(model.named_parameters())
    _require(named and len({name for name, _ in named}) == len(named), "invalid parameter order")
    vectors, records = [], []
    for objective_index, (objective_name, objective) in enumerate(objectives.items()):
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
        "balanced_norms": [float(x) for x in diagnostics["balanced_norms"].detach().cpu()],
        "projected_norms": [float(x) for x in diagnostics["projected_norms"].detach().cpu()],
        "post_projection_alignment_with_merged": [
            None if not torch.isfinite(x) else float(x)
            for x in diagnostics["post_projection_cosines"].detach().cpu()],
        "effective_norm_ratios_to_reference": [
            None if diagnostics["reference_norm"] <= eps else float(
                (x / diagnostics["reference_norm"]).detach().cpu())
            for x in diagnostics["projected_norms"]
        ],
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


def unscaled_raw_increment_mse(runtime: Runtime, output: dict[str, torch.Tensor],
                               target: dict[str, torch.Tensor], d_pre: torch.Tensor,
                               history_pre: torch.Tensor) -> dict[str, float]:
    d_error = (output["raw_node"][:, 0] * runtime.model.damage_increment_scale -
               (target["d_peak"] - d_pre))
    h_error = (output["raw_history"] * runtime.model.history_increment_scale -
               (target["history_peak"][..., :3] - history_pre[..., :3]))
    d_value = (d_error.square() * output["nodal_weight"]).sum() / output["nodal_weight"].sum()
    h_value = (h_error.square() * output["gp_weight"][..., None]).sum((0, 1)) / output["gp_weight"].sum()
    _require(torch.isfinite(d_value) and torch.isfinite(h_value).all(),
             "nonfinite unscaled raw-increment diagnostic", FloatingPointError)
    return {"damage": float(d_value.detach().cpu()),
            **{f"history_{name}": float(value.detach().cpu())
               for name, value in zip(("H", "alpha_bar", "q_prev"), h_value)}}


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
    _require(growth and stagnant and persistence, "empty judgement group")
    values = {
        "L_judge": torch.stack(judge).mean(),
        "growth_damage_increment_mae": torch.stack([damage_mae[i] for i in growth]).mean(),
        "growth_persistence_baseline": torch.stack(persistence).mean(),
        "near_stagnant_false_growth": torch.stack([false_growth[i] for i in stagnant]).mean(),
    }
    _require(all(torch.isfinite(value) for value in values.values()), "nonfinite evaluation metric",
             FloatingPointError)
    _require(values["growth_persistence_baseline"] > 0, "persistence baseline must be positive")
    return {
        **{name: float(value.cpu()) for name, value in values.items()},
        "hard_constraint_violations": violations,
        "finite": True,
    }


def decision_from_metrics(initial: dict[str, Any], final: dict[str, Any],
                          config: dict[str, Any]) -> dict[str, Any]:
    capacity = final["L_judge"] <= 0.20 * initial["L_judge"]
    growth = final["growth_damage_increment_mae"] < final["growth_persistence_baseline"]
    stagnant_limit = 0.25 * config["data"]["detectable_growth_scale_D"]
    stagnant = final["near_stagnant_false_growth"] <= stagnant_limit
    validity = final["finite"] and final["hard_constraint_violations"] == 0
    return {
        "formal_p1_pass": bool(capacity and growth and stagnant and validity),
        "clauses": {"capacity": bool(capacity), "growth": bool(growth),
                    "near_stagnant": bool(stagnant), "validity": bool(validity)},
        "initial": initial, "final": final,
        "thresholds": {"capacity_ratio": 0.20,
                       "growth_persistence_baseline": final["growth_persistence_baseline"],
                       "detectable_growth_scale_D": config["data"]["detectable_growth_scale_D"],
                       "near_stagnant_false_growth_limit": stagnant_limit},
        "claim_boundary": "development-only bounded memorisation; no rollout/generalisation/FEM-truth/teacher-validity/PINO-benefit claim",
    }


def _reject_noncanonical_or_symlink(path: Path, label: str) -> Path:
    _require(path.is_absolute(), f"{label} must be absolute")
    _require(".." not in path.parts, f"{label} contains parent traversal")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if os.path.lexists(current):
            _require(not current.is_symlink(), f"{label} contains a symlink component")
    return path.resolve(strict=False)


def validated_staging_path(output_path: Path, approved_staging_root: Path) -> Path:
    root = _reject_noncanonical_or_symlink(approved_staging_root, "approved staging root")
    _require(root.is_dir(), "approved staging root does not exist")
    output = _reject_noncanonical_or_symlink(output_path, "resolved config path")
    _require(output.parent == root, "resolved config must be a direct child of approved staging root")
    return output


def validated_producer_paths(output_dir: Path, config: dict[str, Any]) -> tuple[Path, Path]:
    output = _reject_noncanonical_or_symlink(output_dir, "output root")
    configured = _reject_noncanonical_or_symlink(
        Path(config["producer"]["remote_root"]), "configured output root")
    approved_root = _reject_noncanonical_or_symlink(
        Path("/mnt/data2/drtao/wennie"), "approved output parent")
    archive = _reject_noncanonical_or_symlink(
        Path(config["producer"]["archive_root"]), "archive root")
    approved_archive = _reject_noncanonical_or_symlink(
        Path("/mnt/data2/drtao/pidl_archives"), "approved archive parent")
    _require(output == configured, "output root differs from resolved config")
    _require(output.parent == approved_root,
             "output root is not a direct child of approved Taobo root")
    _require(archive.parent == approved_archive,
             "archive root is not a direct child of approved archive root")
    return output, archive


def _execution_preflight(runtime: Runtime, *, config_path: Path, packet_dir: Path,
                         output_dir: Path, repo_root: Path) -> None:
    _require(sys.platform.startswith("linux"), "P1 training is forbidden off Linux", PermissionError)
    _require(torch.cuda.is_available(), "CUDA is required", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible and "," not in visible, "exactly one CUDA_VISIBLE_DEVICES entry is required")
    _require(str(runtime.config["producer"]["gpu_id"]) == visible, "GPU ID/config mismatch")
    output_dir, _ = validated_producer_paths(output_dir, runtime.config)
    _require(not output_dir.exists(), "fresh output root already exists")
    _require(current_commit(repo_root) == runtime.config["source"]["training_commit"], "trainer commit mismatch")
    _require(current_commit(repo_root) == runtime.config["source"]["code_ready_approved_commit"],
             "trainer commit lacks exact Code Ready binding")
    _require(_tracked_execution_files_clean(repo_root), "tracked execution files are dirty")
    _require(packet_dir.is_dir(), "packet directory missing")
    free = shutil.disk_usage(output_dir.parent).free
    _require(free >= 5 * 1024**3, "less than 5 GiB free at Taobo run root")
    observed_environment = {
        "hostname": socket.gethostname(), "platform": platform.platform(),
        "python": sys.version, "torch": torch.__version__, "cuda": torch.version.cuda,
        "gpu": gpu_identity(visible), "CUDA_VISIBLE_DEVICES": visible,
    }
    _require(observed_environment == runtime.config["producer"]["resolved_environment"],
             "producer environment differs from resolved preflight")


def run_training(*, packet_dir: Path, config_path: Path, output_dir: Path,
                 repo_root: Path) -> dict[str, Any]:
    """Execute the reviewed 1,000-update run after all final gates resolve."""
    config = _json(config_path)
    _require(config.get("execution_authorized") is True,
             "unresolved config cannot create producer receipt roots", PermissionError)
    _require(config.get("source", {}).get("code_ready_approved_commit") == current_commit(repo_root),
             "config is not bound to current approved commit")
    output_dir, archive_dir = validated_producer_paths(output_dir, config)
    _require(not archive_dir.exists(), "fresh audit/archive root already exists")
    archive_dir.mkdir(parents=False)
    start = time.time()
    expected_packet_sha256 = config.get("source", {}).get("input_packet_sha256")
    optimizer_steps_completed = 0
    fully_logged_updates = 0
    last_diagnostic_update = None
    output_created_by_this_run = False
    stage = "producer_initialisation"
    runtime = None
    try:
        _require(sys.platform.startswith("linux"), "P1 training is forbidden off Linux", PermissionError)
        _require(torch.cuda.is_available(), "CUDA is required", RuntimeError)
        device = torch.device("cuda:0")
        torch.manual_seed(config["model"]["seed"])
        torch.cuda.manual_seed_all(config["model"]["seed"])
        runtime = build_runtime(packet_dir=packet_dir, config_path=config_path,
                                device=device, executable=True)
        stage = "execution_preflight"
        _execution_preflight(runtime, config_path=config_path, packet_dir=packet_dir,
                             output_dir=output_dir, repo_root=repo_root)
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=False)
        output_created_by_this_run = True
        (output_dir / "config_resolved.json").write_bytes(config_path.read_bytes())
        (output_dir / "input_packet_identity.json").write_bytes(canonical_json(runtime.packet_identity))
        environment = {**config["producer"]["resolved_environment"],
                       "commit": current_commit(repo_root)}
        (output_dir / "environment.txt").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n")
        stage = "initial_evaluation"
        initial = evaluate(runtime)
        (output_dir / "judgement_initial.json").write_bytes(canonical_json(initial))
        optimizer = torch.optim.AdamW(
            runtime.model.parameters(), lr=config["optimisation"]["learning_rate"],
            betas=tuple(config["optimisation"]["betas"]), eps=config["optimisation"]["epsilon"],
            weight_decay=config["optimisation"]["weight_decay"],
        )
        train_rows = []
        order = config["data"]["selected_cycles"]
        cycles = runtime.arrays["cycles"].tolist()
        stage = "training_updates"
        with (output_dir / "train_log.jsonl").open("x") as train_stream, \
             (output_dir / "gradient_diagnostics.jsonl").open("x") as gradient_stream, \
             (output_dir / "diagnostic_metrics.jsonl").open("x") as diagnostic_stream:
            diagnostic_stream.write(canonical_json({"update": 0, **initial}).decode()); diagnostic_stream.flush()
            last_diagnostic_update = 0
            for update in range(1, 1001):
                index = cycles.index(order[(update - 1) % len(order)])
                runtime.model.train()
                optimizer.zero_grad(set_to_none=True)
                output, target, objectives, base, raw = _objectives(runtime, index)
                d_pre, history_pre, _ = _example(runtime, index)[0]
                vectors, layout = full_objective_gradients(runtime.model, objectives)
                _require(layout["parameter_order"] == config["optimisation"]["gradient_vector_contract"]["resolved_parameter_order"],
                         "per-update parameter order differs from resolved config")
                merged, grad_diag = merge_objective_gradients(
                    vectors, clip_norm=config["optimisation"]["global_clip_norm"],
                    eps=config["optimisation"]["gradient_epsilon"])
                assign_merged_gradient(runtime.model, merged, layout["parameter_order"])
                optimizer.step()
                optimizer_steps_completed = update
                train_row = {
                    "update": update, "cycle": cycles[index],
                    "scaled_combined_objectives": {
                        name: float(value.detach().cpu()) for name, value in objectives.items()},
                    "scaled_projected_output_objectives": {
                        name: float(value.detach().cpu()) for name, value in base.items()},
                    "scaled_raw_proposal_objectives": {
                        name: float(value.detach().cpu()) for name, value in raw.items()},
                    "unscaled_raw_increment_mse": unscaled_raw_increment_mse(
                        runtime, output, target, d_pre, history_pre),
                    "proposal_projection_diagnostics": proposal_projection_diagnostics(runtime, d_pre, output),
                }
                gradient_row = {"update": update, "cycle": cycles[index], "layout": layout,
                                **gradient_record(vectors, merged, grad_diag)}
                train_rows.append(train_row)
                train_stream.write(canonical_json(train_row).decode()); train_stream.flush()
                gradient_stream.write(canonical_json(gradient_row).decode()); gradient_stream.flush()
                if update in DIAGNOSTIC_STEPS:
                    diagnostic_stream.write(canonical_json({"update": update, **evaluate(runtime)}).decode())
                    diagnostic_stream.flush()
                    last_diagnostic_update = update
                fully_logged_updates = update
        stage = "final_evaluation"
        final = evaluate(runtime)
        _require(len(train_rows) == 1000 and train_rows[-1]["cycle"] == 46, "update schedule mismatch")
        decision = decision_from_metrics(initial, final, runtime.config)
        (output_dir / "judgement_final.json").write_bytes(canonical_json(final))
        (output_dir / "decision_metrics.json").write_bytes(canonical_json(decision))
        torch.save({"model": runtime.model.state_dict(), "optimizer": optimizer.state_dict(),
                    "update": 1000, "config_sha256": sha256_file(config_path),
                    "packet_sha256": runtime.packet_identity["manifest_sha256"]},
                   output_dir / "checkpoint_final.pt")
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
            "successful_updates": 1000, "optimizer_steps_completed": 1000,
            "fully_logged_updates": 1000, "last_diagnostic_update": last_diagnostic_update,
            "last_valid_diagnostic_log": "diagnostic_metrics.jsonl",
            "elapsed_seconds": time.time() - start,
            "commit": current_commit(repo_root), "config_sha256": sha256_file(config_path),
            "packet_manifest_sha256": runtime.packet_identity["manifest_sha256"],
            "producer": environment, "decision": decision,
        }
        (output_dir / "run_receipt.json").write_bytes(canonical_json(receipt))
        (archive_dir / "run_receipt.json").write_bytes(canonical_json(receipt))
        missing = set(config["minimum_outputs"]) - {p.name for p in output_dir.iterdir()}
        _require(not missing, f"minimum outputs missing: {sorted(missing)}")
        return receipt
    except BaseException as error:
        failure = {
            "status": "FAILED", "stage": stage, "error_type": type(error).__name__,
            "error": str(error), "elapsed_seconds": time.time() - start,
            "successful_updates": fully_logged_updates,
            "optimizer_steps_completed": optimizer_steps_completed,
            "fully_logged_updates": fully_logged_updates,
            "last_diagnostic_update": last_diagnostic_update,
            "last_valid_diagnostic_log": (
                "diagnostic_metrics.jsonl" if output_created_by_this_run and last_diagnostic_update is not None
                else None),
            "run_id": config.get("planned_run_id"), "commit": current_commit(repo_root),
            "config_sha256": sha256_file(config_path),
            "expected_packet_manifest_sha256": expected_packet_sha256,
            "observed_packet_manifest_sha256": (
                None if runtime is None else runtime.packet_identity["manifest_sha256"]),
            "packet_identity_verified": runtime is not None,
            "audit_root": str(archive_dir),
        }
        (archive_dir / "run_receipt.json").write_bytes(canonical_json(failure))
        if output_created_by_this_run and output_dir.exists() and output_dir.is_dir():
            (output_dir / "run_receipt.json").write_bytes(canonical_json(failure))
        raise
