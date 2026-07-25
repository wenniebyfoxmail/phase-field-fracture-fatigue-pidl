#!/usr/bin/env python3
"""Frozen-state optimizer basin gate for Formal/Graph/Hybrid PIDL archives.

The runner never advances fatigue history.  For each requested physical cycle
it reconstructs the peak substep objective with checkpoint ``step-1`` history,
then compares matched RPROP and strong-Wolfe LBFGS branches from either the
archived final network or the previous-substep warm start.  Optional parameter
perturbations probe local basin sensitivity.
"""

from __future__ import annotations

import argparse
import ast
import copy
import csv
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "source"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SOURCE))

_argv = sys.argv
sys.argv = ["run_frozen_optimizer_basin_gate", "8", "400", "1", "TrainableReLU", "1.0"]
import config
from compute_energy import compute_energy, gradients, strain_energy_with_split
from construct_model import construct_model
from fatigue_history import compute_fatigue_degrad
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from network import bind_mesh_graph
sys.argv = _argv


def parse_settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def parse_literal(settings: dict[str, str], key: str, default):
    value = settings.get(key)
    return default if value is None else ast.literal_eval(value)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_load(path: Path, device: torch.device):
    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


def peak_step(cycle: int, settings: dict[str, str]) -> int:
    offset = int(settings.get("recovery_step_offset", 0))
    factors = parse_literal(settings, "explicit_cycle_factors", [0.25, 0.5, 0.75, 1.0, 0.0])
    peak_index = int(np.argmax(np.asarray(factors, dtype=np.float64)))
    return offset + (cycle - 1) * len(factors) + peak_index


def step_displacement(step: int, settings: dict[str, str]) -> float:
    offset = int(settings.get("recovery_step_offset", 0))
    umax = float(settings.get("umax", 0.12))
    if offset and step < offset:
        return 0.0
    factors = parse_literal(settings, "explicit_cycle_factors", [0.25, 0.5, 0.75, 1.0, 0.0])
    return umax * float(factors[(step - offset) % len(factors)])


def exact_bc(settings: dict[str, str]) -> dict | None:
    if not parse_bool(settings.get("exact_bc_enable"), False):
        return None
    return {"enable": True, "mode": settings.get("exact_bc_mode", "sent_plane_strain")}


def resolve_mesh(archive: Path, settings: dict[str, str], override: Path | None) -> Path:
    if override is not None:
        path = override.expanduser().resolve()
    else:
        raw = Path(settings["fine_mesh_file"])
        candidates = (raw, HERE / raw.name, archive / raw.name)
        path = next((candidate for candidate in candidates if candidate.is_file()), raw)
    if not path.is_file():
        raise FileNotFoundError(f"PIDL mesh unavailable: {path}")
    return path


@dataclass
class FrozenState:
    settings: dict[str, str]
    field: FieldComputation
    inp: torch.Tensor
    conn: torch.Tensor
    area: torch.Tensor
    hist_alpha: torch.Tensor
    hist_fat: torch.Tensor
    f_fatigue: torch.Tensor
    matprop: object
    pffmodel: object
    weight_decay: float
    irreversibility: dict


def build_state(
    archive: Path,
    step: int,
    device: torch.device,
    mesh_override: Path | None,
    initialization: str,
) -> FrozenState:
    settings = parse_settings(archive / "model_settings.txt")
    mesh = resolve_mesh(archive, settings, mesh_override)
    net_cfg = dict(config.network_dict)
    net_cfg.update(
        hidden_layers=int(settings.get("hidden_layers", 8)),
        neurons=int(settings.get("neurons", 400)),
        seed=int(settings.get("seed", 1)),
        init_coeff=float(settings.get("init_coeff", settings.get("coeff", 1.0))),
        compile=False,
    )
    pff_cfg = dict(config.PFF_model_dict)
    pff_cfg["residual_stiffness"] = float(settings.get("residual_stiffness", 0.0))
    graph_cfg = parse_literal(settings, "graph_dict", {"enable": False})
    pffmodel, matprop, network = construct_model(
        pff_cfg,
        config.mat_prop_dict,
        net_cfg,
        config.domain_extrema,
        device,
        williams_dict=None,
        fourier_dict=None,
        graph_dict=graph_cfg,
    )
    numr_cfg = dict(config.numr_dict)
    numr_cfg["gradient_type"] = "numerical"
    numr_cfg["irreversibility_penalty"] = parse_literal(
        settings,
        "irreversibility_penalty",
        {"enable": False, "mode": "fem_gp_tri3"},
    )
    inp, conn, area, _ = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        numr_cfg,
        mesh_file=str(mesh),
        device=device,
    )
    bind_mesh_graph(network, conn, inp.shape[0])
    field = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema.to(device),
        lmbda=torch.tensor([step_displacement(step, settings)], device=device),
        theta=config.loading_angle.to(device),
        alpha_constraint=numr_cfg["alpha_constraint"],
        williams_dict=None,
        ansatz_dict=None,
        l0=config.mat_prop_dict["l0"],
        exact_bc_dict=exact_bc(settings),
    )
    field.net = field.net.to(device)
    model_step = step if initialization == "final" else step - 1
    model_path = archive / "best_models" / f"trained_1NN_{model_step}.pt"
    history_path = archive / "best_models" / f"checkpoint_step_{step - 1}.pt"
    if not model_path.is_file() or not history_path.is_file():
        raise FileNotFoundError(f"missing model/history pair: {model_path}, {history_path}")
    field.net.load_state_dict(safe_load(model_path, device))
    previous = safe_load(history_path, device)
    hist_alpha = previous["hist_alpha"].to(device).detach()
    hist_fat = previous["hist_fat"].to(device).detach()
    fatigue_cfg = dict(config.fatigue_dict)
    fatigue_cfg["alpha_T"] = float(settings.get("alpha_T", fatigue_cfg["alpha_T"]))
    f_fatigue = compute_fatigue_degrad(hist_fat, fatigue_cfg).detach()
    return FrozenState(
        settings=settings,
        field=field,
        inp=inp,
        conn=conn,
        area=area,
        hist_alpha=hist_alpha,
        hist_fat=hist_fat,
        f_fatigue=f_fatigue,
        matprop=matprop,
        pffmodel=pffmodel,
        weight_decay=float(settings.get("weight_decay", config.optimizer_dict["weight_decay"])),
        irreversibility=numr_cfg["irreversibility_penalty"],
    )


