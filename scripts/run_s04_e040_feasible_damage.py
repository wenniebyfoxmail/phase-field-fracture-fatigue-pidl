"""Run the isolated S04-E040 state-referenced feasible-damage arm on a GPU.

This runner deliberately does not call the standard fit loop: that loop builds
the irreversibility penalty even when its multiplier is zero.  E040 instead
uses an opt-in alpha constraint and an elastic-plus-damage-only objective while
preserving the standard fresh RPROP hyperparameters and stopping arithmetic.

It is a producer-only program.  It refuses CPU execution and writes an atomic
accepted-state record after each accepted physical step.  A failed/capped step
is terminal for this arm and never advances the accepted pointer.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "source"), str(ROOT / "SENS_tensile")]

from construct_model import construct_model
from compute_energy import compute_energy, get_psi_plus_per_elem, gradients, strain_energy_with_split
from fatigue_history import compute_fatigue_degrad, update_fatigue_history
from fit import EarlyStopping
from feasible_damage import (
    DEFAULT_RAW_INCREMENT_SCALE,
    StateReferencedDamageMap,
    compute_elastic_damage_energy,
    freeze_damage_state,
)
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from optim import get_optimizer


FAT = dict(
    loading_type="cyclic",
    accum_type="carrara",
    degrad_type="asymptotic",
    alpha_T=0.5,
)
IRR = dict(enable=True, mode="fem_gp_tri3")
REDUCTION = dict(enable=True, mode="fem_gp_tri3_g_mean")
FACTORS = (0.25, 0.5, 0.75, 1.0, 0.0)
WEIGHT_DECAY = 1.0e-5
MIN_DELTA = 5.0e-7
PATIENCE = 10
EPS = np.finfo(float).eps
FINALIZATION_RESERVE_SECONDS = 15.0


class StepCap(RuntimeError):
    """The fixed wall-time budget ended before a normal stop."""


class StateContractError(RuntimeError):
    """An accepted-state or same-forward invariant was violated."""


@dataclass
class AcceptedState:
    commit_id: str
    history_alpha: torch.Tensor
    hist_fat: torch.Tensor
    psi_plus_prev: torch.Tensor
    q_ref: torch.Tensor
    parent_commit_id: str | None


@dataclass
class FinalCache:
    forward_id: int
    u: torch.Tensor
    v: torch.Tensor
    d: torch.Tensor
    q_raw: torch.Tensor
    e_el: torch.Tensor
    e_d: torch.Tensor
    e_irr_shadow: torch.Tensor
    strain_xx: torch.Tensor
    strain_yy: torch.Tensor
    strain_xy: torch.Tensor
    raw_psi: torch.Tensor
    active_driver: torch.Tensor
    trial_A: torch.Tensor
    trial_f: torch.Tensor


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fsync_directory(path: Path) -> None:
    """Persist a completed rename on POSIX filesystems used by the producer."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json_durable(path: Path, value: Any) -> None:
    rendered = json.dumps(value, indent=2, allow_nan=False) + "\n"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    write_json_durable(tmp, value)
    os.replace(tmp, path)
    fsync_directory(path.parent)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def publish_file(tmp_path: Path, final_path: Path) -> None:
    require(tmp_path.is_file(), f"missing staged file: {tmp_path}")
    require(not final_path.exists(), f"final path already exists: {final_path}")
    os.replace(tmp_path, final_path)
    fsync_directory(final_path.parent)


def publish_directory(tmp_path: Path, final_path: Path) -> None:
    require(tmp_path.is_dir(), f"missing staged directory: {tmp_path}")
    require(not final_path.exists(), f"final directory already exists: {final_path}")
    os.replace(tmp_path, final_path)
    fsync_directory(final_path.parent)


def load_torch(path: Path, device: str = "cuda") -> Any:
    return torch.load(path, map_location=device, weights_only=False)


def clone_state_dict(net: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {name: value.detach().clone() for name, value in net.state_dict().items()}


def state_dict_equal(
    first: dict[str, torch.Tensor], second: dict[str, torch.Tensor]
) -> bool:
    return first.keys() == second.keys() and all(
        torch.equal(first[name], second[name]) for name in first
    )


def tensor_sha256(value: torch.Tensor) -> str:
    array = value.detach().contiguous().cpu().numpy()
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode())
    digest.update(repr(array.shape).encode())
    digest.update(array.tobytes())
    return digest.hexdigest()


