"""GPU-only S04-E040: state-referenced feasible damage, no E_irr in loss.

This isolated runner never changes shared defaults.  It supports two fixed
arms: global raw-q only, or a q-only partition-of-unity crack-tip patch.  The
caller is responsible for the approved producer, destination and budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "source"), str(ROOT / "SENS_tensile")]

from compute_energy import compute_energy, get_psi_plus_per_elem
from construct_model import construct_model
from fatigue_history import compute_fatigue_degrad, update_fatigue_history
from feasible_damage import StateReferencedFeasibleDamageMap
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from optim import get_optimizer

FATIGUE = dict(loading_type="cyclic", accum_type="carrara", degrad_type="asymptotic", alpha_T=0.5)
FACTORS = (0.25, 0.5, 0.75, 1.0, 0.0)


class StepCap(RuntimeError):
    pass


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load(path: Path, device: str):
    return torch.load(path, map_location=device, weights_only=False)


def tensor_digest(*tensors: torch.Tensor) -> str:
    digest = hashlib.sha256()
    for tensor in tensors:
        array = tensor.detach().contiguous().cpu().numpy()
        digest.update(str(array.shape).encode())
        digest.update(str(array.dtype).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def require_baseline_contract(baseline: Path, initial, checkpoint, inp, conn) -> None:
    """Reject a similarly named archive that is not the frozen S04 recovery state."""
    settings_path = baseline / "model_settings.txt"
    if not settings_path.is_file():
        raise FileNotFoundError(settings_path)
    settings = settings_path.read_text()
    for token in ("umax: 0.12", "mesh_tag: hard_d1_u0_recovery",
                  "recovery_step_offset: 1", "fem_gp_tri3_g_mean"):
        if token not in settings:
            raise ValueError(f"baseline settings missing required token: {token}")
    if not isinstance(initial, dict):
        raise TypeError("trained_1NN_0.pt must contain a state dictionary")
    required = ("hist_alpha", "hist_fat", "psi_plus_prev", "history_driver_mode",
                "lagged_stiffness_enabled", "_frac_detected")
    missing = [key for key in required if key not in checkpoint]
    if missing:
        raise KeyError(f"baseline checkpoint is missing keys: {missing}")
    if checkpoint["history_driver_mode"] != "current_active":
        raise ValueError("baseline must use current_active history driver")
    if bool(checkpoint["lagged_stiffness_enabled"]) or bool(checkpoint["_frac_detected"]):
        raise ValueError("baseline must not contain lagged stiffness or prior fracture detection")
    if checkpoint["hist_alpha"].numel() != inp.shape[0]:
        raise ValueError("hist_alpha does not match mesh node count")
    if checkpoint["hist_fat"].numel() != conn.shape[0] or checkpoint["psi_plus_prev"].numel() != conn.shape[0]:
        raise ValueError("fatigue state does not match mesh element count")


def weight_l2(net: torch.nn.Module) -> torch.Tensor:
    return sum((parameter.square().sum() for name, parameter in net.named_parameters() if "weight" in name))


def tri3_bounds(h: torch.Tensor, damage: torch.Tensor, conn: torch.Tensor) -> dict[str, float]:
    delta = damage - h
    vertex_min = float(delta.min())
    gp = torch.stack([
        (4.0 * delta[conn[:, 0]] + delta[conn[:, 1]] + delta[conn[:, 2]]) / 6.0,
        (delta[conn[:, 0]] + 4.0 * delta[conn[:, 1]] + delta[conn[:, 2]]) / 6.0,
        (delta[conn[:, 0]] + delta[conn[:, 1]] + 4.0 * delta[conn[:, 2]]) / 6.0,
    ])
    return {
        "node_min_d_minus_h": vertex_min,
        "node_max_d": float(damage.max()),
        "gp_min_d_minus_h": float(gp.min()),
        "node_min_d": float(damage.min()),
    }


def accepted_tip(damage: torch.Tensor, inp: torch.Tensor, prior: tuple[float, float]) -> tuple[float, float]:
    """Use the accepted d field only; no moving window is allowed inside a solve."""
    mask = (damage.detach() > 0.9) & (inp[:, 0] > 0.0)
    if not bool(mask.any()):
        return prior
    candidates = inp[mask]
    distance = torch.maximum(candidates[:, 0].abs(), candidates[:, 1].abs())
    point = candidates[distance.argmax()]
    return float(point[0]), float(point[1])


def build_field(net, device: str, mode: str, tip: tuple[float, float]) -> FieldComputation:
    local_patch = {"enable": False}
    if mode == "q_local":
        local_patch = {
            "enable": True, "x_tip": tip[0], "y_tip": tip[1], "wr": 0.10,
            "output_mode": "q_only", "blend_mode": "damage_partition",
            "hidden_layers": 3, "neurons": 80, "activation": "TrainableReLU", "init_coeff": 1.0,
        }
    return FieldComputation(
        net, torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], device=device),
        torch.tensor(0.0, device=device), torch.tensor([np.pi / 2], device=device),
        l0=0.01, local_patch_dict=local_patch,
    )


def direct_objective(field, inp, h, f, mat, pff, area, conn):
    u, v, damage = field.fieldCalculation(inp)
    e_el, e_d, _ = compute_energy(
        inp, u, v, damage, h, mat, pff, area, conn, f_fatigue=f,
        include_irreversibility=False,
    )
    physical = e_el + e_d
    if not bool(torch.isfinite(physical)) or not bool(physical > 0):
        raise FloatingPointError("non-positive or non-finite E_el + E_d")
    return torch.log10(physical) + 1e-5 * weight_l2(field.net), (u, v, damage), (e_el, e_d)


def solve_step(field, inp, h, f, mat, pff, area, conn, cap_seconds: float, max_updates: int):
    started = time.monotonic()
    optimiser = get_optimizer(field.parameters(), "RPROP")
    stable = 0
    previous = None
    trace = []
    for update in range(1, max_updates + 1):
        if time.monotonic() - started >= cap_seconds:
            raise StepCap("step wall cap")
        optimiser.zero_grad(set_to_none=True)
        loss, _, _ = direct_objective(field, inp, h, f, mat, pff, area, conn)
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("non-finite direct loss")
        loss.backward()
        if not all(parameter.grad is None or bool(torch.isfinite(parameter.grad).all())
                   for parameter in field.parameters()):
            raise FloatingPointError("non-finite parameter gradient")
        value = float(loss.detach())
        optimiser.step()
        if previous is not None:
            stable = stable + 1 if abs(value - previous) <= 5e-7 * max(abs(previous), 1e-12) else 0
        previous = value
        if update == 1 or update % 50 == 0:
            trace.append({"update": update, "loss": value, "seconds": time.monotonic() - started})
        if stable >= 10:
            return update, trace, time.monotonic() - started
    raise StepCap("update cap")


def save_trial(folder, field, inp, h, A, previous_driver, f, mat, pff, area, conn):
    with torch.no_grad():
        loss, (u, v, damage), (e_el, e_d) = direct_objective(field, inp, h, f, mat, pff, area, conn)
        # This detached diagnostic is intentionally outside the optimized graph.
        _, _, shadow_e_irr = compute_energy(inp, u, v, damage, h, mat, pff, area, conn, f_fatigue=f)
        active = get_psi_plus_per_elem(inp, u, v, damage, mat, pff, area, conn,
                                       history_driver_reduction_dict={"enable": True, "mode": "fem_gp_tri3_g_mean"})
        trial_A = update_fatigue_history(A, active, previous_driver, FATIGUE)
        raw_q = field.raw_damage_channel(inp).detach()
        bounds = tri3_bounds(h, damage, conn)
        np.savez_compressed(
            folder / "fields.npz", u=u.cpu().numpy(), v=v.cpu().numpy(), d=damage.cpu().numpy(),
            h=h.cpu().numpy(), A=A.cpu().numpy(), previous_driver=previous_driver.cpu().numpy(),
            f=f.cpu().numpy(), q=raw_q.cpu().numpy(), trial_A=trial_A.cpu().numpy(), active=active.cpu().numpy(),
        )
        return dict(loss=float(loss), E_el=float(e_el), E_d=float(e_d), shadow_E_irr=float(shadow_e_irr),
                    **bounds), (damage.detach(), trial_A.detach(), active.detach(), raw_q.detach())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--mode", choices=("global", "q_local"), required=True)
    parser.add_argument("--step-seconds", type=float, default=240.0)
    parser.add_argument("--total-seconds", type=float, default=3300.0)
    parser.add_argument("--max-updates", type=int, default=10000)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("S04-E040 is producer-only; CUDA is required")
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    device = "cuda"
    started = time.monotonic()
    pff, mat, net = construct_model(
        dict(PFF_model="AT1", se_split="volumetric", tol_ir=5e-3, residual_stiffness=0.0),
        dict(mat_E=1.0, mat_nu=0.3, w1=1.0, l0=0.01),
        dict(hidden_layers=8, neurons=400, seed=1, activation="TrainableReLU", init_coeff=1.0, compile=False),
        torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], device=device), device,
    )
    inp, conn, area, _ = prep_input_data(mat, pff, dict(x_init=[-0.5], y_init=[0], L_crack=[0.5], angle_crack=[0]),
                                          dict(gradient_type="numerical"), str(ROOT / "SENS_tensile/meshed_geom_fem_soft_hist0.msh"), device)
    initial = load(args.baseline / "best_models/trained_1NN_0.pt", device)
    checkpoint = load(args.baseline / "best_models/checkpoint_step_0.pt", device)
    require_baseline_contract(args.baseline, initial, checkpoint, inp, conn)
    net.load_state_dict(initial, strict=True)
    h = checkpoint["hist_alpha"].detach().clone()
    A = checkpoint["hist_fat"].detach().clone()
    previous_driver = checkpoint["psi_plus_prev"].detach().clone()
    if bool((h < 0).any()) or bool((h > 1).any()):
        raise ValueError("the supplied accepted h is outside [0,1]")
    mesh_hash = tensor_digest(inp, conn, area)
    tip = (0.0, 0.0)
    field = build_field(net, device, args.mode, tip)
    records = []
    for step in range(1, 16):
        if time.monotonic() - started + args.step_seconds >= args.total_seconds:
            break
        folder = args.output / f"step_{step:03d}"
        folder.mkdir()
        field.lmbda = torch.tensor(0.12 * FACTORS[(step - 1) % 5], device=device)
        f = compute_fatigue_degrad(A, FATIGUE)
        q_reference = field.raw_damage_channel(inp).detach().clone()
        field.alpha_constraint = StateReferencedFeasibleDamageMap(h, q_reference)
        try:
            updates, trace, elapsed = solve_step(field, inp, h, f, mat, pff, area, conn,
                                                 args.step_seconds, args.max_updates)
            metrics, state = save_trial(folder, field, inp, h, A, previous_driver, f, mat, pff, area, conn)
            accepted = metrics["node_min_d_minus_h"] >= 0.0 and metrics["gp_min_d_minus_h"] >= 0.0 and metrics["node_max_d"] <= 1.0
            reason = "accepted" if accepted else "postsolve_feasibility_failure"
        except (StepCap, FloatingPointError) as exc:
            updates, trace, elapsed, accepted, reason = 0, [], time.monotonic() - started, False, type(exc).__name__
            try:
                metrics, state = save_trial(folder, field, inp, h, A, previous_driver, f, mat, pff, area, conn)
            except (FloatingPointError, RuntimeError) as diagnostic_exc:
                metrics, state = {"diagnostic_error": type(diagnostic_exc).__name__}, None
                reason = f"{reason}_and_{type(diagnostic_exc).__name__}"
        if accepted:
            damage, trial_A, active, _ = state
            h, A, previous_driver = damage, trial_A, active
            tip = accepted_tip(h, inp, tip)
            if args.mode == "q_local":
                field.set_local_patch_centers([tip])
            next_q_reference = field.raw_damage_channel(inp).detach().clone()
            torch.save({"network": net.state_dict(), "hist_alpha": h, "hist_fat": A,
                        "psi_plus_prev": previous_driver, "q_reference": next_q_reference,
                        "tip": tip, "mesh_hash": mesh_hash,
                        "map": {"kind": "state_referenced_feasible_damage_v1", "slope": 0.25}},
                       folder / "accepted_state.pt")
        write_json(folder / "trace.json", trace)
        record = {"step": step, "cycle": (step - 1) // 5 + 1, "substep": (step - 1) % 5 + 1,
                  "mode": args.mode, "accepted": accepted, "reason": reason, "updates": updates,
                  "elapsed_seconds": elapsed, "tip": tip, **metrics}
        write_json(folder / "receipt.json", record)
        records.append(record)
        write_json(args.output / "steps.json", records)
        if not accepted:
            break
    write_json(args.output / "manifest.json", {"experiment": "S04-E040", "source_commit": args.source_commit,
               "mode": args.mode, "mesh_hash": mesh_hash, "irreversibility_in_loss": False,
               "accepted_steps": sum(row["accepted"] for row in records), "steps": records})


if __name__ == "__main__":
    main()
