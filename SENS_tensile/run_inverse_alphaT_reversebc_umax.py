#!/usr/bin/env python3
"""PIDL inverse-alpha_T prototype against reverseBC FEM snapshots.

This runner is deliberately conservative:
  - reverseBC/FEM-anchor essential BC via ``exact_bc_mode=fem_anchor``;
  - fixed Deep Ritz / irreversibility weighting;
  - no adaptive residual reweighting, sidecar sampling, tip weighting, or
    spatial alpha_T;
  - ``alpha_T`` is the only trainable physical scalar.

The first useful run should be a producer-side smoke/short run. Do not run the
training loop on Mac.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _bool_mask_from_kind(kind, pidl_centroids, *, x_min, y_abs_max):
    if kind == "full":
        return None

    import torch

    cx = torch.from_numpy(pidl_centroids[:, 0])
    cy = torch.from_numpy(pidl_centroids[:, 1])
    if kind == "boundary":
        return cx >= x_min
    if kind == "crack_path":
        return (cy.abs() <= y_abs_max) & (cx >= 0.0)
    if kind == "boundary_or_crack":
        return (cx >= x_min) | ((cy.abs() <= y_abs_max) & (cx >= 0.0))
    raise ValueError(f"unknown mask kind {kind!r}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float, default=0.12)
    p.add_argument("--n-cycles", type=int, default=90)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--alphaT-init", type=float, default=0.25)
    p.add_argument("--alphaT-min", type=float, default=0.05)
    p.add_argument("--alphaT-max", type=float, default=2.0)
    p.add_argument("--K", type=int, default=74,
                   help="Last cycle with FEM observation loss active.")
    p.add_argument("--lambda-alpha", type=float, default=1.0)
    p.add_argument("--supervised-every", type=int, default=10,
                   help="Apply observation loss every N optimizer epochs.")
    p.add_argument("--fem-dir", default="",
                   help="Folder containing reverseBC u12_reverseBC_cycle_*.mat and mesh_geometry.mat.")
    p.add_argument("--mask-kind", default="boundary_or_crack",
                   choices=["full", "boundary", "crack_path", "boundary_or_crack"])
    p.add_argument("--mask-x-min", type=float, default=0.45)
    p.add_argument("--mask-y-abs-max", type=float, default=0.05)
    args = p.parse_args()

    sys.argv = [
        "run_inverse_alphaT_reversebc_umax.py",
        "8", "400", str(args.seed), "TrainableReLU", "1.0",
    ]

    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import numpy as np
    import torch
    import config
    from construct_model import construct_model
    from fem_supervision import FEMSupervision
    from field_computation import FieldComputation
    from input_data_from_mesh import prep_input_data
    from model_train import train

    # ReverseBC/FEM-anchor baseline. Keep E_irrev and all loss weights fixed.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = True
    config.exact_bc_dict["mode"] = "fem_anchor"
    config.symmetry_prior = False
    config.adaptive_sampling_dict["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict.pop("symmetry_soft", None)
    config.fatigue_dict.pop("side_traction_soft", None)

    config.fatigue_dict["accum_type"] = "carrara"
    config.fatigue_dict["degrad_type"] = "asymptotic"
    config.fatigue_dict["alpha_T"] = 0.5  # reference value; train() replaces it with a scalar module
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["enable_E_fallback"] = False
    config.fatigue_dict["fracture_confirm_cycles"] = 10
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aTlearnInit{args.alphaT_init:g}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    inv_tag = (
        f"_inverseAlphaT_reverseBC_K{args.K}_lamA{args.lambda_alpha:g}"
        f"_mask{args.mask_kind}_fixedEirrev"
    )
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + inv_tag
    )

    config.model_path = config.resolve_archive_dir(here, dir_name)
    config.trainedModel_path = config.model_path / Path("best_models/")
    config.intermediateModel_path = config.model_path / Path("intermediate_models/")
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))

    fem_dir = Path(args.fem_dir).expanduser() if args.fem_dir else None
    fem_sup = FEMSupervision(umax=float(args.umax), fem_dir=fem_dir)

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
        config.domain_extrema, config.device,
        williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict,
    )
    inp_tmp, t_conn_tmp, _, _ = prep_input_data(
        matprop, pffmodel, config.crack_dict, config.numr_dict,
        mesh_file=config.fine_mesh_file, device=config.device,
    )
    inp_np = inp_tmp.detach().cpu().numpy()
    t_np = t_conn_tmp.cpu().numpy() if torch.is_tensor(t_conn_tmp) else t_conn_tmp
    cx = (inp_np[t_np[:, 0], 0] + inp_np[t_np[:, 1], 0] + inp_np[t_np[:, 2], 0]) / 3.0
    cy = (inp_np[t_np[:, 0], 1] + inp_np[t_np[:, 1], 1] + inp_np[t_np[:, 2], 1]) / 3.0
    pidl_centroids = np.column_stack([cx, cy])
    obs_mask = _bool_mask_from_kind(
        args.mask_kind,
        pidl_centroids,
        x_min=args.mask_x_min,
        y_abs_max=args.mask_y_abs_max,
    )

    mit8_dict = {
        "enable": True,
        "K": int(args.K),
        "lambda": float(args.lambda_alpha),
        "fem_sup": fem_sup,
        "pidl_centroids": pidl_centroids,
        "loss_kind": "mse_lin",
        "every_n_epochs": int(args.supervised_every),
        "mask": obs_mask,
        "target_kind": "alpha",
    }
    inverse_dict = {
        "enable": True,
        "target": "alpha_T",
        "initial_value": float(args.alphaT_init),
        "min_value": float(args.alphaT_min),
        "max_value": float(args.alphaT_max),
    }

    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema,
        lmbda=torch.tensor([0.0], device=config.device),
        theta=config.loading_angle,
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=config.williams_dict,
        ansatz_dict=config.ansatz_dict,
        l0=config.mat_prop_dict["l0"],
        symmetry_prior=config.symmetry_prior,
        exact_bc_dict=config.exact_bc_dict,
    )
    field_comp.net = field_comp.net.to(config.device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
    field_comp.theta = field_comp.theta.to(config.device)

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as f:
        f.write("runner: run_inverse_alphaT_reversebc_umax.py\n")
        f.write("purpose: reverseBC FEM inverse alpha_T prototype\n")
        f.write("exact_bc_mode: fem_anchor\n")
        f.write("fixed_E_irrev: true\n")
        f.write(f"adaptive_sampling: {config.adaptive_sampling_dict['enable']}\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"alphaT_init: {args.alphaT_init}\n")
        f.write(f"alphaT_bounds: [{args.alphaT_min}, {args.alphaT_max}]\n")
        f.write(f"fem_dir: {fem_sup.fem_dir}\n")
        f.write(f"fem_cycles: {fem_sup.cycles}\n")
        f.write(f"obs_target: alpha\n")
        f.write(f"obs_lambda: {args.lambda_alpha}\n")
        f.write(f"obs_K: {args.K}\n")
        f.write(f"obs_mask_kind: {args.mask_kind}\n")

    n_mask = "full" if obs_mask is None else f"{int(obs_mask.sum().item())}/{len(obs_mask)}"
    print("=" * 72)
    print("PIDL inverse-alpha_T prototype against reverseBC FEM")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  alpha_T init/bounds = {args.alphaT_init} / [{args.alphaT_min}, {args.alphaT_max}]")
    print(f"  BC          = exact_bc fem_anchor (reverseBC-compatible)")
    print("  E_irrev     = fixed weighting; no adaptive residual/lambda balancing")
    print(f"  FEM dir     = {fem_sup.fem_dir}")
    print(f"  FEM cycles  = {fem_sup.cycles}")
    print(f"  obs         = alpha target, K={args.K}, lambda={args.lambda_alpha}, mask={n_mask}")
    print(f"  archive     = {dir_name}")
    print("=" * 72)

    train(
        field_comp, config.disp_cyclic, pffmodel, matprop,
        config.crack_dict, config.numr_dict,
        config.optimizer_dict, config.training_dict,
        config.coarse_mesh_file, config.fine_mesh_file,
        config.device,
        config.trainedModel_path, config.intermediateModel_path,
        config.writer,
        fatigue_dict=config.fatigue_dict,
        mit8_dict=mit8_dict,
        inverse_dict=inverse_dict,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