def state_dict_sha256(net: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in net.state_dict().items():
        digest.update(name.encode())
        digest.update(tensor_sha256(value).encode())
    return digest.hexdigest()


def mesh_hash(inp: torch.Tensor, conn: torch.Tensor, area: torch.Tensor) -> str:
    digest = hashlib.sha256()
    for name, value in (("xy", inp), ("triangles", conn), ("area", area)):
        digest.update(name.encode())
        digest.update(tensor_sha256(value).encode())
    return digest.hexdigest()


def all_finite(*values: torch.Tensor) -> bool:
    return all(bool(torch.isfinite(value).all()) for value in values)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StateContractError(message)


def lumped_weights(conn: torch.Tensor, area: torch.Tensor, n_nodes: int) -> torch.Tensor:
    weights = torch.zeros(n_nodes, device=area.device, dtype=area.dtype)
    for corner in range(3):
        weights.index_add_(0, conn[:, corner], area / 3.0)
    require(bool((weights > 0).all()), "non-positive nodal lumped weight")
    return (weights / weights.sum()).detach()


def tri3_values(nodal: torch.Tensor, conn: torch.Tensor) -> torch.Tensor:
    """Linear triangular values at the project's three degree-two points."""
    vertex = nodal[conn]
    return torch.stack(
        (
            4.0 * vertex[:, 0] + vertex[:, 1] + vertex[:, 2],
            vertex[:, 0] + 4.0 * vertex[:, 1] + vertex[:, 2],
            vertex[:, 0] + vertex[:, 1] + 4.0 * vertex[:, 2],
        ),
        dim=1,
    ) / 6.0


def field_route_hash(field: FieldComputation) -> str:
    route = dict(
        raw_damage_input="FieldComputation.net_output[:,2]",
        williams_enabled=bool(field.williams_enabled),
        symmetry_prior=bool(field.symmetry_prior),
        local_patch_enabled=bool(field.local_patch_enabled),
        ansatz_enabled=bool(field.ansatz_enabled),
        exact_bc_enabled=bool(field.exact_bc_enabled),
    )
    return hashlib.sha256(
        json.dumps(route, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class LegacyRawCapture:
    """Capture the exact raw tensor passed into the legacy alpha callable."""

    def __init__(self, legacy_constraint: Callable[[torch.Tensor], torch.Tensor]):
        self.legacy_constraint = legacy_constraint
        self.calls = 0
        self.raw: torch.Tensor | None = None

    def __call__(self, raw: torch.Tensor) -> torch.Tensor:
        self.calls += 1
        self.raw = raw.detach().clone()
        return self.legacy_constraint(raw)


def construct_standard_field(device: str) -> tuple[Any, Any, torch.nn.Module, FieldComputation, torch.Tensor, torch.Tensor, torch.Tensor]:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], device=device)
    pff, mat, net = construct_model(
        dict(PFF_model="AT1", se_split="volumetric", tol_ir=5e-3, residual_stiffness=0.0),
        dict(mat_E=1.0, mat_nu=0.3, w1=1.0, l0=0.01),
        dict(hidden_layers=8, neurons=400, seed=1, activation="TrainableReLU", init_coeff=1.0, compile=False),
        extrema,
        device,
    )
    field = FieldComputation(
        net.to(device),
        extrema,
        torch.tensor(0.0, device=device),
        torch.tensor([np.pi / 2], device=device),
        l0=0.01,
    )
    inp, conn, area, _ = prep_input_data(
        mat,
        pff,
        dict(x_init=[-0.5], y_init=[0.0], L_crack=[0.5], angle_crack=[0.0]),
        dict(gradient_type="numerical"),
        str(ROOT / "SENS_tensile" / "meshed_geom_fem_soft_hist0.msh"),
        device,
    )
    require(inp.shape == (45591, 2), f"unexpected node mesh {tuple(inp.shape)}")
    require(conn.shape == (90000, 3), f"unexpected element mesh {tuple(conn.shape)}")
    return pff, mat, net, field, inp, conn, area


def frozen_digest(
    history_alpha: torch.Tensor,
    hist_fat: torch.Tensor,
    psi_plus_prev: torch.Tensor,
    q_ref: torch.Tensor,
    f_fixed: torch.Tensor,
) -> str:
    digest = hashlib.sha256()
    for name, value in (
        ("h", history_alpha),
        ("A", hist_fat),
        ("p", psi_plus_prev),
        ("qref", q_ref),
        ("f", f_fixed),
    ):
        digest.update(name.encode())
        digest.update(tensor_sha256(value).encode())
    return digest.hexdigest()


def assert_frozen(
    original: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
    current: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
    label: str,
) -> None:
    labels = ("history_alpha", "hist_fat", "psi_plus_prev", "q_ref", "f_fixed")
    for name, before, after in zip(labels, original, current, strict=True):
        require(torch.equal(before, after), f"{label}: frozen {name} changed")


def check_state_shapes(
    state: AcceptedState,
    n_nodes: int,
    n_elem: int,
    route_digest: str,
    expected_mesh_hash: str,
    record: dict[str, Any] | None = None,
) -> None:
    h, A, p, q_ref = (
        state.history_alpha,
        state.hist_fat,
        state.psi_plus_prev,
        state.q_ref,
    )
    require(h.shape == q_ref.shape == (n_nodes,), "state nodal shape mismatch")
    require(A.shape == p.shape == (n_elem,), "state element shape mismatch")
    require(h.device == q_ref.device == A.device == p.device, "state device mismatch")
    require(h.dtype == q_ref.dtype == A.dtype == p.dtype, "state dtype mismatch")
    require(not h.requires_grad and not A.requires_grad and not p.requires_grad and not q_ref.requires_grad,
            "accepted-state tensors must be detached")
    require(all_finite(h, A, p, q_ref), "state has a non-finite tensor")
    require(bool(((h >= 0) & (h <= 1)).all()), "history_alpha outside [0,1]")
    require(bool((A >= 0).all()), "fatigue accumulation below zero")
    require(bool((p >= 0).all()), "previous active driver below zero")
    if record is not None:
        require(record["mesh_order_hash"] == expected_mesh_hash, "record mesh hash mismatch")
        require(record["field_route_hash"] == route_digest, "record field route hash mismatch")


def damage_branch_metrics(
    q_raw: torch.Tensor,
    history_alpha: torch.Tensor,
    q_ref: torch.Tensor,
    weights: torch.Tensor,
) -> dict[str, float | None]:
    z = q_raw - q_ref
    free = history_alpha < 1.0
    mass = weights[free].sum()
    if float(mass) == 0.0:
        return dict(
            free_mass=0.0,
            dead_free_mass_fraction=None,
            kink_free_mass_fraction=None,
            open_free_mass_fraction=None,
            normalized_one_sided_damage_jacobian=None,
            raw_increment_min=float(z.min()),
            raw_increment_max=float(z.max()),
        )
    def fraction(mask: torch.Tensor) -> float:
        return float(weights[mask].sum() / mass)

    dead = free & (z < 0)
    kink = free & (z == 0)
    open_branch = free & (z > 0)
    active = free & (z >= 0)
    scale = q_raw.new_tensor(DEFAULT_RAW_INCREMENT_SCALE)
    denom = scale * torch.sum(weights * (1.0 - history_alpha) * free)
    jac = scale * (1.0 - history_alpha) / (1.0 + scale * torch.relu(z)).square()
    ratio = None if float(denom) == 0.0 else float(torch.sum(weights * jac * active) / denom)
    return dict(
        free_mass=float(mass),
        dead_free_mass_fraction=fraction(dead),
        kink_free_mass_fraction=fraction(kink),
        open_free_mass_fraction=fraction(open_branch),
        normalized_one_sided_damage_jacobian=ratio,
        raw_increment_min=float(z.min()),
        raw_increment_max=float(z.max()),
    )


def relative_change(current: float, previous: float) -> float:
    return abs(current - previous) / (abs(previous) + EPS)


def full_step_deadline(
    total_deadline: float,
    step_seconds: float,
    now: float,
) -> float | None:
    """Return a full-step deadline without reserving finalization twice.

    ``step_seconds`` already includes the protected finalization reserve inside
    :func:`run_step`. Callers provide the time after durable-state restoration,
    so a non-``None`` result leaves one complete physical-step budget without
    crossing the runner-wide deadline.
    """
    if total_deadline - now < step_seconds:
        return None
    return min(now + step_seconds, total_deadline)


def flat_gradient_metrics(
    named: list[tuple[str, torch.nn.Parameter]],
    physical_grads: Iterable[torch.Tensor | None],
) -> dict[str, Any]:
    physical_parts, l2_parts, total_parts, actual_parts = [], [], [], []
    output_weight: dict[str, torch.Tensor] = {}
    for (name, parameter), physical in zip(named, physical_grads, strict=True):
        physical_value = torch.zeros_like(parameter) if physical is None else physical.detach()
        l2_value = 2.0 * WEIGHT_DECAY * parameter.detach() if "weight" in name else torch.zeros_like(parameter)
        total_value = physical_value + l2_value
        actual_value = torch.zeros_like(parameter) if parameter.grad is None else parameter.grad.detach()
        physical_parts.append(physical_value.reshape(-1))
        l2_parts.append(l2_value.reshape(-1))
        total_parts.append(total_value.reshape(-1))
        actual_parts.append(actual_value.reshape(-1))
        if name == "output_layer.weight":
            output_weight = dict(physical=physical_value[2], l2=l2_value[2], total=total_value[2], actual=actual_value[2])
    physical_flat = torch.cat(physical_parts)
    l2_flat = torch.cat(l2_parts)
    total_flat = torch.cat(total_parts)
    actual_flat = torch.cat(actual_parts)

    def summarize(physical: torch.Tensor, l2: torch.Tensor, total: torch.Tensor, actual: torch.Tensor) -> dict[str, float]:
        denom = physical.norm() * l2.norm()
        cosine = 0.0 if float(denom) == 0.0 else float(torch.dot(physical, l2) / denom)
        nonzero = physical != 0
        return dict(
            physical_l2=float(physical.norm()),
            regularizer_l2=float(l2.norm()),
            combined_l2=float(total.norm()),
            actual_l2=float(actual.norm()),
            physical_regularizer_cosine=cosine,
            sign_changed_fraction=float((physical.sign() != total.sign()).float().mean()),
            nonzero_physical_reversed_fraction=(
                float(((physical[nonzero] * total[nonzero]) < 0).float().mean())
                if bool(nonzero.any()) else 0.0
            ),
            actual_minus_combined_max_abs=float((actual - total).abs().max()),
        )

    result: dict[str, Any] = dict(full=summarize(physical_flat, l2_flat, total_flat, actual_flat))
    if output_weight:
        result["third_head_output_weight_row"] = summarize(**output_weight)
    return result


def field_residual_metrics(
    cache: FinalCache,
    history_alpha: torch.Tensor,
    inp: torch.Tensor,
    conn: torch.Tensor,
    area: torch.Tensor,
    weights: torch.Tensor,
    mat: Any,
    pff: Any,
    f_fixed: torch.Tensor,
) -> dict[str, float | None]:
    """Independent nodal residual report; never an acceptance condition."""
    u = cache.u.detach().requires_grad_()
    v = cache.v.detach().requires_grad_()
    d = cache.d.detach().requires_grad_()
    e_el, e_d = compute_elastic_damage_energy(inp, u, v, d, mat, pff, area, conn, f_fatigue=f_fixed)
    ru, rv, rd = torch.autograd.grad(e_el + e_d, (u, v, d), allow_unused=False)
    free_uv = (inp[:, 1] > -0.5 + 1e-7) & (inp[:, 1] < 0.5 - 1e-7)
    projected = d.detach() - torch.maximum(
        history_alpha,
        torch.minimum(torch.ones_like(d), d.detach() - rd.detach() / weights),
    )
    return dict(
        field_damage_projected_inf=float(projected.abs().max()),
        free_uv_residual_inf=float(torch.maximum(ru[free_uv].abs().max(), rv[free_uv].abs().max())),
    )


def physical_fields(
    field: FieldComputation,
    mapping: StateReferencedDamageMap,
    history_alpha: torch.Tensor,
    hist_fat: torch.Tensor,
    psi_plus_prev: torch.Tensor,
    f_fixed: torch.Tensor,
    inp: torch.Tensor,
    conn: torch.Tensor,
    area: torch.Tensor,
    mat: Any,
    pff: Any,
) -> FinalCache:
    """Create exactly one result cache from a field forward after RPROP stops."""
    with torch.no_grad():
        u, v, d = field.fieldCalculation(inp)
        snapshot = mapping.latest()
        require(snapshot.forward_id == mapping.last_forward_id, "stale map forward id")
        require(torch.equal(snapshot.damage, d), "final mapped damage not from final forward")
        q_raw = snapshot.raw_damage
        e_el, e_d = compute_elastic_damage_energy(inp, u, v, d, mat, pff, area, conn, f_fatigue=f_fixed)
        _, _, e_irr_shadow = compute_energy(
            inp,
            u,
            v,
            d,
            history_alpha,
            mat,
            pff,
            area,
            conn,
            f_fatigue=f_fixed,
            irreversibility_penalty_cfg=IRR,
        )
        strain_xx, strain_yy, strain_xy, _, _ = gradients(inp, u, v, d, area, conn)
        alpha_elem = (d[conn[:, 0]] + d[conn[:, 1]] + d[conn[:, 2]]) / 3.0
        _, raw_psi = strain_energy_with_split(strain_xx, strain_yy, strain_xy, alpha_elem, mat, pff)
        active = get_psi_plus_per_elem(
            inp,
            u,
            v,
            d,
            mat,
            pff,
            area,
            conn,
            history_driver_reduction_dict=REDUCTION,
        )
        trial_A = update_fatigue_history(hist_fat, active, psi_plus_prev, FAT)
        trial_f = compute_fatigue_degrad(trial_A, FAT)
        return FinalCache(
            forward_id=snapshot.forward_id,
            u=u.detach().clone(),
            v=v.detach().clone(),
            d=d.detach().clone(),
            q_raw=q_raw.detach().clone(),
            e_el=e_el.detach().clone(),
            e_d=e_d.detach().clone(),
            e_irr_shadow=e_irr_shadow.detach().clone(),
            strain_xx=strain_xx.detach().clone(),
            strain_yy=strain_yy.detach().clone(),
            strain_xy=strain_xy.detach().clone(),
            raw_psi=raw_psi.detach().clone(),
            active_driver=active.detach().clone(),
            trial_A=trial_A.detach().clone(),
            trial_f=trial_f.detach().clone(),
        )


def candidate_metrics(
    cache: FinalCache,
    history_alpha: torch.Tensor,
    q_ref: torch.Tensor,
    weights: torch.Tensor,
    conn: torch.Tensor,
    net: torch.nn.Module,
) -> dict[str, Any]:
    delta = cache.d - history_alpha
    gp_delta = tri3_values(delta, conn)
    gp_upper = tri3_values(1.0 - cache.d, conn)
    metrics: dict[str, Any] = dict(
        E_el=float(cache.e_el),
        E_d=float(cache.e_d),
        E_noirr=float(cache.e_el + cache.e_d),
        shadow_E_irr=float(cache.e_irr_shadow),
        weighted_L2=float(
            WEIGHT_DECAY * sum(parameter.square().sum() for name, parameter in net.named_parameters() if "weight" in name)
        ),
        d_min=float(cache.d.min()),
        d_max=float(cache.d.max()),
        min_damage_increment=float(delta.min()),
        max_damage_increment=float(delta.max()),
        min_tri3_damage_increment=float(gp_delta.min()),
        min_tri3_upper_slack=float(gp_upper.min()),
        q_ref_max_abs=float(q_ref.abs().max()),
        q_raw_max_abs=float(cache.q_raw.abs().max()),
    )
    metrics.update(damage_branch_metrics(cache.q_raw, history_alpha, q_ref, weights))
    return metrics


def write_fields(
    folder: Path,
    cache: FinalCache,
    history_alpha: torch.Tensor,
    hist_fat: torch.Tensor,
    psi_plus_prev: torch.Tensor,
    q_ref: torch.Tensor,
    f_fixed: torch.Tensor,
) -> None:
    with (folder / "fields.npz").open("wb") as handle:
        np.savez_compressed(
            handle,
            u=cache.u.cpu().numpy(),
            v=cache.v.cpu().numpy(),
            d=cache.d.cpu().numpy(),
            history_d=history_alpha.cpu().numpy(),
            history_A=hist_fat.cpu().numpy(),
            history_prev=psi_plus_prev.cpu().numpy(),
            f_solve=f_fixed.cpu().numpy(),
            strain_xx=cache.strain_xx.cpu().numpy(),
            strain_yy=cache.strain_yy.cpu().numpy(),
            strain_xy=cache.strain_xy.cpu().numpy(),
            raw_psi=cache.raw_psi.cpu().numpy(),
            active_driver=cache.active_driver.cpu().numpy(),
            trial_A=cache.trial_A.cpu().numpy(),
            trial_f=cache.trial_f.cpu().numpy(),
            q_raw=cache.q_raw.cpu().numpy(),
            q_ref=q_ref.cpu().numpy(),
        )
        handle.flush()
        os.fsync(handle.fileno())


def write_torch_durable(path: Path, value: Any) -> None:
    with path.open("wb") as handle:
        torch.save(value, handle)
        handle.flush()
        os.fsync(handle.fileno())


def reload_audit(
    record_path: Path,
    template_net: torch.nn.Module,
    inp: torch.Tensor,
    expected_mesh_hash: str,
    expected_route_hash: str,
    device: str,
) -> dict[str, Any]:
    """Reload a staged state record and test its declared start invariant."""
    record = load_torch(record_path, device)
    require(record["mesh_order_hash"] == expected_mesh_hash, "reload mesh hash mismatch")
    require(record["field_route_hash"] == expected_route_hash, "reload route hash mismatch")
    net = copy.deepcopy(template_net).to(device)
    net.load_state_dict(record["network_state_dict"], strict=True)
    field = FieldComputation(
        net,
        torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], device=device),
        torch.tensor(0.0, device=device),
        torch.tensor([np.pi / 2], device=device),
        l0=0.01,
    )
    mapping = StateReferencedDamageMap(record["history_alpha"], record["q_ref"])
    field.alpha_constraint = mapping
    with torch.no_grad():
        _, _, d_reload = field.fieldCalculation(inp)
        snapshot = mapping.latest()
    q_reload = snapshot.raw_damage
    q_ref = record["q_ref"]
    h = record["history_alpha"]
    q_error = float((q_reload - q_ref).abs().max())
    d_error = float((d_reload - h).abs().max())
    q_tol = float(32.0 * torch.finfo(q_ref.dtype).eps * max(1.0, float(q_ref.abs().max())))
    d_tol = float(16.0 * torch.finfo(h.dtype).eps)
    passed = q_error <= q_tol and d_error <= d_tol
    return dict(
        passed=passed,
        q_reload_max_abs=q_error,
        d_reload_max_abs=d_error,
        q_reload_tolerance=q_tol,
        d_reload_tolerance=d_tol,
        q_reload_bitwise=torch.equal(q_reload, q_ref),
        d_reload_bitwise=torch.equal(d_reload, h),
        same_forward_id=snapshot.forward_id == mapping.last_forward_id,
    )


