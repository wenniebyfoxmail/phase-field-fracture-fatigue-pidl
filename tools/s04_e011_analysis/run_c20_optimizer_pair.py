#!/usr/bin/env python3
"""Strict c20/s4 RPROP versus strong-Wolfe L-BFGS comparison.

This is a frozen-state numerical-optimizer experiment.  It never advances a
fatigue/history variable, never writes the input checkpoint, and evaluates the
same legacy float32 joint PIDL objective in both arms.  A budget unit is one
loss-plus-backward evaluation; every L-BFGS line-search closure is counted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import torch

import run_pidl_block_diagnosis as diagnosis


class BudgetStop(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def clone_parameters(net) -> list[torch.Tensor]:
    return [parameter.detach().clone() for parameter in net.parameters()]


def restore_parameters(net, values: list[torch.Tensor]) -> None:
    with torch.no_grad():
        for parameter, value in zip(net.parameters(), values):
            parameter.copy_(value)


def parameter_digest(net) -> str:
    digest = hashlib.sha256()
    for parameter in net.parameters():
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def parameter_change(net, reference: list[torch.Tensor]) -> tuple[float, float]:
    max_abs = 0.0
    square_sum = 0.0
    for parameter, start in zip(net.parameters(), reference):
        delta = parameter.detach() - start
        max_abs = max(max_abs, float(delta.abs().max()))
        square_sum += float(delta.square().sum())
    return max_abs, math.sqrt(square_sum)


def build_legacy_problem(input_path: Path, model_path: Path, device: torch.device):
    data_npz = np.load(input_path, allow_pickle=False)
    data = {key: data_npz[key] for key in data_npz.files}
    for key in ("nodes", "cells", "pidl_hist_alpha_pre", "pidl_f_pre", "u_fem", "v_fem", "d_fem"):
        if key not in data:
            raise KeyError(f"required c20/s4 input key missing: {key}")
    if tuple(data["nodes"].shape) != (86756, 2) or tuple(data["cells"].shape) != (86408, 4):
        raise ValueError("unexpected c20/s4 Q4 mesh identity")
    state = torch.load(model_path, map_location=device, weights_only=True)
    problem = diagnosis.LocalProblem(data, device)
    field = diagnosis.make_field(state, device, 0.11999988, "legacy_nonsmooth")
    x32 = problem.x.float()
    hist32 = problem.hist.float()
    fatigue32 = problem.f.float()
    area32 = diagnosis.q4_shape_data(x32, problem.cells)[2].sum(1)

    def objective() -> torch.Tensor:
        u, v, damage = field.fieldCalculation(x32)
        parts = diagnosis.compute_energy(
            x32, u, v, damage, hist32, problem.mat, problem.model, area32,
            problem.cells, f_fatigue=fatigue32,
            irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
        )
        energy = sum(parts)
        if not bool(torch.isfinite(energy)) or float(energy.detach()) <= 0.0:
            raise RuntimeError("legacy joint objective left its log-energy domain")
        regularization = sum(
            parameter.square().sum()
            for name, parameter in field.net.named_parameters()
            if "weight" in name
        )
        return torch.log10(energy) + 1.0e-5 * regularization

    return data, problem, field, objective


def terminal_readout(field, problem, objective, start_parameters: list[torch.Tensor]) -> dict:
    field.net.zero_grad(set_to_none=True)
    value = objective()
    value.backward()
    gradients = [
        parameter.grad.detach().reshape(-1)
        for parameter in field.net.parameters()
        if parameter.grad is not None
    ]
    gradient = torch.cat(gradients)
    with torch.no_grad():
        u, v, damage = field.fieldCalculation(problem.x.float())
    max_abs, l2 = parameter_change(field.net, start_parameters)
    metrics = problem.measures(u, v, damage)
    metrics.update(
        loss_total=float(value.detach()),
        gradient_l2=float(torch.linalg.vector_norm(gradient)),
        gradient_rms=float(torch.sqrt(torch.mean(gradient.square()))),
        parameter_delta_inf=max_abs,
        parameter_delta_l2=l2,
        parameter_digest=parameter_digest(field.net),
    )
    return metrics


def run_rprop(field, objective, start_parameters, max_evaluations, wall_seconds):
    optimizer = torch.optim.Rprop(field.net.parameters(), lr=1.0e-5, step_sizes=(1.0e-10, 50.0))
    trace: list[dict] = []
    started = time.monotonic()
    for evaluation in range(1, max_evaluations + 1):
        if time.monotonic() - started >= wall_seconds:
            return trace, {"stop": "wall_deadline", "evaluations": evaluation - 1}
        before = clone_parameters(field.net)
        field.net.zero_grad(set_to_none=True)
        loss = objective()
        loss.backward()
        optimizer.step()
        step_inf, step_l2 = parameter_change(field.net, before)
        trace.append({
            "evaluation": evaluation,
            "loss": float(loss.detach()),
            "parameter_step_inf": step_inf,
            "parameter_step_l2": step_l2,
        })
    return trace, {"stop": "evaluation_budget", "evaluations": max_evaluations}


def run_lbfgs(field, objective, start_parameters, max_evaluations, wall_seconds):
    optimizer = torch.optim.LBFGS(
        field.net.parameters(), lr=1.0, max_iter=1, max_eval=20, history_size=5,
        tolerance_grad=0.0, tolerance_change=0.0, line_search_fn="strong_wolfe",
    )
    trace: list[dict] = []
    started = time.monotonic()
    calls = 0
    accepted = 0
    last_accepted = clone_parameters(field.net)
    stop = "evaluation_budget"

    def closure():
        nonlocal calls
        if calls >= max_evaluations:
            raise BudgetStop("evaluation budget")
        if time.monotonic() - started >= wall_seconds:
            raise BudgetStop("wall deadline")
        field.net.zero_grad(set_to_none=True)
        value = objective()
        value.backward()
        calls += 1
        trace.append({"evaluation": calls, "loss": float(value.detach())})
        return value

    while calls < max_evaluations:
        before = clone_parameters(field.net)
        try:
            optimizer.step(closure)
        except BudgetStop as exc:
            restore_parameters(field.net, last_accepted)
            stop = "wall_deadline" if "wall" in str(exc) else "evaluation_budget"
            break
        step_inf, step_l2 = parameter_change(field.net, before)
        accepted += 1
        last_accepted = clone_parameters(field.net)
        if step_inf == 0.0:
            stop = "exact_parameter_stagnation"
            break
        if time.monotonic() - started >= wall_seconds:
            stop = "wall_deadline"
            break
    return trace, {"stop": stop, "evaluations": calls, "accepted_updates": accepted}


def run_arm(name, data, problem, field, objective, start_parameters, args, out_dir: Path) -> dict:
    restore_parameters(field.net, start_parameters)
    initial_digest = parameter_digest(field.net)
    initial = terminal_readout(field, problem, objective, start_parameters)
    if name == "rprop":
        trace, status = run_rprop(field, objective, start_parameters, args.max_evaluations, args.wall_seconds)
    else:
        trace, status = run_lbfgs(field, objective, start_parameters, args.max_evaluations, args.wall_seconds)
    terminal = terminal_readout(field, problem, objective, start_parameters)
    arm = {
        "optimizer": name,
        "initial": initial,
        "terminal": terminal,
        "initial_parameter_digest": initial_digest,
        "same_initial_parameters": initial_digest == parameter_digest_from_values(start_parameters),
        "budget_unit": "objective_plus_backward",
        "trace_rows": len(trace),
        **status,
    }
    write_json(out_dir / f"{name}_trace.json", trace)
    write_json(out_dir / f"{name}_result.json", arm)
    torch.save(field.net.state_dict(), out_dir / f"{name}_terminal.pt")
    return arm


def parameter_digest_from_values(values: list[torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-evaluations", type=int, default=200)
    parser.add_argument("--wall-seconds", type=float, default=600.0)
    parser.add_argument("--expected-initial-loss", type=float, default=-2.0094141960144043)
    parser.add_argument("--initial-loss-tolerance", type=float, default=1.0e-6)
    args = parser.parse_args()
    if args.max_evaluations <= 0 or args.wall_seconds <= 0.0:
        raise ValueError("budgets must be positive")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this producer run")
    device = torch.device(args.device)
    input_path = args.input.resolve()
    model_path = args.model.resolve()
    out_dir = args.out.resolve()
    if out_dir.exists():
        raise FileExistsError(f"refusing to reuse output directory: {out_dir}")
    out_dir.mkdir(parents=True)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1)
    data, problem, field, objective = build_legacy_problem(input_path, model_path, device)
    start_parameters = clone_parameters(field.net)
    initial = terminal_readout(field, problem, objective, start_parameters)
    if abs(initial["loss_total"] - args.expected_initial_loss) > args.initial_loss_tolerance:
        raise AssertionError(
            f"source objective reproduction failed: {initial['loss_total']} vs {args.expected_initial_loss}"
        )
    manifest = {
        "protocol": "S04-E044-c20-optimizer-main-r1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": os.uname().nodename,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "device": str(device),
        "input": str(input_path),
        "input_sha256": sha256(input_path),
        "model": str(model_path),
        "model_sha256": sha256(model_path),
        "mesh": {"nodes": list(data["nodes"].shape), "cells": list(data["cells"].shape)},
        "cycle": 20,
        "substep": 4,
        "step": 99,
        "objective": "legacy float32 log10(E_el + E_d + E_hist) + 1e-5 weight regularizer",
        "frozen_history": True,
        "history_commits": 0,
        "max_evaluations_per_arm": args.max_evaluations,
        "wall_seconds_per_arm": args.wall_seconds,
        "initial_parameter_digest": parameter_digest_from_values(start_parameters),
        "initial_readout": initial,
    }
    write_json(out_dir / "manifest.json", manifest)
    results = {}
    for name in ("rprop", "lbfgs"):
        results[name] = run_arm(name, data, problem, field, objective, start_parameters, args, out_dir)
    write_json(out_dir / "results.json", results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