def perturb_parameters(model: torch.nn.Module, relative_scale: float, seed: int) -> None:
    if relative_scale <= 0.0:
        return
    generator = torch.Generator(device=next(model.parameters()).device)
    generator.manual_seed(seed)
    with torch.no_grad():
        for parameter in model.parameters():
            rms = torch.sqrt(torch.mean(parameter**2)).clamp_min(1.0e-12)
            noise = torch.randn(
                parameter.shape,
                dtype=parameter.dtype,
                device=parameter.device,
                generator=generator,
            )
            parameter.add_(relative_scale * rms * noise)


def parameter_vector(model: torch.nn.Module) -> torch.Tensor:
    return torch.cat([p.detach().reshape(-1) for p in model.parameters() if p.requires_grad])


def objective(state: FrozenState, backward: bool) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    if backward:
        state.field.net.zero_grad(set_to_none=True)
    u, v, alpha = state.field.fieldCalculation(state.inp)
    e_el, e_d, e_hist = compute_energy(
        state.inp,
        u,
        v,
        alpha,
        state.hist_alpha,
        state.matprop,
        state.pffmodel,
        state.area,
        state.conn,
        f_fatigue=state.f_fatigue,
        irreversibility_penalty_cfg=state.irreversibility,
    )
    variational = torch.log10(e_el + e_d + e_hist)
    regularization = torch.zeros((), dtype=variational.dtype, device=variational.device)
    for name, parameter in state.field.net.named_parameters():
        if "weight" in name:
            regularization = regularization + torch.sum(parameter**2)
    total = variational + state.weight_decay * regularization
    if backward:
        total.backward()
    return total, {
        "u": u,
        "v": v,
        "alpha": alpha,
        "E_el": e_el,
        "E_d": e_d,
        "E_hist": e_hist,
        "loss_variational": variational,
        "loss_regularization": state.weight_decay * regularization,
    }


def project_to_fem(values: np.ndarray, projection: dict[str, np.ndarray]) -> np.ndarray:
    numer = np.bincount(
        projection["dst"],
        weights=projection["weight"] * values[projection["src"]],
        minlength=len(projection["overlap_area"]),
    )
    return numer / np.maximum(projection["overlap_area"], 1.0e-30)


def load_reference(path: Path | None, projection_path: Path | None, cycle: int):
    if path is None:
        return None
    data = np.load(path, allow_pickle=False)
    cycles = np.asarray(data["cycles"]).reshape(-1)
    matches = np.flatnonzero(cycles == cycle)
    if len(matches) != 1:
        raise ValueError(f"reference has {len(matches)} entries for cycle {cycle}")
    states = np.asarray(data["states"])[matches[0]]
    damage = np.clip(states[:, 0], 0.0, 1.0)
    history = np.maximum(states[:, 1], 0.0)
    fatigue = np.clip(states[:, 2], 0.0, 1.0)
    raw = np.power(10.0, states[:, 3])
    reference = {
        "damage": damage,
        "history": history,
        "fatigue": fatigue,
        "raw": raw,
        "active": (1.0 - damage) ** 2 * raw,
        "area": np.asarray(data["areas"], dtype=np.float64),
    }
    if projection_path is None:
        raise ValueError("--projection-map is required with --fem-reference")
    projection_data = np.load(projection_path, allow_pickle=False)
    projection = {key: np.asarray(projection_data[key]) for key in projection_data.files}
    if int(projection["src"].max()) + 1 != 90000:
        raise ValueError("projection source is not the 90,000-element PIDL mesh")
    return reference, projection


