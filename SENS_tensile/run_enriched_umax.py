#!/usr/bin/env python3
"""
run_enriched_umax.py — Runner for Enriched Ansatz S-N sweep (CSD3 Request 1).

Usage:
    python run_enriched_umax.py <U_max>
    # e.g.:
    python run_enriched_umax.py 0.08
    python run_enriched_umax.py 0.10

Overrides config dicts in memory to force a CLEAN Enriched-Ansatz baseline
regardless of what config.py happens to contain at HEAD. This avoids
requiring CSD3 (producer role) to hand-edit config.py.

The overrides match the Ch2 paper E1 experiment:
- ansatz_dict.enable        = True   (Mode-I r^(1/2) output enrichment)
- williams_dict.enable      = False
- fatigue_dict.accum_type   = 'carrara'   (NOT golahmar)
- fatigue_dict.spatial_alpha_T.enable = False
- fatigue_dict.psi_hack.enable        = False
- fatigue_dict.disp_max     = <U_max>  (per-job CLI argument)
- fatigue_dict.n_cycles     = 700
- fatigue_dict.enable_E_fallback = False (α-boundary primary criterion only)
- network_dict = 8x400 TrainableReLU, coeff=1.0, seed=1
- fatigue_dict.alpha_T = 0.5

Archive dir auto-built by config.py tagging logic:
    hl_8_Neurons_400_..._aT0.5_N700_R0.0_Umax<UMAX>_enriched_ansatz_modeI_v1/

After training, archive should auto-get _cycle<N>_Nf<NN>_real_fracture
suffix via the rename step, matching other archives' naming convention.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Enriched Ansatz S-N runner (one U_max).")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (e.g., 0.08, 0.09, 0.10, 0.11, 0.12).")
args = parser.parse_args()

if not (0.05 <= args.umax <= 0.20):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")

# --- Inject CLI args for main.py / config.py argv parsing --------------------
# config.py + main.py read sys.argv[1:5] = [hidden_layers, neurons, seed,
#   activation, init_coeff]. We set the E1 canonical values and then import.
sys.argv = [
    "run_enriched_umax.py",
    "8",              # hidden_layers
    "400",            # neurons
    "1",              # seed
    "TrainableReLU",  # activation
    "1.0",            # init_coeff
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# --- Override config dicts ---------------------------------------------------
# Importing config applies command-line argv to network_dict; then we stomp
# on the fatigue / ansatz / williams dicts for the E1 canonical state.
import config  # noqa: E402
import torch   # noqa: E402

# Ansatz ON (the method under test)
config.ansatz_dict["enable"]   = True
config.ansatz_dict["x_tip"]    = 0.0
config.ansatz_dict["y_tip"]    = 0.0
config.ansatz_dict["r_cutoff"] = 0.1
config.ansatz_dict["nu"]       = 0.3
config.ansatz_dict["c_init"]   = 0.01
config.ansatz_dict["modes"]    = ["I"]

# Williams input features OFF
config.williams_dict["enable"] = False

# Fatigue: clean Carrara baseline, no Dir 6.x toggles, E2 hack off
config.fatigue_dict["accum_type"]               = "carrara"
config.fatigue_dict["degrad_type"]              = "asymptotic"
config.fatigue_dict["alpha_T"]                  = 0.5
config.fatigue_dict["disp_max"]                 = float(args.umax)
config.fatigue_dict["n_cycles"]                 = 700
config.fatigue_dict["R_ratio"]                  = 0.0
config.fatigue_dict["enable_E_fallback"]        = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False

# Rebuild the archive path tag since we just changed fatigue_dict fields.
# config.py computes model_path at import time based on the dicts as they
# were when first imported. We recompute here for this override.
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
_ansatz_tag = "_enriched_ansatz_modeI_v1"  # ansatz.enable=True, modes=['I']
_williams_tag = ""                          # williams.enable=False
_spAlphaT_tag = ""                          # spatial_alpha_T.enable=False
_psiHack_tag  = ""                          # psi_hack.enable=False

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
config.model_path           = _PATH_ROOT / Path(_dir_name)
config.trainedModel_path    = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print(f"Enriched Ansatz S-N run")
print(f"  U_max      = {args.umax}")
print(f"  archive    = {_dir_name}")
print(f"  n_cycles   = {config.fatigue_dict['n_cycles']}")
print(f"  accum_type = {config.fatigue_dict['accum_type']}")
print(f"  ansatz     = enabled (Mode I, r_cutoff=0.1)")
print(f"  device     = {config.device}")
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

# Loading profile auto-selected by fatigue_on + loading_type
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
