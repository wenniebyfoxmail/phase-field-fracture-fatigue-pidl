#!/usr/bin/env python3
"""
run_psi_hack_umax.py — Runner for E2 ψ⁺ hack at a given U_max.

Reusable wrapper around Mac's one-off E2 experiment (which warm-started
from baseline cycle 50 at Umax=0.12). This version is **cold-start**
(cycle 0), so other machines (Windows, CSD3) can reproduce without
needing a pre-trained baseline archive.

Usage:
    python run_psi_hack_umax.py <U_max>
    # e.g.:
    python run_psi_hack_umax.py 0.08
    python run_psi_hack_umax.py 0.10

Config overrides (all applied in-memory; config.py untouched):
- psi_hack.enable        = True
- psi_hack.mult          = 1000,  r_hack = 0.02,  x_tip = (0, 0)
- accum_type             = 'carrara'   (NOT golahmar)
- spatial_alpha_T.enable = False
- williams_dict.enable   = False
- ansatz_dict.enable     = False       (baseline architecture; no Enriched)
- fatigue_dict.disp_max  = CLI arg

Archive dir auto-tagged:
    hl_8_..._Umax<UMAX>_psiHack_m1000_r0.02/

Safety notes:
- psi_hack only affects get_psi_plus_per_elem (fed to fatigue accumulator).
  The Deep Ritz training loss uses a separate compute_energy path and does
  NOT see the amplified ψ⁺. NN training dynamics are therefore unchanged;
  only the ᾱ accumulation receives the amplified driver.
- Cold start from cycle 0 is safe: pretraining (no fatigue) runs first,
  so when cyclic loading starts, the NN already has a sensible field.

Purpose (for paper):
Gives the "theoretical upper bound" point on the S-N curve at the given
U_max — i.e., what α accumulation would look like if PIDL could represent
FEM-level tip ψ⁺ concentration. Compared against baseline and Enriched
S-N curves to show how much of the gap any ψ⁺-concentration method could
in principle close.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="E2 ψ⁺ hack cold-start runner (one U_max).")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (e.g., 0.08, 0.09, 0.10, 0.11).")
parser.add_argument("--mult", type=float, default=1000.0,
                    help="Gaussian amplifier at tip (default 1000).")
parser.add_argument("--r_hack", type=float, default=0.02,
                    help="Gaussian localization length (default 0.02 ≈ 2l₀).")
args = parser.parse_args()

if not (0.05 <= args.umax <= 0.20):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_psi_hack_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# --- Override config dicts ---------------------------------------------------
import config  # noqa: E402
import torch   # noqa: E402

# Architectural toggles: all OFF except plain baseline
config.ansatz_dict["enable"]   = False
config.williams_dict["enable"] = False

# Fatigue: clean Carrara baseline + psi_hack ON
config.fatigue_dict["accum_type"]                = "carrara"
config.fatigue_dict["degrad_type"]               = "asymptotic"
config.fatigue_dict["alpha_T"]                   = 0.5
config.fatigue_dict["disp_max"]                  = float(args.umax)
config.fatigue_dict["n_cycles"]                  = 700    # high-enough ceiling
config.fatigue_dict["R_ratio"]                   = 0.0
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False

# E2 ψ⁺ hack
config.fatigue_dict["psi_hack"]["enable"]     = True
config.fatigue_dict["psi_hack"]["x_tip"]      = 0.0
config.fatigue_dict["psi_hack"]["y_tip"]      = 0.0
config.fatigue_dict["psi_hack"]["r_hack"]     = float(args.r_hack)
config.fatigue_dict["psi_hack"]["multiplier"] = float(args.mult)

# --- Rebuild archive path with psiHack tag ----------------------------------
_fat = config.fatigue_dict
_ph  = _fat["psi_hack"]
_fatigue_tag = (
    f"_fatigue_on"
    f"_{_fat['accum_type']}"
    f"_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}"
    f"_N{_fat['n_cycles']}"
    f"_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_williams_tag = ""
_ansatz_tag   = ""
_spAlphaT_tag = ""
_psiHack_tag  = f"_psiHack_m{int(_ph['multiplier'])}_r{_ph['r_hack']}"

_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _williams_tag
    + _ansatz_tag
    + _spAlphaT_tag
    + _psiHack_tag
)

_PATH_ROOT = HERE
config.model_path             = _PATH_ROOT / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("E2 ψ⁺ hack cold-start (upper-bound S-N probe)")
print(f"  U_max        = {args.umax}")
print(f"  multiplier   = {args.mult}")
print(f"  r_hack       = {args.r_hack}")
print(f"  archive      = {_dir_name}")
print(f"  device       = {config.device}")
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
    ansatz_dict=config.ansatz_dict,
    l0=config.mat_prop_dict["l0"],
)
field_comp.net = field_comp.net.to(config.device)
field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
field_comp.theta = field_comp.theta.to(config.device)
if field_comp.c_singular is not None:
    import torch.nn as _nn
    field_comp.c_singular = _nn.Parameter(
        field_comp.c_singular.data.to(config.device))

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
