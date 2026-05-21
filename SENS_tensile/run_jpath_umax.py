#!/usr/bin/env python3
"""run_jpath_umax.py — J-integral path-independence regulariser (no FEM target).

For a valid elastic field, the J-integral is contour-independent. We compute J
on several circular contours around the crack tip and penalise their spread
(squared coefficient of variation). This is a SELF-CONSISTENCY regulariser — no
FEM supervision — that pushes the near-tip field toward LEFM-consistent
behaviour, improving tip-field quality without imposing the unlearnable pointwise
ψ⁺ singularity that pointwise-ψ⁺ supervision suffers from.

Architecture: plain (no C4, no Fourier, no supervision, no IS).

Usage:
    python run_jpath_umax.py 0.12 --n-cycles 50 --seed 1 --lambda-j 0.1
    python run_jpath_umax.py 0.12 --n-cycles 50 --seed 1 --lambda-j 0.5 --n-theta 150
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("umax", type=float)
parser.add_argument("--n-cycles", type=int, default=50)
parser.add_argument("--seed", type=int, default=1)
parser.add_argument("--lambda-j", type=float, default=0.1,
                    help="Weight of the J path-independence penalty (default 0.1).")
parser.add_argument("--n-theta", type=int, default=100,
                    help="Contour discretisation points per radius (default 100).")
args = parser.parse_args()

sys.argv = ["run_jpath_umax.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import torch
import config

# ── Architecture: plain, no C4/Fourier/supervision ──────────────────────────
config.exact_bc_dict["enable"]          = False
config.fourier_dict["enable"]           = False
config.williams_dict["enable"]          = False
config.ansatz_dict["enable"]            = False
config.adaptive_sampling_dict["enable"] = False
config.fatigue_dict["tip_weight_cfg"]["enable"]    = False
config.fatigue_dict["spatial_alpha_T"]["enable"]   = False
config.fatigue_dict["psi_hack"]["enable"]          = False

config.fatigue_dict["disp_max"]          = float(args.umax)
config.fatigue_dict["n_cycles"]          = int(args.n_cycles)
config.fatigue_dict["enable_E_fallback"] = False
config.rebuild_disp_cyclic()

_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + f"_jpath_lam{args.lambda_j}_nt{args.n_theta}"
)
config.model_path             = config.resolve_archive_dir(HERE, _dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

with open(config.model_path / "model_settings.txt", "w") as f:
    f.write("runner: run_jpath_umax.py\n")
    f.write(f"umax: {args.umax}\nn_cycles: {args.n_cycles}\nseed: {args.seed}\n")
    f.write(f"lambda_j: {args.lambda_j}\nn_theta: {args.n_theta}\n")
    f.write("C4: False\nFourier: False\nsupervision: False\n")
    f.write("jpath: ACTIVE (J-integral path-independence regulariser)\n")

j_path_dict = {
    "enable": True,
    "lambda": float(args.lambda_j),
    "radii": (0.05, 0.08, 0.12),    # 5ℓ, 8ℓ, 12ℓ — outside the damage band
    "n_theta": int(args.n_theta),
    "x_tip": 0.0,                    # contour centre (initial tip)
}

from construct_model import construct_model
from field_computation import FieldComputation
from model_train import train

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict,
    fourier_dict=config.fourier_dict)

field_comp = FieldComputation(
    net=network, domain_extrema=config.domain_extrema,
    lmbda=torch.tensor([0.0], device=config.device),
    theta=config.loading_angle,
    alpha_constraint=config.numr_dict["alpha_constraint"],
    williams_dict=config.williams_dict,
    l0=config.mat_prop_dict["l0"],
    exact_bc_dict=config.exact_bc_dict)
field_comp.net = field_comp.net.to(config.device)
field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
field_comp.theta = field_comp.theta.to(config.device)

print("=" * 72)
print("J-integral path-independence regulariser (no FEM target)")
print(f"  umax={args.umax} | lambda_j={args.lambda_j} | n_theta={args.n_theta}")
print(f"  radii={j_path_dict['radii']} | n_cycles={args.n_cycles} | seed={args.seed}")
print(f"  archive: {_dir_name}")
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
    j_path_dict=j_path_dict,
)
