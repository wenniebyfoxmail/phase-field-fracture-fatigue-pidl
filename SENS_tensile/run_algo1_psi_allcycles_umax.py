#!/usr/bin/env python3
"""run_algo1_psi_allcycles_umax.py — Experiment 2: Algo1 + ψ⁺ supervision ALL cycles, no C4.

Difference from Exp 1 (run_algo1_mit8_noc4_umax.py):
  - K = n_cycles (supervision never released; runs as long as FEM data exists)
  - Algorithm 1 REQUIRED: without it, λ_sup=1 with full-cycle supervision
    is likely to overwhelm the physics loss and overfit FEM data.

Hypothesis: if gradient imbalance (not architectural constraint) was the real
reason prior supervision experiments failed post-release, then continuous
supervision + Algo1 auto-balancing should sustain crack propagation throughout.

Usage:
    python run_algo1_psi_allcycles_umax.py 0.12 --n-cycles 100 --seed 1
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("umax", type=float)
parser.add_argument("--n-cycles", type=int, default=100)
parser.add_argument("--seed", type=int, default=1)
parser.add_argument("--lam-init", type=float, default=1.0)
parser.add_argument("--algo1-alpha", type=float, default=0.9)
parser.add_argument("--algo1-every", type=int, default=10)
parser.add_argument("--loss-kind", default="mse_log",
                    choices=["mse_log", "mse_lin", "mse_rel"])
parser.add_argument("--supervised-every", type=int, default=1)
args = parser.parse_args()

if args.umax not in (0.08, 0.12):
    raise SystemExit(f"umax={args.umax} has no FEM snapshots. Use 0.08 or 0.12.")

sys.argv = ["run_algo1_psi_allcycles_umax.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import torch, numpy as np
import config

# ── Architecture: no C4, no Fourier ─────────────────────────────────────────
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
    + f"_algo1_psiAll_lam{args.lam_init}_a{args.algo1_alpha}"
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

with open(config.model_path / "model_settings.txt", "w") as f:
    f.write(f"runner: run_algo1_psi_allcycles_umax.py\n")
    f.write(f"umax: {args.umax}\nK: all_cycles (={args.n_cycles})\n")
    f.write(f"lam_init: {args.lam_init}\nalgo1_alpha: {args.algo1_alpha}\n")
    f.write(f"algo1_every: {args.algo1_every}\nn_cycles: {args.n_cycles}\nseed: {args.seed}\n")
    f.write(f"C4: False\nFourier: False\n")

from fem_supervision import FEMSupervision
from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from model_train import train

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict,
    fourier_dict=config.fourier_dict)

fem_sup = FEMSupervision(umax=args.umax)
inp_tmp, T_conn_tmp, _, _ = prep_input_data(
    matprop, pffmodel, config.crack_dict, config.numr_dict,
    mesh_file=config.fine_mesh_file, device=config.device)
inp_np = inp_tmp.detach().cpu().numpy()
T_np   = T_conn_tmp.cpu().numpy() if torch.is_tensor(T_conn_tmp) else T_conn_tmp
cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
pidl_centroids = np.column_stack([cx, cy])

# K = n_cycles — supervision active for all cycles where FEM data exists
# FEMSupervision silently skips cycles beyond available data (nearest-neighbor interp)
mit8_dict = {
    "enable": True,
    "K": int(args.n_cycles),   # never release
    "lambda": float(args.lam_init),
    "fem_sup": fem_sup,
    "pidl_centroids": pidl_centroids,
    "loss_kind": args.loss_kind,
    "every_n_epochs": int(args.supervised_every),
    "target_kind": "psi",
}

grad_annealing_state = {
    "enable": True,
    "alpha_mom": float(args.algo1_alpha),
    "update_every": int(args.algo1_every),
    "lambda_sup": float(args.lam_init),
    "lambda_sym": 1.0,
    "lambda_strac": 1.0,
    "_step": 0,
}

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
print("Experiment 2: Algorithm 1 + ψ⁺ supervision ALL cycles, no C4")
print(f"  umax={args.umax} | K=all ({args.n_cycles}) | lam_init={args.lam_init}")
print(f"  algo1_α={args.algo1_alpha} | update_every={args.algo1_every}")
print(f"  n_cycles={args.n_cycles} | seed={args.seed}")
print(f"  FEM data available: {sorted(fem_sup.cycles)[:5]} ... (auto-extend)")
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
    mit8_dict=mit8_dict,
    grad_annealing_state=grad_annealing_state,
)