def support_metrics(predicted: np.ndarray, reference: np.ndarray, area: np.ndarray) -> dict[str, float]:
    eps = 1.0e-12
    finite = np.isfinite(predicted) & np.isfinite(reference)
    pred = np.maximum(predicted, 0.0)
    ref = np.maximum(reference, 0.0)
    threshold = float(np.percentile(ref[finite], 99.0))
    mask_ref = finite & (ref >= threshold)
    mask_pred = finite & (pred >= threshold)
    own_threshold = float(np.percentile(pred[finite], 99.0))
    mask_own = finite & (pred >= own_threshold)

    def area_sum(mask):
        return float(np.sum(area[mask]))

    union = area_sum(mask_ref | mask_pred)
    own_union = area_sum(mask_ref | mask_own)
    ref_area = area_sum(mask_ref)
    log_ref = np.log10(ref[finite] + eps)
    log_pred = np.log10(pred[finite] + eps)
    return {
        "active_log_mae": float(np.mean(np.abs(log_pred - log_ref))),
        "active_log_rmse": float(np.sqrt(np.mean((log_pred - log_ref) ** 2))),
        "active_log_corr": float(np.corrcoef(log_pred, log_ref)[0, 1]),
        "active_absolute_p99_iou": area_sum(mask_ref & mask_pred) / max(union, eps),
        "active_own_p99_iou": area_sum(mask_ref & mask_own) / max(own_union, eps),
        "active_support_area_ratio": area_sum(mask_pred) / max(ref_area, eps),
    }


def evaluate(state: FrozenState, reference_bundle, previous_parameters: torch.Tensor | None) -> dict[str, float]:
    total, terms = objective(state, backward=True)
    grads = [
        torch.zeros_like(parameter).reshape(-1)
        if parameter.grad is None
        else parameter.grad.detach().reshape(-1)
        for parameter in state.field.net.parameters()
        if parameter.requires_grad
    ]
    gradient = torch.cat(grads)
    current = parameter_vector(state.field.net)
    with torch.no_grad():
        alpha = terms["alpha"]
        alpha_elem = (
            alpha[state.conn[:, 0]] + alpha[state.conn[:, 1]] + alpha[state.conn[:, 2]]
        ) / 3.0
        eps_xx, eps_yy, eps_xy, _, _ = gradients(
            state.inp, terms["u"], terms["v"], alpha, state.area, state.conn
        )
        _, raw = strain_energy_with_split(
            eps_xx, eps_yy, eps_xy, alpha_elem, state.matprop, state.pffmodel
        )
        degradation, _ = state.pffmodel.Edegrade(alpha_elem)
        active = degradation * raw
    row = {
        "loss_total": float(total.detach()),
        "loss_variational": float(terms["loss_variational"].detach()),
        "loss_regularization": float(terms["loss_regularization"].detach()),
        "E_el": float(terms["E_el"].detach()),
        "E_d": float(terms["E_d"].detach()),
        "E_hist": float(terms["E_hist"].detach()),
        "gradient_l2": float(torch.linalg.vector_norm(gradient)),
        "gradient_rms": float(torch.sqrt(torch.mean(gradient**2))),
        "update_l2": float("nan")
        if previous_parameters is None
        else float(torch.linalg.vector_norm(current - previous_parameters)),
        "parameter_l2": float(torch.linalg.vector_norm(current)),
    }
    if reference_bundle is not None:
        reference, projection = reference_bundle
        mapped_active = project_to_fem(active.detach().cpu().numpy(), projection)
        mapped_damage = project_to_fem(alpha_elem.detach().cpu().numpy(), projection)
        row.update(support_metrics(mapped_active, reference["active"], reference["area"]))
        row["damage_rmse"] = float(np.sqrt(np.average(
            (mapped_damage - reference["damage"]) ** 2, weights=reference["area"]
        )))
    return row


