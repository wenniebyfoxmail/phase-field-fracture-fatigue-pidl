#!/usr/bin/env python3
"""Freeze a smoke-only risk weight from the U0.12/c82 checkpoint.

This is an offline scalar-scale diagnostic. It never constructs an optimizer
and never enters the training loop. The frozen coefficient makes the added
risk utility equal to 1% of the absolute baseline Deep-Ritz loss at c82.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import torch


EXPECTED = {
    "checkpoint": "581304ad5ac236da6be40c04aa694242c2a1d1ce3e28b45bb070c5a10b36faaa",
    "model": "94e7a3e249fc5b16f850382be9f027d5ff86dccc64b35b94c59458e15683fe00",
    "settings": "015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047",
    "mesh": "16b447e3dd789e300f5181c3cf9b34322e4f27575867b354f55473d2969a9ed8",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_posthoc(code_root: Path):
    path = code_root / "SENS_tensile" / "posthoc_mesh_probe_alignment.py"
    spec = importlib.util.spec_from_file_location("g3_scale_posthoc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-root", type=Path, required=True)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--mesh", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--step", type=int, default=409)
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--alpha", type=float, default=0.85)
    ap.add_argument("--target-loss-fraction", type=float, default=0.01)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    if not 0.0 < args.target_loss_fraction < 0.1:
        raise ValueError("target loss fraction must be in (0, 0.1)")

    code_root = args.code_root.resolve()
    archive = args.archive.resolve()
    mesh = args.mesh.resolve()
    assets = {
        "checkpoint": archive / "best_models" / f"checkpoint_step_{args.step}.pt",
        "model": archive / "best_models" / f"trained_1NN_{args.step}.pt",
        "settings": archive / "model_settings.txt",
        "mesh": mesh,
    }
    actual = {name: sha256(path) for name, path in assets.items()}
    if actual != EXPECTED:
        raise RuntimeError(f"frozen asset mismatch: {actual}")

    ph = load_posthoc(code_root)
    sys.path.insert(0, str(code_root / "source"))
    from compute_energy import compute_energy
    from fatigue_history import compute_fatigue_degrad
    from mechanical_residual_risk import (
        interior_free_node_mask,
        mechanical_mean_excess_from_fields,
        nodal_lumped_dual_area,
    )

    settings = ph.parse_settings(archive / "model_settings.txt")
    net_cfg = dict(ph.network_dict)
    net_cfg["seed"] = int(settings.get("seed", net_cfg["seed"]))
    net_cfg["init_coeff"] = float(
        settings.get("coeff", settings.get("init_coeff", net_cfg["init_coeff"]))
    )
    pffmodel, matprop, network = ph.construct_model(
        ph.PFF_model_dict, ph.mat_prop_dict, net_cfg, ph.domain_extrema, ph.DEVICE,
        williams_dict=None, fourier_dict=None,
    )
    inp, conn, areas, _ = ph.prep_input_data(
        matprop, pffmodel, ph.crack_dict, ph.numr_dict,
        mesh_file=str(mesh), device=ph.DEVICE,
    )
    field = ph.FieldComputation(
        net=network, domain_extrema=ph.domain_extrema,
        lmbda=torch.tensor([args.umax], device=ph.DEVICE), theta=ph.loading_angle,
        alpha_constraint=ph.numr_dict["alpha_constraint"], williams_dict=None,
        l0=ph.mat_prop_dict["l0"], exact_bc_dict=ph.exact_bc_from_settings(archive),
        local_patch_dict=ph.local_patch_from_settings(archive),
    )
    field.net.load_state_dict(torch.load(assets["model"], map_location=ph.DEVICE, weights_only=True))
    field.net.eval()
    u, v, damage = field.fieldCalculation(inp)
    state = torch.load(assets["checkpoint"], map_location=ph.DEVICE, weights_only=False)
    hist_alpha = state["hist_alpha"].to(ph.DEVICE)
    hist_fat = state["hist_fat"].to(ph.DEVICE)
    fatigue_cfg = {
        "loading_type": "cyclic",
        "accum_type": "carrara",
        "degrad_type": "asymptotic",
        "alpha_T": 0.5,
        "spatial_alpha_T": {"enable": False},
    }
    f_fatigue = compute_fatigue_degrad(hist_fat, fatigue_cfg)
    eel, ed, eh = compute_energy(
        inp, u, v, damage, hist_alpha, matprop, pffmodel, areas, conn,
        f_fatigue=f_fatigue,
        irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_tri3"},
    )
    base_loss = torch.log10(eel + ed + eh)
    dual = nodal_lumped_dual_area(conn, areas, len(inp))
    node_mask = interior_free_node_mask(inp, ph.domain_extrema.to(inp))
    risk, diag = mechanical_mean_excess_from_fields(
        inp, u, v, damage, matprop, pffmodel, areas, conn,
        node_mask=node_mask, dual_area=dual, scale=args.umax, alpha=args.alpha,
    )
    coefficient = args.target_loss_fraction * abs(float(base_loss.detach())) / float(risk.detach())
    achieved = coefficient * float(risk.detach()) / abs(float(base_loss.detach()))
    if not torch.isfinite(torch.tensor(coefficient)) or coefficient <= 0.0:
        raise RuntimeError(f"invalid coefficient {coefficient}")

    args.output.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(["git", "-C", str(code_root), "rev-parse", "HEAD"], text=True).strip()
    payload = {
        "schema": "rrapinn-g3-smoke-lambda-v1",
        "diagnostic_only": True,
        "training_authorized": False,
        "selection_rule": "lambda * risk = 0.01 * abs(log10(Eel+Ed+Ehist)) at U0.12/c82",
        "target_loss_fraction": args.target_loss_fraction,
        "achieved_loss_fraction": achieved,
        "alpha": args.alpha,
        "scale": args.umax,
        "base_loss": float(base_loss.detach()),
        "energies": {"elastic": float(eel.detach()), "damage": float(ed.detach()), "history": float(eh.detach())},
        "risk_mean_excess": float(risk.detach()),
        "risk_threshold": float(diag["threshold"]),
        "frozen_lambda": coefficient,
        "assets": {name: {"path": str(path), "sha256": actual[name]} for name, path in assets.items()},
        "code": {"root": str(code_root), "head": commit},
        "claim_boundary": "Smoke canary scale only; not an efficacy-tuned RRaPINN weight.",
    }
    (args.output / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