def stage_accepted_state_record(
    records_dir: Path,
    net: torch.nn.Module,
    state: AcceptedState,
    mesh_order_hash: str,
    route_hash: str,
    inp: torch.Tensor,
    device: str,
    deadline: float,
) -> tuple[Path, Path, dict[str, Any], str]:
    """Stage, reload-audit, and hash a record without advancing the pointer."""
    records_dir.mkdir(parents=True, exist_ok=True)
    final_path = records_dir / f"{state.commit_id}.pt"
    require(not final_path.exists(), f"record already exists: {final_path.name}")
    payload = dict(
        commit_id=state.commit_id,
        parent_commit_id=state.parent_commit_id,
        network_state_dict=clone_state_dict(net),
        history_alpha=state.history_alpha.detach().clone(),
        hist_fat=state.hist_fat.detach().clone(),
        psi_plus_prev=state.psi_plus_prev.detach().clone(),
        q_ref=state.q_ref.detach().clone(),
        mesh_order_hash=mesh_order_hash,
        field_route_hash=route_hash,
        dtype=str(state.history_alpha.dtype),
    )
    tmp_path = records_dir / f".{state.commit_id}.{uuid.uuid4().hex}.pt.tmp"
    try:
        write_torch_durable(tmp_path, payload)
        if time.monotonic() >= deadline:
            raise StepCap("wall cap before staged-record reload audit")
        audit = reload_audit(tmp_path, net, inp, mesh_order_hash, route_hash, device)
        if not audit["passed"]:
            raise StateContractError(f"record reload audit failed: {audit}")
        require(
            audit["q_reload_bitwise"],
            "staged record reload q(theta) != q_ref bitwise",
        )
        require(
            audit["d_reload_bitwise"],
            "staged record reload d(theta) != history_alpha bitwise",
        )
        staged = load_torch(tmp_path, device)
        require(state_dict_equal(payload["network_state_dict"], staged["network_state_dict"]), "staged network changed")
        for name in ("history_alpha", "hist_fat", "psi_plus_prev", "q_ref"):
            require(torch.equal(payload[name], staged[name]), f"staged {name} changed")
        if time.monotonic() >= deadline:
            raise StepCap("wall cap after staged-record reload audit")
        return tmp_path, final_path, audit, sha256_file(tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def write_artifact_manifest(folder: Path, artifact_names: list[str]) -> tuple[Path, str]:
    """Hash every staged evidence artifact before it can be pointer-referenced."""
    entries: list[dict[str, Any]] = []
    for name in artifact_names:
        candidate = folder / name
        require(candidate.is_file(), f"missing staged artifact: {name}")
        entries.append(
            dict(name=name, bytes=candidate.stat().st_size, sha256=sha256_file(candidate))
        )
    manifest_path = folder / "artifact_manifest.json"
    write_json_durable(
        manifest_path,
        dict(schema="S04-E040-artifact-manifest-v1", artifacts=entries),
    )
    return manifest_path, sha256_file(manifest_path)


def verify_artifact_manifest(folder: Path, manifest_file: str, expected_sha256: str) -> None:
    manifest_path = folder / manifest_file
    require(manifest_path.is_file(), f"missing artifact manifest: {manifest_path}")
    require(sha256_file(manifest_path) == expected_sha256, "artifact manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema") == "S04-E040-artifact-manifest-v1", "artifact manifest schema mismatch")
    artifacts = manifest.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "artifact manifest is empty")
    seen: set[str] = set()
    for entry in artifacts:
        require(isinstance(entry, dict), "malformed artifact entry")
        name = entry.get("name")
        require(isinstance(name, str) and name not in seen and "/" not in name, "invalid artifact name")
        seen.add(name)
        candidate = folder / name
        require(candidate.is_file(), f"manifest artifact missing: {name}")
        require(candidate.stat().st_size == entry.get("bytes"), f"artifact size mismatch: {name}")
        require(sha256_file(candidate) == entry.get("sha256"), f"artifact hash mismatch: {name}")


