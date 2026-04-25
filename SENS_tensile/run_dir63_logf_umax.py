#!/usr/bin/env python3
"""
run_dir63_logf_umax.py — Direction 6.3: logarithmic Carrara f-shape.

Single-knob change: swap fatigue degradation function from Carrara Eq.41
(asymptotic, f never reaches 0) to Carrara Eq.42 (logarithmic, f reaches
0 at finite ᾱ = α_T·10^(1/κ)).

Default κ = 0.5 → finite breaking point ᾱ_c = 0.5 · 10² = 50, comfortably
above all observed PIDL ceilings (~10) but reachable in principle.

All other config matches baseline coeff=1.0 8×400 TrainableReLU exactly:
- No Williams, no Enriched, no spAlphaT, no psi_hack
- accum_type='carrara' (linear ᾱ accumulator, baseline)
- α_T = 0.5

Usage:
    python run_dir63_logf_umax.py <U_max> [--kappa 0.5]

Archive dir auto-named:
    hl_8_..._Umax<UMAX>_logf_kappa<KAPPA>/

Purpose: chain-segment audit MIT — fills the 0-experiment gap on f(ᾱ)
segment. Two clean predictions:
    - If ᾱ_max ceiling stays at ~10  →  f-shape NOT a bottleneck;
      MIT-4 temporal-sharpness diagnosis confirmed (the bottleneck is
      upstream of f).
    - If ᾱ_max breaks past 10        →  f-shape IS a bottleneck;
      Apr 25 mechanism reframe needs further revision.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Dir 6.3 logarithmic-f runner (one U_max).")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (e.g., 0.08, 0.09, 0.10, 0.11, 0.12).")
parser.add_argument("--kappa", type=float, default=0.5,
                    help="Logarithmic-f decay rate (ᾱ_c = α_T·10^(1/κ)). Default 0.5 → ᾱ_c=50.")
args = parser.parse_args()

if not (0.05 <= args.umax <= 0.20):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")
if not (0.1 <= args.kappa <= 5.0):
    raise SystemExit(f"kappa={args.kappa} out of sensible range [0.1, 5.0]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_dir63_logf_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# --- Override config dicts ---------------------------------------------------
import config  # noqa: E402
import torch   # noqa: E402

KAPPA = args.kappa
ALPHA_T = 0.5
ALPHA_CRIT = ALPHA_T * (10.0 ** (1.0 / KAPPA))   # finite breaking ᾱ

# Disable everything else; clean baseline + log-f
config.ansatz_dict["enable"]   = False
config.williams_dict["enable"] = False

config.fatigue_dict["accum_type"]                = "carrara"
config.fatigue_dict["degrad_type"]               = "logarithmic"  # ★ THE CHANGE
config.fatigue_dict["kappa"]                     = KAPPA           # ★ NEW PARAM
config.fatigue_dict["alpha_T"]                   = ALPHA_T
config.fatigue_dict["disp_max"]                  = float(args.umax)
config.fatigue_dict["n_cycles"]                  = 300
config.rebuild_disp_cyclic()  # ★ Apr 25 bugfix: rebuild loading vector after dict mutation
config.fatigue_dict["R_ratio"]                   = 0.0
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False

# --- Rebuild archive path with logf tag --------------------------------------
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on"
    f"_{_fat['accum_type']}"
    f"_{_fat['degrad_type'][:3]}"          # 'log' instead of 'asy'
    f"_aT{_fat['alpha_T']}"
    f"_N{_fat['n_cycles']}"
    f"_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_logf_tag = f"_logf_kappa{KAPPA}"

_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _logf_tag
)

_PATH_ROOT = HERE
config.model_path             = _PATH_ROOT / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("Direction 6.3: Logarithmic Carrara f(ᾱ)")
print(f"  U_max         = {args.umax}")
print(f"  κ (kappa)     = {KAPPA}")
print(f"  α_T           = {ALPHA_T}")
print(f"  ᾱ_crit (f→0) = {ALPHA_CRIT:.1f}      (vs asymptotic baseline never reaches)")
print(f"  archive       = {_dir_name}")
print(f"  device        = {config.device}")
print("=" * 72)

# --- Build model and train ---------------------------------------------------
from field_computation import FieldComputation
from construct_model import construct_model
from model_train import train

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict
)
field_comp = FieldComputation(
    net=network, domain_extrema=config.domain_extrema,
    lmbda=torch.tensor([0.0], device=config.device),
    theta=config.loading_angle,
    alpha_constraint=config.numr_dict["alpha_constraint"],
    williams_dict=config.williams_dict,
    l0=config.mat_prop_dict["l0"],
)
field_comp.net = field_comp.net.to(config.device)
field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
field_comp.theta = field_comp.theta.to(config.device)

active_disp = config.disp_cyclic

train(
    field_comp, active_disp, pffmodel, matprop,
    config.crack_dict, config.numr_dict,
    config.optimizer_dict, config.training_dict,
    config.coarse_mesh_file, config.fine_mesh_file,
    config.device,
    config.trainedModel_path, config.intermediateModel_path,
    config.writer,
    fatigue_dict=config.fatigue_dict,
)
