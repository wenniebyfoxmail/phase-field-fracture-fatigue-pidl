#!/usr/bin/env python3
"""Audit the frozen G4 lambda at c60/c76/c82 peaks without recalibration."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import torch


FROZEN_LAMBDA = 0.000549728557462236
FROZEN_ALPHA = 0.85
MAX_RATIO = 0.05
STEPS = {
    299: {
        "cycle": 60,
        "checkpoint": "2c6d60192e94fa353f7f27f29f910e3710cf5fddf0dd6eada69bd76625d0f72a",
        "model": "5ceffa7057d7726e9c3213774d38631a97ce295876d0cfd7587ab0c3b0e5ba8d",
    },
    379: {
        "cycle": 76,
        "checkpoint": "0e84ac59526fa33699aaab42956a2fcd48f493d3a5463c125b3beb7cec9bf67b",
        "model": "09da9a3f48827dad52859b3150856ad93a4c929e6e6d052b47121aeb343330ac",
    },
    409: {
        "cycle": 82,
        "checkpoint": "581304ad5ac236da6be40c04aa694242c2a1d1ce3e28b45bb070c5a10b36faaa",
        "model": "94e7a3e249fc5b16f850382be9f027d5ff86dccc64b35b94c59458e15683fe00",
    },
}
SETTINGS_SHA256 = "015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047"
MESH_SHA256 = "16b447e3dd789e300f5181c3cf9b34322e4f27575867b354f55473d2969a9ed8"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_rows(rows):
    if [int(row["raw_step"]) for row in rows] != list(STEPS):
        raise ValueError("lambda audit must contain exactly the frozen peak steps")
    for row in rows:
        values = [
            row["base_loss"], row["risk_mean_excess"],
            row["lambda_times_risk"], row["contribution_ratio"],
        ]
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("lambda audit contains a non-finite value")
        if float(row["contribution_ratio"]) > MAX_RATIO:
            raise ValueError("frozen lambda exceeds the 5 percent contribution gate")
    return True


def load_posthoc(code_root: Path):
    path = code_root / "SENS_tensile" / "posthoc_mesh_probe_alignment.py"
    spec = importlib.util.spec_from_file_location("g4_lambda_posthoc", path)
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
    args = ap.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    code_root = args.code_root.resolve()
    archive = args.archive.resolve()
    mesh = args.mesh.resolve()
    settings_path = archive / "model_settings.txt"
    if sha256(settings_path) != SETTINGS_SHA256 or sha256(mesh) != MESH_SHA256:
        raise RuntimeError("frozen settings or mesh hash mismatch")
    for step, expected in STEPS.items():
        for kind, prefix in (("checkpoint", "checkpoint_step_"), ("model", "trained_1NN_")):
            path = archive / "best_models" / f"{prefix}{step}.pt"
            if sha256(path) != expected[kind]:
                raise RuntimeError(f"frozen {kind} hash mismatch at step {step}")

    ph = load_posthoc(code_root)
    sys.path.insert(0, str(code_root / "source"))
    from compute_energy import compute_energy
    from fatigue_history import compute_fatigue_degrad
    from mechanical_residual_risk import (
        interior_free_node_mask,
        mechanical_mean_excess_from_fields,
        nodal_lumped_dual_area,
    )

    settings = ph.parse_settings(settings_path)
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
        lmbda=torch.tensor([0.12], device=ph.DEVICE), theta=ph.loading_angle,
        alpha_constraint=ph.numr_dict["alpha_constraint"], williams_dict=None,
        l0=ph.mat_prop_dict["l0"], exact_bc_dict=ph.exact_bc_from_settings(archive),
        local_patch_dict=ph.local_patch_from_settings(archive),
    )
    dual = nodal_lumped_dual_area(conn, areas, len(inp))
    node_mask = interior_free_node_mask(inp, ph.domain_extrema.to(inp))
    fatigue_cfg = {
        "loading_type": "cyclic", "accum_type": "carrara",
        "degrad_type": "asymptotic", "alpha_T": 0.5,
        "spatial_alpha_T": {"enable": False},
    }
    rows = []
    for step, expected in STEPS.items():
        model_path = archive / "best_models" / f"trained_1NN_{step}.pt"
        checkpoint_path = archive / "best_models" / f"checkpoint_step_{step}.pt"
        field.net.load_state_dict(
            torch.load(model_path, map_location=ph.DEVICE, weights_only=True)
        )
        field.net.eval()
        u, v, damage = field.fieldCalculation(inp)
        state = torch.load(checkpoint_path, map_location=ph.DEVICE, weights_only=False)
        hist_alpha = state["hist_alpha"].to(ph.DEVICE)
        hist_fat = state["hist_fat"].to(ph.DEVICE)
        f_fatigue = compute_fatigue_degrad(hist_fat, fatigue_cfg)
        eel, ed, eh = compute_energy(
            inp, u, v, damage, hist_alpha, matprop, pffmodel, areas, conn,
            f_fatigue=f_fatigue,
            irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_tri3"},
        )
        base_loss = torch.log10(eel + ed + eh)
        risk, diagnostics = mechanical_mean_excess_from_fields(
            inp, u, v, damage, matprop, pffmodel, areas, conn,
            node_mask=node_mask, dual_area=dual, scale=0.12, alpha=FROZEN_ALPHA,
        )
        risk_value = float(risk.detach())
        base_value = float(base_loss.detach())
        contribution = FROZEN_LAMBDA * risk_value
        ratio = contribution / abs(base_value)
        rows.append({
            "raw_step": step,
            "physical_cycle": expected["cycle"],
            "state": "peak_posthoc_checkpoint_state",
            "base_loss": base_value,
            "elastic_energy": float(eel.detach()),
            "damage_energy": float(ed.detach()),
            "history_energy": float(eh.detach()),
            "risk_mean_excess": risk_value,
            "risk_threshold": float(diagnostics["threshold"]),
            "lambda": FROZEN_LAMBDA,
            "lambda_times_risk": contribution,
            "contribution_ratio": ratio,
            "model_sha256": expected["model"],
            "checkpoint_sha256": expected["checkpoint"],
        })
    validate_rows(rows)
    output.mkdir(parents=True, exist_ok=False)
    columns = list(rows[0])
    with (output / "lambda_trajectory.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "schema": "rrapinn-g4-lambda-trajectory-audit-v1",
        "diagnostic_only": True,
        "training_authorized": False,
        "development_case": "U0.12",
        "fixed_lambda": FROZEN_LAMBDA,
        "alpha": FROZEN_ALPHA,
        "maximum_contribution_ratio": MAX_RATIO,
        "status": "PASS" if max(row["contribution_ratio"] for row in rows) <= MAX_RATIO else "FAIL",
        "rows": rows,
        "assets": {"settings_sha256": SETTINGS_SHA256, "mesh_sha256": MESH_SHA256},
        "claim_boundary": (
            "Posthoc contribution audit only; no lambda retuning and no efficacy claim. "
            "Energy terms use each peak's post-step checkpoint history state."
        ),
    }
    with (output / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
