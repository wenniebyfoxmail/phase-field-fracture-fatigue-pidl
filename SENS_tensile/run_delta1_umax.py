#!/usr/bin/env python3
"""run_delta1_umax.py — Experiment 3: C6 (δ-1) element-level importance sampling.

δ-1 = true importance sampling at element level (NOT loss reweighting).
  - At end of cycle j: compute residual proxy r_e = |E_el_e| + |E_d_e| per element
  - Normalize: p_e = r_e / sum(r_e)
  - At cycle j+1: sample K elements with replacement from p_e
  - Loss = (1/K) Σ_{e_sampled} (1/p_e) · (E_el_e + E_d_e + E_hist_e)
  - Expectation over mini-batches = full Deep Ritz integral (UNBIASED)

This avoids the covariance-bias catastrophe of C6 α/β/γ (log(Σ w·E) exploded
at cycle 1 because w and E correlated at tip, Kt→1924). δ-1 uses sampling
not reweighting, so the loss formula is UNCHANGED; only WHICH elements enter
each epoch is modulated.

Implementation status (2026-05-20):
  ✅ dataset_element.py — ElementDataset + compute_residual_proxy
  ✅ fit.py             — grad_annealing_state param (Algo1, used here too)
  ✅ model_train.py     — grad_annealing_state param
  🔧 TODO (1-2 days):   compute_energy.py — add element_subset + 1/p_e param
  🔧 TODO (1-2 days):   model_train.py    — element-level DataLoader integration
                         (replace node-level TensorDataset with ElementDataset)

Usage (once TODOs are done):
    python run_delta1_umax.py 0.12 --n-cycles 50 --seed 1 --K-elems 500
    python run_delta1_umax.py 0.12 --n-cycles 100 --seed 1
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("umax", type=float)
parser.add_argument("--n-cycles", type=int, default=100)
parser.add_argument("--seed", type=int, default=1)
parser.add_argument("--K-elems", type=int, default=None,
                    help="Elements per mini-batch epoch. None = n_elem (full IS).")
parser.add_argument("--start-cycle", type=int, default=1,
                    help="First cycle with importance sampling active (default 1).")
parser.add_argument("--algo1-alpha", type=float, default=0.9,
                    help="Algo1 EMA momentum. Algo1 is combined with δ-1 to "
                         "balance physics loss vs any BC terms.")
parser.add_argument("--algo1-every", type=int, default=10)
args = parser.parse_args()

sys.argv = ["run_delta1_umax.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import torch
import config

# ── Architecture: no C4, no Fourier, no old C6 reweight ─────────────────────
config.exact_bc_dict["enable"]          = False
config.fourier_dict["enable"]           = False
config.williams_dict["enable"]          = False
config.ansatz_dict["enable"]            = False
config.adaptive_sampling_dict["enable"] = False   # old C6 reweight disabled
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
_K_tag = f"_K{args.K_elems}" if args.K_elems else "_Kfull"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + f"_delta1{_K_tag}_start{args.start_cycle}"
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

with open(config.model_path / "model_settings.txt", "w") as f:
    f.write(f"runner: run_delta1_umax.py\n")
    f.write(f"umax: {args.umax}\nn_cycles: {args.n_cycles}\nseed: {args.seed}\n")
    f.write(f"K_elems: {args.K_elems}\nstart_cycle: {args.start_cycle}\n")
    f.write(f"C4: False\nFourier: False\nold-C6-reweight: False\n")
    f.write(f"delta1: ACTIVE (element-level IS)\n")

# ── δ-1 dict (passed to model_train when TODO integration is done) ───────────
delta1_dict = {
    "enable": True,
    "samples_per_epoch": args.K_elems,    # None = n_elem (full IS)
    "start_cycle": int(args.start_cycle),
    "residual_source": "full",             # |E_el| + |E_d|
}

# ── Algorithm 1 state (combined with δ-1 for BC-term balancing) ──────────────
grad_annealing_state = {
    "enable": True,
    "alpha_mom": float(args.algo1_alpha),
    "update_every": int(args.algo1_every),
    "lambda_sup": 1.0,
    "lambda_sym": 1.0,
    "lambda_strac": 1.0,
    "_step": 0,
}

print("=" * 72)
print("Experiment 3: C6 δ-1 element-level importance sampling")
print(f"  umax={args.umax} | K_elems={args.K_elems} | start_cycle={args.start_cycle}")
print(f"  n_cycles={args.n_cycles} | seed={args.seed}")
print(f"  archive: {_dir_name}")
print("=" * 72)

# ── STUB: full integration requires compute_energy + model_train changes ──────
# The TODO items are:
#
#   1. compute_energy.compute_energy(element_subset, importance_weights):
#      loss = (1/K) Σ_{e in subset} (1/p_e) · (E_el_e + E_d_e + E_hist_e)
#      When element_subset=None → full batch (backward-compatible).
#
#   2. model_train.train() δ-1 integration:
#      if delta1_dict and delta1_dict.get('enable', False):
#          from dataset_element import ElementDataset, compute_residual_proxy
#          elem_ds = ElementDataset(n_elem)
#          # Main cycle loop:
#          #   a) train with element mini-batches (loader from elem_ds.make_loader())
#          #   b) after training, update p_e:
#          #      proxy = compute_residual_proxy(inp, field_comp, ...)
#          #      elem_ds.update_weights(proxy)
#
# For now, fall back to FULL-BATCH training (same as baseline) to at least
# validate archive naming, checkpoint logic, and δ-1 dict plumbing.

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

print("[δ-1] WARNING: element-level IS not yet wired into model_train.py.")
print("  Running full-batch baseline until compute_energy TODO is done.")
print("  See STUB comment above for integration plan.")

train(
    field_comp, config.disp_cyclic, pffmodel, matprop,
    config.crack_dict, config.numr_dict,
    config.optimizer_dict, config.training_dict,
    config.coarse_mesh_file, config.fine_mesh_file,
    config.device,
    config.trainedModel_path, config.intermediateModel_path,
    config.writer,
    fatigue_dict=config.fatigue_dict,
    # delta1_dict=delta1_dict,       # uncomment after model_train TODO done
    grad_annealing_state=grad_annealing_state,
)