def optimize_branch(
    state: FrozenState,
    optimizer_name: str,
    budget: int,
    lr: float,
    record_every: int,
    reference_bundle,
) -> tuple[list[dict[str, float]], dict[str, torch.Tensor]]:
    rows: list[dict[str, float]] = []
    previous = parameter_vector(state.field.net)
    best_loss = math.inf
    best_state = copy.deepcopy(state.field.net.state_dict())
    calls = 0

    def record(index: int, stage: str):
        nonlocal previous, best_loss, best_state
        row = evaluate(state, reference_bundle, previous)
        row.update({"record": index, "stage": stage, "closure_calls": calls})
        rows.append(row)
        previous = parameter_vector(state.field.net)
        if row["loss_total"] < best_loss:
            best_loss = row["loss_total"]
            best_state = copy.deepcopy(state.field.net.state_dict())

    record(0, "initial")
    if optimizer_name == "rprop":
        optimizer = torch.optim.Rprop(
            state.field.net.parameters(), lr=lr, step_sizes=(1.0e-10, 50.0)
        )
        for update in range(1, budget + 1):
            objective(state, backward=True)[0]
            optimizer.step()
            if update % record_every == 0 or update == budget:
                record(update, "iterate")
    elif optimizer_name == "lbfgs":
        optimizer = torch.optim.LBFGS(
            state.field.net.parameters(),
            lr=lr,
            max_iter=budget,
            max_eval=budget * 4,
            history_size=100,
            tolerance_grad=1.0e-12,
            tolerance_change=1.0e-12,
            line_search_fn="strong_wolfe",
        )

        def closure():
            nonlocal calls
            calls += 1
            return objective(state, backward=True)[0]

        optimizer.step(closure)
        record(budget, "iterate")
    else:
        raise ValueError(f"unknown optimizer {optimizer_name!r}")
    state.field.net.load_state_dict(best_state)
    record(budget, "best_restored")
    return rows, best_state


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--cycles", type=int, nargs="+", default=[76, 87, 89])
    parser.add_argument("--optimizers", nargs="+", choices=("rprop", "lbfgs"), default=["rprop", "lbfgs"])
    parser.add_argument("--initializations", nargs="+", choices=("final", "previous"), default=["final", "previous"])
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--perturbation", type=float, default=1.0e-4)
    parser.add_argument("--rprop-budget", type=int, default=2000)
    parser.add_argument("--lbfgs-budget", type=int, default=400)
    parser.add_argument("--rprop-lr", type=float, default=1.0e-5)
    parser.add_argument("--lbfgs-lr", type=float, default=0.5)
    parser.add_argument("--record-every", type=int, default=100)
    parser.add_argument("--mesh-file", type=Path)
    parser.add_argument("--fem-reference", type=Path)
    parser.add_argument("--projection-map", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--save-models", action="store_true")
    args = parser.parse_args()

    archive = args.archive.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    device = torch.device(args.device)
    settings = parse_settings(archive / "model_settings.txt")
    all_rows: list[dict] = []
    started = time.time()
    for cycle in args.cycles:
        step = peak_step(cycle, settings)
        reference = load_reference(args.fem_reference, args.projection_map, cycle)
        for initialization in args.initializations:
            for optimizer_name in args.optimizers:
                for seed in args.seeds:
                    state = build_state(archive, step, device, args.mesh_file, initialization)
                    perturb_parameters(state.field.net, args.perturbation if seed else 0.0, seed)
                    budget = args.rprop_budget if optimizer_name == "rprop" else args.lbfgs_budget
                    lr = args.rprop_lr if optimizer_name == "rprop" else args.lbfgs_lr
                    rows, best_state = optimize_branch(
                        state, optimizer_name, budget, lr, args.record_every, reference
                    )
                    branch = f"c{cycle}_{initialization}_{optimizer_name}_seed{seed}"
                    for row in rows:
                        row.update(
                            branch=branch,
                            cycle=cycle,
                            step=step,
                            initialization=initialization,
                            optimizer=optimizer_name,
                            seed=seed,
                            perturbation=args.perturbation if seed else 0.0,
                        )
                    all_rows.extend(rows)
                    if args.save_models:
                        torch.save(best_state, out_dir / f"{branch}_best.pt")
                    write_csv(out_dir / f"{branch}_trace.csv", rows)
                    print(f"[complete] {branch} best={rows[-1]['loss_total']:.8g}", flush=True)

    write_csv(out_dir / "all_optimizer_traces.csv", all_rows)
    manifest = {
        "archive": str(archive),
        "archive_settings_sha256": sha256(archive / "model_settings.txt"),
        "cycles": args.cycles,
        "optimizers": args.optimizers,
        "initializations": args.initializations,
        "seeds": args.seeds,
        "perturbation": args.perturbation,
        "budgets": {"rprop": args.rprop_budget, "lbfgs": args.lbfgs_budget},
        "learning_rates": {"rprop": args.rprop_lr, "lbfgs": args.lbfgs_lr},
        "history_semantics": "network at requested initialization; frozen history checkpoint step-1",
        "fem_reference": None if args.fem_reference is None else str(args.fem_reference.resolve()),
        "projection_map": None if args.projection_map is None else str(args.projection_map.resolve()),
        "elapsed_seconds": time.time() - started,
        "device": str(device),
        "torch_version": torch.__version__,
    }
    (out_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
