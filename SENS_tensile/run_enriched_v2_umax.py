#!/usr/bin/env python3
"""
run_enriched_v2_umax.py — Enriched Ansatz v2 (STRONGER) variant of
run_enriched_umax.py.

Hyperparameter changes vs v1:
    c_init   : 0.01 → 0.1     (10× stronger initial K_I)
    r_cutoff : 0.1 → 0.05     (tighter singular localization, ≈ 5·l₀)
All other config matches v1 exactly (Mode I, Carrara, no spAlphaT, no
psi_hack, no Williams, seed=1, 8×400 TrainableReLU coeff=1.0).

Usage:
    python run_enriched_v2_umax.py <U_max>

Archive dir auto-named:
    hl_8_..._Umax<UMAX>_enriched_ansatz_modeI_v2_cinit0.1_rcut0.05/

Purpose: test whether the Enriched-Ansatz family has headroom beyond v1.
If v2 breaks ᾱ_max past 10 or pushes N_f toward FEM (82), Enriched is
worth double-downing (v2 5-Umax sweep). If v2 stays at ~10 ceiling, the
Enriched family is capped — pivot to C2/C4 architectural candidates.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Enriched Ansatz v2 STRONGER runner (one U_max).")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (e.g., 0.08, 0.09, 0.10, 0.11, 0.12).")
args = parser.parse_args()

if not (0.05 <= args.umax <= 0.20):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")

# --- Inject CLI args for main.py / config.py argv parsing --------------------
sys.argv = [
    "run_enriched_v2_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# --- Override config dicts ---------------------------------------------------
import config  # noqa: E402
import torch   # noqa: E402

# Enriched v2 STRONGER params — the only change vs v1 runner
V2_C_INIT   = 0.1
V2_R_CUTOFF = 0.05

config.ansatz_dict["enable"]   = True
config.ansatz_dict["x_tip"]    = 0.0
config.ansatz_dict["y_tip"]    = 0.0
config.ansatz_dict["r_cutoff"] = V2_R_CUTOFF      # was 0.1
config.ansatz_dict["nu"]       = 0.3
config.ansatz_dict["c_init"]   = V2_C_INIT        # was 0.01
config.ansatz_dict["modes"]    = ["I"]

config.williams_dict["enable"] = False

config.fatigue_dict["accum_type"]                = "carrara"
config.fatigue_dict["degrad_type"]               = "asymptotic"
config.fatigue_dict["alpha_T"]                   = 0.5
config.fatigue_dict["disp_max"]                  = float(args.umax)
config.fatigue_dict["n_cycles"]                  = 300
config.rebuild_disp_cyclic()  # ★ Apr 25 bugfix: rebuild loading vector after dict mutation
config.fatigue_dict["R_ratio"]                   = 0.0
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False

# --- Rebuild archive path with v2 tag ---------------------------------------
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on"
    f"_{_fat['accum_type']}"
    f"_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}"
    f"_N{_fat['n_cycles']}"
    f"_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_ansatz_tag = f"_enriched_ansatz_modeI_v2_cinit{V2_C_INIT}_rcut{V2_R_CUTOFF}"
_williams_tag = ""
_spAlphaT_tag = ""
_psiHack_tag  = ""

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
print("Enriched Ansatz v2 STRONGER")
print(f"  U_max     = {args.umax}")
print(f"  c_init    = {V2_C_INIT}   (v1 was 0.01)")
print(f"  r_cutoff  = {V2_R_CUTOFF}  (v1 was 0.1)")
print(f"  archive   = {_dir_name}")
print(f"  device    = {config.device}")
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