def stage_state_index(
    indices_dir: Path,
    *,
    state: AcceptedState,
    parent_index_file: str | None,
    record_file: str,
    record_sha256: str,
    evidence_dir: str,
    artifact_manifest_file: str,
    artifact_manifest_sha256: str,
    mesh_order_hash: str,
    route_hash: str,
    phase: dict[str, Any] | None,
) -> tuple[Path, Path, str]:
    """Stage the immutable index that binds state, evidence, and parent lineage."""
    indices_dir.mkdir(parents=True, exist_ok=True)
    final_path = indices_dir / f"{state.commit_id}.json"
    require(not final_path.exists(), f"state index already exists: {final_path.name}")
    payload = dict(
        schema="S04-E040-state-index-v1",
        state_commit_id=state.commit_id,
        parent_state_commit_id=state.parent_commit_id,
        parent_index_file=parent_index_file,
        record_file=record_file,
        record_sha256=record_sha256,
        evidence_dir=evidence_dir,
        artifact_manifest_file=artifact_manifest_file,
        artifact_manifest_sha256=artifact_manifest_sha256,
        mesh_order_hash=mesh_order_hash,
        field_route_hash=route_hash,
        phase=phase,
    )
    tmp_path = indices_dir / f".{state.commit_id}.{uuid.uuid4().hex}.json.tmp"
    write_json_durable(tmp_path, payload)
    return tmp_path, final_path, sha256_file(tmp_path)


def validate_committed_bundle(
    *,
    arm_dir: Path,
    records_dir: Path,
    indices_dir: Path,
    pointer: dict[str, Any],
    expected_mesh_hash: str,
    expected_route_hash: str,
    device: str,
) -> dict[str, Any]:
    """Validate the exact bundle made authoritative by an accepted-state pointer."""
    required = (
        "accepted_commit_id", "parent_commit_id", "record_file", "record_sha256",
        "state_index_file", "state_index_sha256", "parent_index_file", "mesh_order_hash", "field_route_hash",
    )
    for key in required:
        require(key in pointer, f"accepted pointer missing {key}")
    require(pointer["mesh_order_hash"] == expected_mesh_hash, "pointer mesh hash mismatch")
    require(pointer["field_route_hash"] == expected_route_hash, "pointer route hash mismatch")
    index_file = pointer["state_index_file"]
    require(isinstance(index_file, str) and "/" not in index_file, "invalid pointer index filename")
    index_path = indices_dir / index_file
    require(index_path.is_file(), "pointer index file missing")
    require(sha256_file(index_path) == pointer["state_index_sha256"], "pointer index hash mismatch")
    index = json.loads(index_path.read_text())
    require(index.get("schema") == "S04-E040-state-index-v1", "state index schema mismatch")
    require(index.get("state_commit_id") == pointer["accepted_commit_id"], "pointer/index commit mismatch")
    require(index.get("parent_state_commit_id") == pointer["parent_commit_id"], "pointer/index parent mismatch")
    require(index.get("parent_index_file") == pointer["parent_index_file"], "pointer/index parent-index mismatch")
    require(index.get("record_file") == pointer["record_file"], "pointer/index record mismatch")
    require(index.get("record_sha256") == pointer["record_sha256"], "pointer/index record hash mismatch")
    require(index.get("mesh_order_hash") == expected_mesh_hash, "index mesh hash mismatch")
    require(index.get("field_route_hash") == expected_route_hash, "index route hash mismatch")
    record_file = pointer["record_file"]
    require(isinstance(record_file, str) and "/" not in record_file, "invalid pointer record filename")
    record_path = records_dir / record_file
    require(record_path.is_file(), "pointer record file missing")
    require(sha256_file(record_path) == pointer["record_sha256"], "pointer record hash mismatch")
    evidence_dir = index.get("evidence_dir")
    require(isinstance(evidence_dir, str) and "/" not in evidence_dir, "invalid evidence directory")
    evidence_path = arm_dir / evidence_dir
    require(evidence_path.is_dir(), "pointer evidence directory missing")
    manifest_file = index.get("artifact_manifest_file")
    manifest_sha = index.get("artifact_manifest_sha256")
    require(isinstance(manifest_file, str) and isinstance(manifest_sha, str), "index manifest metadata missing")
    verify_artifact_manifest(evidence_path, manifest_file, manifest_sha)
    record = load_torch(record_path, device)
    require(record.get("commit_id") == pointer["accepted_commit_id"], "pointer record commit mismatch")
    require(record.get("parent_commit_id") == pointer["parent_commit_id"], "pointer record parent mismatch")
    require(record.get("mesh_order_hash") == expected_mesh_hash, "record mesh hash mismatch")
    require(record.get("field_route_hash") == expected_route_hash, "record route hash mismatch")
    return index


def publish_pointer_last(
    *,
    pointer_path: Path,
    arm_dir: Path,
    records_dir: Path,
    indices_dir: Path,
    state: AcceptedState,
    final_record_path: Path,
    record_sha256: str,
    final_index_path: Path,
    index_sha256: str,
    expected_mesh_hash: str,
    expected_route_hash: str,
    device: str,
    deadline: float,
) -> dict[str, Any]:
    """Publish the sole acceptance authority after all state/evidence files exist."""
    if pointer_path.exists():
        previous = json.loads(pointer_path.read_text())
        require(state.parent_commit_id is not None, "initial state cannot replace an existing pointer")
        require(previous.get("accepted_commit_id") == state.parent_commit_id, "accepted pointer parent drift")
        parent_index_file = previous.get("state_index_file")
        require(isinstance(parent_index_file, str), "previous pointer lacks state index")
        validate_committed_bundle(
            arm_dir=arm_dir,
            records_dir=records_dir,
            indices_dir=indices_dir,
            pointer=previous,
            expected_mesh_hash=expected_mesh_hash,
            expected_route_hash=expected_route_hash,
            device=device,
        )
    else:
        previous = None
        require(state.parent_commit_id is None, "non-initial state lacks accepted pointer")
        parent_index_file = None
    if time.monotonic() >= deadline:
        raise StepCap("wall cap before accepted-state pointer publication")
    payload = dict(
        schema="S04-E040-accepted-state-pointer-v1",
        accepted_commit_id=state.commit_id,
        parent_commit_id=state.parent_commit_id,
        parent_index_file=parent_index_file,
        record_file=final_record_path.name,
        record_sha256=record_sha256,
        state_index_file=final_index_path.name,
        state_index_sha256=index_sha256,
        mesh_order_hash=expected_mesh_hash,
        field_route_hash=expected_route_hash,
    )
    # This must happen before the authoritative pointer changes.  A post-write
    # readback remains necessary, but it cannot be the first time a malformed
    # record/index/evidence bundle is discovered.
    validate_committed_bundle(
        arm_dir=arm_dir,
        records_dir=records_dir,
        indices_dir=indices_dir,
        pointer=payload,
        expected_mesh_hash=expected_mesh_hash,
        expected_route_hash=expected_route_hash,
        device=device,
    )
    if time.monotonic() >= deadline:
        raise StepCap("wall cap after accepted-state bundle prevalidation")
    try:
        atomic_json(pointer_path, payload)
    except Exception as publication_error:
        # A failure after os.replace can be ambiguous.  The new bundle counts as
        # accepted only if the pointer can be reread and fully validates.
        try:
            observed = json.loads(pointer_path.read_text())
            if observed != payload:
                raise StateContractError("pointer did not publish the intended bundle")
            validate_committed_bundle(
                arm_dir=arm_dir,
                records_dir=records_dir,
                indices_dir=indices_dir,
                pointer=observed,
                expected_mesh_hash=expected_mesh_hash,
                expected_route_hash=expected_route_hash,
                device=device,
            )
            return dict(recovered_after_publication_error=True, error=repr(publication_error))
        except Exception as verification_error:
            raise StateContractError(
                f"accepted-state pointer publication failed: {publication_error!r}; "
                f"post-error verification failed: {verification_error!r}"
            ) from publication_error
    observed = json.loads(pointer_path.read_text())
    require(observed == payload, "accepted pointer readback mismatch")
    validate_committed_bundle(
        arm_dir=arm_dir,
        records_dir=records_dir,
        indices_dir=indices_dir,
        pointer=observed,
        expected_mesh_hash=expected_mesh_hash,
        expected_route_hash=expected_route_hash,
        device=device,
    )
    return dict(recovered_after_publication_error=False)


