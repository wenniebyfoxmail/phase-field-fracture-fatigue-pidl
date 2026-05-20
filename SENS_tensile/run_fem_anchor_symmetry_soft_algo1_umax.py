#!/usr/bin/env python3
"""run_fem_anchor_symmetry_soft_algo1_umax.py — FEM-anchor BC + soft symmetry + Wang Algo1.

This is the gradient-balanced counterpart to run_fem_anchor_symmetry_soft_umax.py.
It keeps the same soft mirror-symmetry penalties, but enables Wang, Teng &
Perdikaris (2020) Algorithm 1 so lambda_sym is adapted from gradient statistics.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--lam-alpha", type=float, default=1.0)
    p.add_argument("--lam-u", type=float, default=1.0)
    p.add_argument("--lam-v", type=float, default=1.0)
    p.add_argument("--algo1-alpha", type=float, default=0.9)
    p.add_argument("--algo1-every", type=int, default=10)
    p.add_argument("--lambda-sym-init", type=float, default=1.0)
    args = p.parse_args()

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.symmetry_prior = False
    config.exact_bc_dict["enable"] = True
    config.exact_bc_dict["mode"] = "fem_anchor"

    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.rebuild_disp_cyclic()

    config.fatigue_dict["symmetry_soft"] = {
        "enable": True,
        "lambda_alpha": float(args.lam_alpha),
        "lambda_u": float(args.lam_u),
        "lambda_v": float(args.lam_v),
    }

    grad_annealing_state = {
        "enable": True,
        "alpha_mom": float(args.algo1_alpha),
        "update_every": int(args.algo1_every),
        "lambda_sup": 1.0,
        "lambda_sym": float(args.lambda_sym_init),
        "lambda_strac": 1.0,
        "_step": 0,
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sym_tag = (
        f"_femAnchorBC_symSoftAlgo1_la{args.lam_alpha}_lu{args.lam_u}_lv{args.lam_v}"
        f"_a{args.algo1_alpha}_ev{args.algo1_every}"
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
        + sym_tag
    )
    config.model_path = here / Path(dir_name)
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

    with open(config.model_path / Path("model_settings.txt"), "w") as f:
        f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
        f.write(f"\nneurons: {config.network_dict['neurons']}")
        f.write(f"\nseed: {config.network_dict['seed']}")
        f.write(f"\nactivation: {config.network_dict['activation']}")
        f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
        f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
        f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
        f.write(f"\ntol_ir: {config.PFF_model_dict['tol_ir']}")
        f.write(f"\nexact_bc_enable: {config.exact_bc_dict['enable']}")
        f.write(f"\nexact_bc_mode: {config.exact_bc_dict['mode']}")
        f.write(f"\nsymmetry_prior: {config.symmetry_prior}")
        f.write(f"\nsymmetry_soft: {config.fatigue_dict['symmetry_soft']}")
        f.write(f"\ngrad_annealing_state: {grad_annealing_state}")
        f.write(f"\ndisp_max: {fat['disp_max']}")
        f.write(f"\nn_cycles: {fat['n_cycles']}")
        f.write(f"\naccum_type: {fat['accum_type']}")
        f.write(f"\ndegrad_type: {fat['degrad_type']}")
        f.write(f"\nalpha_T: {fat['alpha_T']}")
        f.write(f"\nR_ratio: {fat['R_ratio']}")
        f.write("\n[runner] run_fem_anchor_symmetry_soft_algo1_umax.py")

    print("=" * 72)
    print("Controlled alignment: FEM-anchor BC + soft symmetry + Wang Algo1")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  symmetry  = soft la={args.lam_alpha}, lu={args.lam_u}, lv={args.lam_v}")
    print(f"  Algo1     = alpha={args.algo1_alpha}, every={args.algo1_every}, lambda_sym_init={args.lambda_sym_init}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    from construct_model import construct_model
    from field_computation import FieldComputation
    from model_train import train
    import torch

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
        config.domain_extrema, config.device,
        williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict)

    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema,
        lmbda=torch.tensor([0.0], device=config.device),
        theta=config.loading_angle,
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=config.williams_dict,
        l0=config.mat_prop_dict["l0"],
        exact_bc_dict=config.exact_bc_dict)
    field_comp.net = field_comp.net.to(config.device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
    field_comp.theta = field_comp.theta.to(config.device)

    train(
        field_comp, config.disp_cyclic, pffmodel, matprop,
        config.crack_dict, config.numr_dict,
        config.optimizer_dict, config.training_dict,
        config.coarse_mesh_file, config.fine_mesh_file,
        config.device,
        config.trainedModel_path, config.intermediateModel_path,
        config.writer,
        fatigue_dict=config.fatigue_dict,
        grad_annealing_state=grad_annealing_state,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
