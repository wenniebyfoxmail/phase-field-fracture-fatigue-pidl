#!/usr/bin/env python3
"""Run the S09-E008 Stage-0A synthetic-only P0 wiring gate."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from s09_equilibrium_operator import build_graph, graph_to_torch
from s09_q4_quadrature import q4_shape_data
from s09_stage0a_transition import (
    Stage0ATransitionOperator,
    carrara_f,
    fixed_judgement_loss,
    raw_increment_objectives,
    stage0a_objectives,
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fixture(dtype=torch.float64):
    xy = np.array([[i / 2, j / 2] for j in range(3) for i in range(3)], dtype=np.float64)
    conn_np = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]])
    area = np.array([1, 2, 1, 2, 4, 2, 1, 2, 1], dtype=np.float64) / 16
    graph = graph_to_torch(build_graph(xy, conn_np, area, bins=2), "cpu", dtype=dtype)
    conn = torch.as_tensor(conn_np)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    d_pre = torch.linspace(0.0, 0.4, len(xy), dtype=dtype)
    alpha = torch.full((4, 4), 0.2, dtype=dtype)
    history = torch.stack(
        (torch.full_like(alpha, 0.3), alpha, torch.full_like(alpha, 0.1), carrara_f(alpha)), -1
    )
    path = torch.tensor([0, 0.03125, 0.0625, 0.09375, 0.125, 0], dtype=dtype)
    return graph, conn, shape, dshape, det, d_pre, history, path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/s09_e008_stage0a_p0.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config["scope"] != "synthetic_p0_only":
        raise RuntimeError("P0 runner accepts synthetic scope only")
    if config["scientific_array_decode_authorized"] or config["training_authorized"]:
        raise RuntimeError("P0 config must prohibit scientific decode and training")
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    receipt = {
        "experiment_id": "S09-E008",
        "gate": "synthetic_stage0a_p0",
        "commit": git("rev-parse", "HEAD"),
        "dirty": git("status", "--porcelain"),
        "hostname": platform.node(),
        "python": sys.version,
        "torch": torch.__version__,
        "scientific_arrays_opened": False,
        "optimizer_steps": 0,
        "started_unix": started,
        "status": "running",
    }
    dump(args.out / "receipt.json", receipt)
    torch.manual_seed(1)
    graph, conn, shape, dshape, det, d_pre, history, path = fixture()
    model = Stage0ATransitionOperator(
        0.1, [0.2, 0.2, 0.2], [0.1, 0.1],
        width=config["width"], rank=config["rank"],
    ).double()

    zero = model(d_pre, history, path, graph, conn, shape, det)
    zero_state = bool(
        torch.equal(zero["d_peak"], d_pre)
        and torch.equal(zero["history_peak"], history)
    )
    y = graph["xy"][:, 1]
    boundary_ok = bool(
        torch.equal(zero["u_peak"][y == y.min()], torch.zeros((3, 2), dtype=y.dtype))
        and torch.equal(zero["u_peak"][y == y.max(), 1], torch.full((3,), path[4], dtype=y.dtype))
    )

    with torch.no_grad():
        for decoder in (model.node_decoder, model.gp_decoder):
            decoder[-1].weight.normal_(0, 1e-3)
            decoder[-1].bias.normal_(0, 1e-3)
    pred = model(d_pre, history, path, graph, conn, shape, det)
    target_history = history + torch.tensor([0.01, 0.02, 0.01, 0.0], dtype=d_pre.dtype)
    target_history[..., 3] = carrara_f(target_history[..., 1])
    target = {
        "d_peak": (d_pre + 0.01).clamp(max=1),
        "history_peak": target_history,
        "u_peak": zero["u_peak"].detach() + 0.002 * (y * (1 - y))[:, None],
    }
    scales = {
        "d": torch.tensor(0.1, dtype=d_pre.dtype),
        "u": torch.tensor([0.1, 0.1], dtype=d_pre.dtype),
        "history": torch.full((4,), 0.2, dtype=d_pre.dtype),
    }
    objectives = stage0a_objectives(
        pred, target, scales, conn=conn, shape=shape, dshape=dshape, det=det,
        xy=graph["xy"], equilibrium_scale=1.0,
    )
    objectives.update(raw_increment_objectives(pred, target, d_pre, history, model))
    judgement = fixed_judgement_loss(pred, target, scales)
    total = sum(objectives.values())
    total.backward()
    gradients = {
        name: {
            "finite": bool(parameter.grad is not None and torch.isfinite(parameter.grad).all()),
            "nonzero": bool(parameter.grad is not None and parameter.grad.abs().sum() > 0),
        }
        for name, parameter in model.named_parameters()
    }
    constraints = {
        "damage_irreversible": bool(torch.all(pred["d_peak"] >= d_pre)),
        "damage_bounded": bool(torch.all(pred["d_peak"] <= 1)),
        "alpha_monotone": bool(torch.all(pred["history_peak"][..., 1] >= history[..., 1])),
        "carrara_exact": bool(torch.equal(
            pred["history_peak"][..., 3], carrara_f(pred["history_peak"][..., 1])
        )),
    }
    passed = (
        zero_state and boundary_ok and all(constraints.values())
        and all(item["finite"] for item in gradients.values())
        and all(torch.isfinite(value) for value in objectives.values())
        and torch.isfinite(judgement)
    )
    report = {
        "verdict": "P0_SYNTHETIC_PASS" if passed else "P0_SYNTHETIC_FAIL",
        "zero_increment_preserved": zero_state,
        "hard_boundary": boundary_ok,
        "constraints": constraints,
        "objectives": {key: float(value.detach()) for key, value in objectives.items()},
        "fixed_judgement": float(judgement.detach()),
        "gradient_parameter_count": len(gradients),
        "finite_gradient_parameters": sum(item["finite"] for item in gradients.values()),
        "nonzero_gradient_parameters": sum(item["nonzero"] for item in gradients.values()),
        "scientific_claim": "none_synthetic_wiring_only",
    }
    dump(args.out / "p0_report.json", report)
    receipt.update(status="succeeded" if passed else "failed", elapsed_seconds=time.time() - started)
    dump(args.out / "receipt.json", receipt)
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