def restore_accepted_state(
    pointer_path: Path,
    arm_dir: Path,
    records_dir: Path,
    indices_dir: Path,
    net: torch.nn.Module,
    expected_mesh_hash: str,
    expected_route_hash: str,
    device: str,
) -> tuple[AcceptedState, dict[str, Any]]:
    """Make the pointer-referenced record, rather than RAM, the next-step source."""
    pointer = json.loads(pointer_path.read_text())
    index = validate_committed_bundle(
        arm_dir=arm_dir,
        records_dir=records_dir,
        indices_dir=indices_dir,
        pointer=pointer,
        expected_mesh_hash=expected_mesh_hash,
        expected_route_hash=expected_route_hash,
        device=device,
    )
    record = load_torch(records_dir / pointer["record_file"], device)
    stored_network = record["network_state_dict"]
    net.load_state_dict(stored_network, strict=True)
    require(state_dict_equal(clone_state_dict(net), stored_network), "persisted network reload mismatch")
    state = AcceptedState(
        commit_id=pointer["accepted_commit_id"],
        history_alpha=record["history_alpha"].detach().clone(),
        hist_fat=record["hist_fat"].detach().clone(),
        psi_plus_prev=record["psi_plus_prev"].detach().clone(),
        q_ref=record["q_ref"].detach().clone(),
        parent_commit_id=record.get("parent_commit_id"),
    )
    record["state_index"] = index
    return state, record

def begin_map_check(
    field: FieldComputation,
    mapping: StateReferencedDamageMap,
    state: AcceptedState,
    inp: torch.Tensor,
) -> None:
    with torch.no_grad():
        _, _, d = field.fieldCalculation(inp)
        snapshot = mapping.latest()
    require(snapshot.forward_id == mapping.last_forward_id, "start map forward id mismatch")
    require(torch.equal(snapshot.raw_damage, state.q_ref), "start q(theta) != q_ref")
    require(torch.equal(d, state.history_alpha), "start d(theta) != history_alpha")


def direct_objective(
    field: FieldComputation,
    inp: torch.Tensor,
    conn: torch.Tensor,
    area: torch.Tensor,
    mat: Any,
    pff: Any,
    f_fixed: torch.Tensor,
    named: list[tuple[str, torch.nn.Parameter]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    u, v, d = field.fieldCalculation(inp)
    e_el, e_d = compute_elastic_damage_energy(inp, u, v, d, mat, pff, area, conn, f_fatigue=f_fixed)
    physical = e_el + e_d
    if not bool(torch.isfinite(physical)) or not bool(physical > 0):
        raise FloatingPointError(f"E_el + E_d must be finite and positive, got {float(physical.detach())}")
    l2 = WEIGHT_DECAY * sum(parameter.square().sum() for name, parameter in named if "weight" in name)
    loss = torch.log10(physical) + l2
    return loss, physical, e_el, e_d, u, v, d


def run_step(
    *,
    step: int,
    step_folder: Path,
    arm_dir: Path,
    state: AcceptedState,
    net: torch.nn.Module,
    field: FieldComputation,
    inp: torch.Tensor,
    conn: torch.Tensor,
    area: torch.Tensor,
    weights: torch.Tensor,
    mat: Any,
    pff: Any,
    deadline: float,
    max_updates: int,
    mesh_order_hash: str,
    route_hash: str,
    records_dir: Path,
    indices_dir: Path,
    pointer_path: Path,
    device: str,
    legacy_initial_gap: dict[str, float] | None,
) -> tuple[bool, AcceptedState, dict[str, Any]]:
    """Solve one physical step and publish its state only after its evidence bundle."""
    started = time.monotonic()
    require(not step_folder.exists(), f"canonical step directory already exists: {step_folder}")
    stage_folder = arm_dir / f".txn-{step_folder.name}.{uuid.uuid4().hex}.tmp"
    stage_folder.mkdir()

    trace: list[dict[str, Any]] = []
    plateau_pairs: list[dict[str, Any]] = []
    updates = 0
    initial_gradient: dict[str, Any] | None = None
    first_update: dict[str, Any] | None = None
    final_metrics: dict[str, Any] | None = None
    post_update: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    cache: FinalCache | None = None
    acceptance_reload_audit: dict[str, Any] | None = None
    pointer_publication: dict[str, Any] | None = None
    validation_finished: float | None = None
    optimization_started: float | None = None
    optimization_finished: float | None = None
    terminal_pre_update_loss: float | None = None
    previous_physical: float | None = None
    h: torch.Tensor | None = None
    A: torch.Tensor | None = None
    p: torch.Tensor | None = None
    q_ref: torch.Tensor | None = None
    f_fixed: torch.Tensor | None = None
    frozen_before: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor] | None = None
    frozen_start_digest: str | None = None
    mapping: StateReferencedDamageMap | None = None
    named: list[tuple[str, torch.nn.Parameter]] = []
    params: list[torch.nn.Parameter] = []
    termination = "not_started"
    setup_complete = False

    try:
        field.lmbda = torch.tensor(0.12 * FACTORS[(step - 1) % 5], device=device)
        require(field.net is net, "FieldComputation does not hold the accepted network object")
        check_state_shapes(state, len(inp), len(conn), route_hash, mesh_order_hash)
        f_fixed = compute_fatigue_degrad(state.hist_fat, FAT).detach().clone()
        require(all_finite(f_fixed), "fixed fatigue degradation is non-finite")
        require(bool(((f_fixed > 0) & (f_fixed <= 1)).all()), "fixed fatigue degradation outside (0,1]")
        h, q_ref = freeze_damage_state(state.history_alpha, state.q_ref)
        A = state.hist_fat.detach().clone()
        p = state.psi_plus_prev.detach().clone()
        frozen_before = tuple(value.detach().clone() for value in (h, A, p, q_ref, f_fixed))
        frozen_start_digest = frozen_digest(h, A, p, q_ref, f_fixed)
        mapping = StateReferencedDamageMap(h, q_ref)
        field.alpha_constraint = mapping
        begin_map_check(field, mapping, state, inp)
        named = list(net.named_parameters())
        params = [parameter for _, parameter in named]
        require(params, "accepted network has no trainable parameters")
        solver_params = list(field.parameters())
        require(
            len(solver_params) == len(params)
            and all(left is right for left, right in zip(solver_params, params, strict=True)),
            "E040 solver parameters diverge from standard FieldComputation parameters",
        )
        require(
            area.dtype == torch.float32
            and inp.dtype == area.dtype
            and all(parameter.dtype == area.dtype for parameter in params),
            "solver dtype differs from the standard field/mesh dtype",
        )
        require(
            all(parameter.device == area.device for parameter in params),
            "solver parameter device differs from the standard mesh device",
        )
        optimizer = get_optimizer(solver_params, "RPROP")
        require(len(optimizer.state) == 0, "RPROP must be freshly initialized per physical step")
        stop = EarlyStopping(tol_steps=PATIENCE, min_delta=MIN_DELTA, device=area.device)
        stop_previous = torch.tensor([0.0], device=area.device)
        setup_complete = True
        validation_finished = time.monotonic()
        optimization_started = validation_finished
        optimization_deadline = deadline - FINALIZATION_RESERVE_SECONDS
        if optimization_deadline <= time.monotonic():
            raise StepCap("wall cap reached before protected finalization reserve")

        for _ in range(max_updates):
            if time.monotonic() >= optimization_deadline:
                raise StepCap("wall cap reached before objective inside finalization reserve")
            optimizer.zero_grad(set_to_none=True)
            loss, physical, _, _, _, _, _ = direct_objective(
                field, inp, conn, area, mat, pff, f_fixed, named
            )
            current_loss = loss.detach()
            if updates == 0:
                physical_log = torch.log10(physical)
                physical_grads = torch.autograd.grad(
                    physical_log, params, allow_unused=True, retain_graph=True
                )
            loss.backward()
            if not all(
                parameter.grad is None or bool(torch.isfinite(parameter.grad).all())
                for parameter in params
            ):
                raise FloatingPointError("non-finite parameter gradient")
            if updates == 0:
                initial_gradient = flat_gradient_metrics(named, physical_grads)

            pre_loss = float(current_loss)
            pre_physical = float(physical.detach())
            terminal_pre_update_loss = pre_loss
            physical_delta = (
                None if previous_physical is None else relative_change(pre_physical, previous_physical)
            )
            prior_loss_for_trace = float(stop_previous)
            optimizer.step()
            updates += 1
            if time.monotonic() >= optimization_deadline:
                raise StepCap("wall cap reached after optimizer update inside finalization reserve")

            # This call, its tensor dtypes, and its placement after RPROP step
            # are deliberately identical to fit.EarlyStopping.
            delta_tensor = torch.abs(current_loss - stop_previous) / (
                torch.abs(stop_previous) + np.finfo(float).eps
            )
            loss_delta = float(delta_tensor)
            stop(current_loss, stop_previous)
            plateau_counter = int(stop.counter.detach().item())
            if bool(delta_tensor > stop.min_delta):
                plateau_pairs = []
            else:
                plateau_pairs.append(
                    dict(
                        update=updates,
                        pre_update_F=pre_loss,
                        previous_pre_update_F=prior_loss_for_trace,
                        relative_F_change=loss_delta,
                        pre_update_E_noirr=pre_physical,
                        previous_pre_update_E_noirr=previous_physical,
                        relative_E_noirr_change=physical_delta,
                    )
                )
                plateau_pairs = plateau_pairs[-PATIENCE:]
            if updates == 1 or updates % 25 == 0 or stop.early_stop:
                trace.append(
                    dict(
                        update=updates,
                        seconds=time.monotonic() - started,
                        pre_update_F=pre_loss,
                        pre_update_E_noirr=pre_physical,
                        relative_F_change=loss_delta,
                        relative_E_noirr_change=physical_delta,
                        plateau_counter=plateau_counter,
                    )
                )
            if updates == 1:
                assert_frozen(frozen_before, (h, A, p, q_ref, f_fixed), "after first update")
                with torch.no_grad():
                    _, _, d_after = field.fieldCalculation(inp)
                    q_after = mapping.latest().raw_damage
                    first_update = damage_branch_metrics(q_after, h, q_ref, weights)
                    first_update.update(
                        d_min=float(d_after.min()),
                        d_max=float(d_after.max()),
                        min_damage_increment=float((d_after - h).min()),
                        max_damage_increment=float((d_after - h).max()),
                    )
            if stop.early_stop:
                termination = "standard_relative_loss_plateau"
                break
            # Standard fit assigns this only after checking early_stop.
            stop_previous = current_loss
            previous_physical = pre_physical
        else:
            termination = "update_cap"
        optimization_finished = time.monotonic()
    except StepCap as exc:
        optimization_finished = time.monotonic()
        termination = "wall_cap_before_finalization"
        failure = dict(error=repr(exc), type=type(exc).__name__)
    except (FloatingPointError, StateContractError) as exc:
        optimization_finished = time.monotonic()
        termination = "invalid_objective_or_state"
        failure = dict(error=repr(exc), type=type(exc).__name__)
    except Exception as exc:  # preserve the terminal record; never advance a state after an error
        optimization_finished = time.monotonic()
        termination = "unexpected_error"
        failure = dict(error=repr(exc), type=type(exc).__name__)

    # A wall cap deliberately gets no new field forward: it reserves the cap
    # for a valid transaction, rather than manufacturing an over-cap trial.
    if (
        setup_complete
        and mapping is not None
        and h is not None
        and A is not None
        and p is not None
        and q_ref is not None
        and f_fixed is not None
        and termination in {"standard_relative_loss_plateau", "update_cap"}
    ):
        if time.monotonic() >= deadline:
            if termination == "standard_relative_loss_plateau":
                termination = "wall_cap_before_final_cache"
                failure = dict(error="hard step deadline reached before final field cache", type="StepCap")
        else:
            try:
                assert_frozen(frozen_before, (h, A, p, q_ref, f_fixed), "before final cache")
                theta_before_final = state_dict_sha256(net)
                cache = physical_fields(field, mapping, h, A, p, f_fixed, inp, conn, area, mat, pff)
                require(state_dict_sha256(net) == theta_before_final, "network changed during final field cache")
                require(
                    all_finite(
                        cache.u, cache.v, cache.d, cache.q_raw, cache.e_el, cache.e_d,
                        cache.e_irr_shadow, cache.strain_xx, cache.strain_yy, cache.strain_xy,
                        cache.raw_psi, cache.active_driver, cache.trial_A, cache.trial_f,
                    ),
                    "final cache has non-finite values",
                )
                require(bool(cache.e_el + cache.e_d > 0), "final E_el + E_d is not positive")
                final_metrics = candidate_metrics(cache, h, q_ref, weights, conn, net)
                try:
                    final_metrics.update(
                        field_residual_metrics(cache, h, inp, conn, area, weights, mat, pff, f_fixed)
                    )
                    final_metrics["field_residual_available"] = True
                except Exception as residual_exc:
                    final_metrics.update(
                        field_damage_projected_inf=None,
                        free_uv_residual_inf=None,
                        field_residual_available=False,
                        field_residual_error=repr(residual_exc),
                    )
                require(bool((cache.trial_A >= A).all()), "trial fatigue fell below accepted fatigue")
                require(
                    bool((cache.trial_f > 0).all()) and bool((cache.trial_f <= 1).all()),
                    "trial fatigue degradation invalid",
                )
                require(bool((cache.d >= h).all()) and bool((cache.d <= 1).all()), "nodal feasible bounds failed")
                require(bool((tri3_values(cache.d - h, conn) >= 0).all()), "TRI3 irreversibility failed")
                require(bool((tri3_values(1.0 - cache.d, conn) >= 0).all()), "TRI3 upper bound failed")
                assert_frozen(frozen_before, (h, A, p, q_ref, f_fixed), "after final cache")
                if time.monotonic() >= deadline and termination == "standard_relative_loss_plateau":
                    termination = "wall_cap_during_finalization"
                    failure = dict(error="hard step deadline reached after final field cache", type="StepCap")
            except Exception as exc:
                if failure is None:
                    termination = "invalid_final_cache"
                    failure = dict(error=repr(exc), type=type(exc).__name__)

    if cache is not None and final_metrics is not None:
        with torch.no_grad():
            final_F = float(torch.log10(cache.e_el + cache.e_d) + WEIGHT_DECAY * sum(
                parameter.square().sum() for name, parameter in named if "weight" in name
            ))
        final_E = float(cache.e_el + cache.e_d)
        post_update = dict(
            terminal_F=final_F,
            terminal_E_noirr=final_E,
            terminal_pre_update_F=terminal_pre_update_loss,
            relative_F_from_terminal_pre_update=(
                None if terminal_pre_update_loss is None else relative_change(final_F, terminal_pre_update_loss)
            ),
            relative_E_from_last_pre_update=(
                None if previous_physical is None else relative_change(final_E, previous_physical)
            ),
        )
        post_update["post_update_departure"] = bool(
            post_update["relative_F_from_terminal_pre_update"] is not None
            and post_update["relative_F_from_terminal_pre_update"] > MIN_DELTA
        )

    physical_stalled = bool(
        termination == "standard_relative_loss_plateau"
        and len(plateau_pairs) == PATIENCE
        and all(
            pair["relative_E_noirr_change"] is not None
            and pair["relative_E_noirr_change"] <= MIN_DELTA
            for pair in plateau_pairs
        )
    )
    if termination != "standard_relative_loss_plateau":
        terminal_classification = "no_normal_loss_plateau"
    elif physical_stalled and final_metrics is not None and (final_metrics["dead_free_mass_fraction"] or 0.0) > 0.0:
        terminal_classification = "loss_and_energy_plateau__negative_raw_damage_branch_present"
    elif physical_stalled:
        terminal_classification = "loss_and_energy_plateau__no_negative_raw_damage_branch"
    else:
        terminal_classification = "loss_plateau__physical_energy_changed"

    next_state = state
    staged_record_tmp: Path | None = None
    staged_record_final: Path | None = None
    staged_record_sha: str | None = None
    can_prepare_acceptance = (
        termination == "standard_relative_loss_plateau"
        and updates < max_updates
        and cache is not None
        and final_metrics is not None
        and failure is None
        and time.monotonic() < deadline
    )
    if can_prepare_acceptance and cache is not None:
        next_state = AcceptedState(
            commit_id=f"state_{step:03d}",
            history_alpha=cache.d.detach().clone(),
            hist_fat=cache.trial_A.detach().clone(),
            psi_plus_prev=cache.active_driver.detach().clone(),
            q_ref=cache.q_raw.detach().clone(),
            parent_commit_id=state.commit_id,
        )
        try:
            require(torch.equal(next_state.history_alpha, cache.d), "commit h is not final cached damage")
            require(torch.equal(next_state.hist_fat, cache.trial_A), "commit A is not final cached trial fatigue")
            require(torch.equal(next_state.psi_plus_prev, cache.active_driver), "commit previous driver is not final cached driver")
            require(torch.equal(next_state.q_ref, cache.q_raw), "commit q_ref is not final cached raw head")
            staged_record_tmp, staged_record_final, acceptance_reload_audit, staged_record_sha = stage_accepted_state_record(
                records_dir,
                net,
                next_state,
                mesh_order_hash,
                route_hash,
                inp,
                device,
                deadline,
            )
        except StepCap as exc:
            termination = "wall_cap_during_finalization"
            failure = dict(error=repr(exc), type=type(exc).__name__)
            next_state = state
            can_prepare_acceptance = False
        except Exception as exc:
            termination = "atomic_record_prepare_failed"
            failure = dict(error=repr(exc), type=type(exc).__name__)
            next_state = state
            can_prepare_acceptance = False

    artifact_receipt: dict[str, Any] = dict(
        arm="feasible_damage",
        step=step,
        cycle=(step - 1) // 5 + 1,
        substep=(step - 1) % 5 + 1,
        load=float(field.lmbda),
        # The immutable receipt exists before the pointer.  The pointer and its
        # hash-bound state index are the sole authority for an accepted state.
        accepted=None if can_prepare_acceptance else False,
        acceptance_status=("prepared_pointer_required" if can_prepare_acceptance else "unaccepted"),
        candidate_commit_id=(next_state.commit_id if can_prepare_acceptance else None),
        stop_reason=termination,
        termination_event=termination if termination == "standard_relative_loss_plateau" else None,
        stationarity_claim="not_assessed",
        updates=updates,
        max_updates=max_updates,
        elapsed_before_evidence_seconds=time.monotonic() - started,
        pre_solve_validation_seconds=(None if validation_finished is None else validation_finished - started),
        optimizer_seconds=(
            None if optimization_started is None or optimization_finished is None
            else optimization_finished - optimization_started
        ),
        finalization_reserve_seconds=FINALIZATION_RESERVE_SECONDS,
        frozen_state_digest=frozen_start_digest,
        accepted_commit_id_before=state.commit_id,
        initial_gradient=initial_gradient,
        first_actual_update=first_update,
        metrics=final_metrics,
        plateau_pairs=plateau_pairs,
        physical_energy_stalled=physical_stalled,
        terminal_classification=terminal_classification,
        post_update=post_update,
        acceptance_reload_audit=acceptance_reload_audit,
        legacy_initial_alpha_gap=legacy_initial_gap,
        failure=failure,
    )

    try:
        artifact_names: list[str] = []
        if cache is not None and h is not None and A is not None and p is not None and q_ref is not None and f_fixed is not None:
            write_fields(stage_folder, cache, h, A, p, q_ref, f_fixed)
            artifact_names.append("fields.npz")
        write_torch_durable(stage_folder / "candidate_network.pt", clone_state_dict(net))
        artifact_names.append("candidate_network.pt")
        if not can_prepare_acceptance:
            write_torch_durable(
                stage_folder / "unaccepted_candidate.pt",
                dict(
                    accepted_commit_id_before=state.commit_id,
                    network_state_dict=clone_state_dict(net),
                    history_alpha=None if h is None else h,
                    hist_fat=None if A is None else A,
                    psi_plus_prev=None if p is None else p,
                    q_ref=None if q_ref is None else q_ref,
                    f_fixed=f_fixed,
                    termination=termination,
                    failure=failure,
                ),
            )
            artifact_names.append("unaccepted_candidate.pt")
        write_json_durable(stage_folder / "trace.json", trace)
        artifact_names.append("trace.json")
        write_json_durable(stage_folder / "plateau_pairs.json", plateau_pairs)
        artifact_names.append("plateau_pairs.json")
        if failure is not None:
            write_json_durable(stage_folder / "failure_context.json", failure)
            artifact_names.append("failure_context.json")
        write_json_durable(stage_folder / "receipt.json", artifact_receipt)
        artifact_names.append("receipt.json")
        manifest_path, manifest_sha = write_artifact_manifest(stage_folder, artifact_names)

        if can_prepare_acceptance and time.monotonic() >= deadline:
            termination = "wall_cap_during_finalization"
            failure = dict(error="hard step deadline reached while staging evidence", type="StepCap")
            can_prepare_acceptance = False
            next_state = state
            if staged_record_tmp is not None:
                staged_record_tmp.unlink(missing_ok=True)
                staged_record_tmp = None
            artifact_receipt.update(
                accepted=False,
                acceptance_status="unaccepted",
                stop_reason=termination,
                termination_event=None,
                failure=failure,
            )
            write_json_durable(stage_folder / "receipt.json", artifact_receipt)
            manifest_path, manifest_sha = write_artifact_manifest(stage_folder, artifact_names)

        if not can_prepare_acceptance:
            publish_directory(stage_folder, step_folder)
            returned = dict(artifact_receipt)
            returned["accepted"] = False
            returned["acceptance_status"] = "unaccepted"
            returned["stop_reason"] = termination
            returned["failure"] = failure
            returned["step_elapsed_seconds"] = time.monotonic() - started
            return False, state, returned

        require(
            staged_record_tmp is not None and staged_record_final is not None and staged_record_sha is not None,
            "prepared acceptance lacks a staged state record",
        )
        parent_pointer = json.loads(pointer_path.read_text())
        require(parent_pointer.get("accepted_commit_id") == state.commit_id, "pointer parent changed before state-index staging")
        parent_index_file = parent_pointer.get("state_index_file")
        require(isinstance(parent_index_file, str), "parent pointer lacks index file")
        staged_index_tmp, staged_index_final, staged_index_sha = stage_state_index(
            indices_dir,
            state=next_state,
            parent_index_file=parent_index_file,
            record_file=staged_record_final.name,
            record_sha256=staged_record_sha,
            evidence_dir=step_folder.name,
            artifact_manifest_file=manifest_path.name,
            artifact_manifest_sha256=manifest_sha,
            mesh_order_hash=mesh_order_hash,
            route_hash=route_hash,
            phase=dict(
                step=step,
                cycle=(step - 1) // 5 + 1,
                substep=(step - 1) % 5 + 1,
                load=float(field.lmbda),
            ),
        )
        publish_file(staged_record_tmp, staged_record_final)
        publish_directory(stage_folder, step_folder)
        publish_file(staged_index_tmp, staged_index_final)
        pointer_publication = publish_pointer_last(
            pointer_path=pointer_path,
            arm_dir=arm_dir,
            records_dir=records_dir,
            indices_dir=indices_dir,
            state=next_state,
            final_record_path=staged_record_final,
            record_sha256=staged_record_sha,
            final_index_path=staged_index_final,
            index_sha256=staged_index_sha,
            expected_mesh_hash=mesh_order_hash,
            expected_route_hash=route_hash,
            device=device,
            deadline=deadline,
        )
        returned = dict(artifact_receipt)
        returned.update(
            accepted=True,
            acceptance_status="committed_by_pointer",
            accepted_commit_id_after=next_state.commit_id,
            step_elapsed_seconds=time.monotonic() - started,
            pointer_publication=pointer_publication,
        )
        return True, next_state, returned
    except Exception as exc:
        if staged_record_tmp is not None and staged_record_tmp.exists():
            staged_record_tmp.unlink(missing_ok=True)
        # No pointer has been advanced unless publish_pointer_last independently
        # verified a completed bundle and returned normally.
        returned = dict(artifact_receipt)
        returned.update(
            accepted=False,
            acceptance_status="transaction_unpublished",
            stop_reason=("wall_cap_during_finalization" if isinstance(exc, StepCap) else "atomic_bundle_publish_failed"),
            failure=dict(error=repr(exc), type=type(exc).__name__),
            step_elapsed_seconds=time.monotonic() - started,
        )
        return False, state, returned

def initial_state_from_recovery(
    *,
    net: torch.nn.Module,
    field: FieldComputation,
    inp: torch.Tensor,
    checkpoint: dict[str, Any],
) -> tuple[AcceptedState, dict[str, float]]:
    require(not field.williams_enabled, "E040 declares no Williams input route")
    require(not field.symmetry_prior, "E040 declares no symmetry input route")
    require(not field.local_patch_enabled, "E040 declares no local patch route")
    require(not field.ansatz_enabled, "E040 declares no enriched output route")
    history_alpha = checkpoint["hist_alpha"].detach().clone()
    hist_fat = checkpoint["hist_fat"].detach().clone()
    psi_plus_prev = checkpoint["psi_plus_prev"].detach().clone()
    legacy_constraint = field.alpha_constraint
    with torch.no_grad():
        _, _, legacy_d = field.fieldCalculation(inp)
    capture = LegacyRawCapture(legacy_constraint)
    field.alpha_constraint = capture
    with torch.no_grad():
        _, _, replay_d = field.fieldCalculation(inp)
    require(capture.calls == 1 and capture.raw is not None, "initial raw damage capture failed")
    require(torch.equal(legacy_d, replay_d), "legacy raw capture changed legacy damage")
    q_ref = capture.raw.detach().clone()
    gap = legacy_d - history_alpha
    gap_metrics = dict(
        min=float(gap.min()),
        max=float(gap.max()),
        mean_abs=float(gap.abs().mean()),
        rms=float(torch.sqrt(gap.square().mean())),
        count_abs_gt_1e_minus_3=int((gap.abs() > 1e-3).sum()),
    )
    return (
        AcceptedState(
            commit_id="state_000",
            history_alpha=history_alpha,
            hist_fat=hist_fat,
            psi_plus_prev=psi_plus_prev,
            q_ref=q_ref,
            parent_commit_id=None,
        ),
        gap_metrics,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--reference-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--step-seconds", type=float, default=240.0)
    parser.add_argument("--total-seconds", type=float, default=3300.0)
    parser.add_argument("--max-updates", type=int, default=10000)
    args = parser.parse_args()
    require(0 < args.step_seconds <= 240.0, "step seconds must be in (0,240]")
    require(0 < args.total_seconds <= 3300.0, "total seconds must be in (0,3300]")
    require(args.max_updates == 10000, "E040 fixed protocol requires exactly 10000 update cap")
    require(torch.cuda.is_available(), "S04-E040 producer must not train on CPU/Mac")
    require(not args.output.exists(), f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    started = time.monotonic()
    total_deadline = started + args.total_seconds
    device = "cuda"
    torch.set_num_threads(4)

    pff, mat, net, field, inp, conn, area = construct_standard_field(device)
    weights = lumped_weights(conn, area, len(inp))
    expected_mesh_hash = mesh_hash(inp, conn, area)
    expected_route_hash = field_route_hash(field)
    require(bool((area > 0).all()), "non-positive mesh area")
    settings = (args.baseline / "model_settings.txt").read_text()
    for token in (
        "umax: 0.12",
        "mesh_tag: hard_d1_u0_recovery",
        "recovery_step_offset: 1",
        "fem_gp_tri3_g_mean",
    ):
        require(token in settings, f"baseline setting missing {token!r}")
    reference_steps = json.loads((args.reference_result / "original" / "steps.json").read_text())
    require(len(reference_steps) == 15 and all(row["accepted"] for row in reference_steps), "reference R001 is incomplete")
    checkpoint = load_torch(args.baseline / "best_models" / "checkpoint_step_0.pt", device)
    initial_network = load_torch(args.baseline / "best_models" / "trained_1NN_0.pt", device)
    net.load_state_dict(initial_network, strict=True)
    require(checkpoint["history_driver_mode"] == "current_active", "wrong baseline history mode")
    require(not checkpoint["lagged_stiffness_enabled"], "wrong baseline stiffness timing")
    require(bool((checkpoint["hist_fat"] == 0).all()), "recovery fatigue is not zero")
    require(bool((checkpoint["psi_plus_prev"] == 0).all()), "recovery previous driver is not zero")

    with (args.output / "mesh.npz").open("wb") as handle:
        np.savez_compressed(
            handle,
            xy=inp.cpu().numpy(),
            triangles=conn.cpu().numpy(),
            area=area.cpu().numpy(),
            node_weights=weights.cpu().numpy(),
        )
        handle.flush()
        os.fsync(handle.fileno())
    write_json_durable(
        args.output / "manifest.json",
        dict(
            experiment="S04-E040",
            protocol="r1",
            source_commit=args.source_commit,
            baseline=str(args.baseline),
            reference_result=str(args.reference_result),
            arm="feasible_damage",
            steps=list(range(1, 16)),
            factors=list(FACTORS),
            torch=torch.__version__,
            gpu=torch.cuda.get_device_name(0),
            step_seconds=args.step_seconds,
            total_seconds=args.total_seconds,
            max_updates=args.max_updates,
            optimizer=dict(name="RPROP", lr=1e-5, step_sizes=[1e-10, 50]),
            objective="log10(E_el + E_d) + 1e-5*sum(weight^2)",
            irreversibility_in_backward_graph=False,
            shadow_irreversibility="final cache only under no_grad",
            damage_map="h + (1-h)*(0.25*clamp_min(q-q_ref,0))/(1+0.25*clamp_min(q-q_ref,0))",
            mesh_order_hash=expected_mesh_hash,
            field_route_hash=expected_route_hash,
        ),
    )
    fsync_directory(args.output)

    arm_dir = args.output / "feasible_damage"
    arm_dir.mkdir()
    records_dir = arm_dir / "accepted_states"
    indices_dir = arm_dir / "state_indices"
    pointer_path = arm_dir / "accepted_state_pointer.json"
    state, legacy_gap = initial_state_from_recovery(net=net, field=field, inp=inp, checkpoint=checkpoint)
    check_state_shapes(state, len(inp), len(conn), expected_route_hash, expected_mesh_hash)

    # State_000 has the same evidence-before-pointer contract as every later
    # step, even though it has no physical phase or fields.npz.
    initial_record_tmp, initial_record_final, initial_audit, initial_record_sha = stage_accepted_state_record(
        records_dir,
        net,
        state,
        expected_mesh_hash,
        expected_route_hash,
        inp,
        device,
        total_deadline,
    )
    initial_stage = arm_dir / f".txn-initial-state.{uuid.uuid4().hex}.tmp"
    initial_stage.mkdir()
    write_json_durable(
        initial_stage / "initial_state_audit.json",
        dict(legacy_alpha_gap=legacy_gap, reload_audit=initial_audit),
    )
    initial_manifest_path, initial_manifest_sha = write_artifact_manifest(
        initial_stage, ["initial_state_audit.json"]
    )
    initial_index_tmp, initial_index_final, initial_index_sha = stage_state_index(
        indices_dir,
        state=state,
        parent_index_file=None,
        record_file=initial_record_final.name,
        record_sha256=initial_record_sha,
        evidence_dir="initial_state",
        artifact_manifest_file=initial_manifest_path.name,
        artifact_manifest_sha256=initial_manifest_sha,
        mesh_order_hash=expected_mesh_hash,
        route_hash=expected_route_hash,
        phase=None,
    )
    publish_file(initial_record_tmp, initial_record_final)
    publish_directory(initial_stage, arm_dir / "initial_state")
    publish_file(initial_index_tmp, initial_index_final)
    publish_pointer_last(
        pointer_path=pointer_path,
        arm_dir=arm_dir,
        records_dir=records_dir,
        indices_dir=indices_dir,
        state=state,
        final_record_path=initial_record_final,
        record_sha256=initial_record_sha,
        final_index_path=initial_index_final,
        index_sha256=initial_index_sha,
        expected_mesh_hash=expected_mesh_hash,
        expected_route_hash=expected_route_hash,
        device=device,
        deadline=total_deadline,
    )
    state, _ = restore_accepted_state(
        pointer_path,
        arm_dir,
        records_dir,
        indices_dir,
        net,
        expected_mesh_hash,
        expected_route_hash,
        device,
    )
    check_state_shapes(state, len(inp), len(conn), expected_route_hash, expected_mesh_hash)

    receipts: list[dict[str, Any]] = []
    for step in range(1, 16):
        # Reload the exact state after every prior pointer publication.  This
        # makes the durable record, rather than a Python variable, the sole
        # source of the next physical step.
        state, _ = restore_accepted_state(
            pointer_path,
            arm_dir,
            records_dir,
            indices_dir,
            net,
            expected_mesh_hash,
            expected_route_hash,
            device,
        )
        check_state_shapes(state, len(inp), len(conn), expected_route_hash, expected_mesh_hash)
        step_started = time.monotonic()
        step_deadline = full_step_deadline(
            total_deadline, args.step_seconds, step_started
        )
        if step_deadline is None:
            atomic_json(
                arm_dir / "budget_stop.json",
                dict(
                    next_step=step,
                    elapsed_seconds=step_started - started,
                    remaining_seconds=total_deadline - step_started,
                    required_step_seconds=args.step_seconds,
                ),
            )
            break
        accepted, new_state, receipt = run_step(
            step=step,
            step_folder=arm_dir / f"step_{step:03d}",
            arm_dir=arm_dir,
            state=state,
            net=net,
            field=field,
            inp=inp,
            conn=conn,
            area=area,
            weights=weights,
            mat=mat,
            pff=pff,
            deadline=step_deadline,
            max_updates=args.max_updates,
            mesh_order_hash=expected_mesh_hash,
            route_hash=expected_route_hash,
            records_dir=records_dir,
            indices_dir=indices_dir,
            pointer_path=pointer_path,
            device=device,
            legacy_initial_gap=legacy_gap if step == 1 else None,
        )
        receipts.append(receipt)
        atomic_json(arm_dir / "steps.json", receipts)
        print(json.dumps(receipt, allow_nan=False), flush=True)
        if not accepted:
            break
        state = new_state

    summary = dict(
        arm="feasible_damage",
        steps_attempted=len(receipts),
        steps_accepted=sum(receipt.get("accepted") is True for receipt in receipts),
        completed_three_cycles=len(receipts) == 15 and all(
            receipt.get("accepted") is True for receipt in receipts
        ),
        elapsed_seconds=time.monotonic() - started,
        final_accepted_commit_id=state.commit_id,
    )
    summary["outcome"] = (
        "completed_all_15_accepted_steps"
        if summary["completed_three_cycles"]
        else "terminated_before_full_accepted_trajectory"
    )
    atomic_json(arm_dir / "summary.json", summary)
    atomic_json(args.output / "results.json", [summary])
    atomic_json(
        args.output / "completed.json",
        dict(
            execution="runner_finished",
            outcome=summary["outcome"],
            elapsed_seconds=time.monotonic() - started,
            results=[summary],
            interpretation="Numerical feasibility and declared RPROP plateau only; no FEM, physical, or field-space stationarity claim.",
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        if "--output" in sys.argv:
            output = Path(sys.argv[sys.argv.index("--output") + 1])
            if output.is_dir():
                dump_json(output / "fatal.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        raise
