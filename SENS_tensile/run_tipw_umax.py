#!/usr/bin/env python3
"""
run_tipw_umax.py — Tip-weighted loss runner at a given U_max.

Tip weighting (Direction 3 of the architecture sweep) re-weights per-element
loss contributions by tip ψ⁺ ratio:

    w_e = 1 + beta * (psi_e / psi_mean) ** power

so elements near the crack tip (where ψ⁺ is high) get larger contribution to
the Deep Ritz loss, in the hope NN allocates more representational capacity
there. Direction 3 was a NEGATIVE result in the original Mac Apr-15 run; this
runner exists for clean reproduction with current bugfixed runner pattern
(rebuild_disp_cyclic + manual path rebuild + model_settings.txt write).

Usage:
    python run_tipw_umax.py <U_max> [--beta B] [--power P] [--start-cycle C]
                                    [--n-cycles N]
    # e.g.:
    python run_tipw_umax.py 0.12 --beta 2.0 --power 1.0

Config overrides:
- tip_weight_cfg.enable      = True
- tip_weight_cfg.beta        = CLI (default 2.0)
- tip_weight_cfg.power       = CLI (default 1.0)
- tip_weight_cfg.start_cycle = CLI (default 1)
- accum_type                 = 'carrara'  (NOT golahmar)
- spatial_alpha_T.enable     = False
- williams_dict.enable       = False
- ansatz_dict.enable         = False  (baseline architecture)
- psi_hack.enable            = False
- fatigue_dict.disp_max      = CLI

Archive dir auto-tagged:
    hl_8_..._Umax<UMAX>_tipw_b<BETA>_p<POWER>/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Tip-weighted loss runner (one U_max).")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (e.g., 0.08, 0.10, 0.12).")
parser.add_argument("--beta", type=float, default=2.0,
                    help="Tip-weighting strength (default 2.0; 0 = uniform).")
parser.add_argument("--power", type=float, default=1.0,
                    help="ψ⁺ ratio exponent (default 1.0 = linear; 2.0 = squared).")
parser.add_argument("--start-cycle", type=int, default=1,
                    help="Cycle at which weighting kicks in (default 1).")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300).")
args = parser.parse_args()

if not (0.05 <= args.umax <= 0.20):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_tipw_umax.py",
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

# Fatigue: clean Carrara baseline + tipw ON
config.fatigue_dict["accum_type"]                = "carrara"
config.fatigue_dict["degrad_type"]               = "asymptotic"
config.fatigue_dict["alpha_T"]                   = 0.5
config.fatigue_dict["disp_max"]                  = float(args.umax)
config.fatigue_dict["n_cycles"]                  = int(args.n_cycles)
config.rebuild_disp_cyclic()  # ★ Apr 25 bugfix: rebuild loading vector after dict mutation
config.fatigue_dict["R_ratio"]                   = 0.0
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False

# Tip-weighted loss
config.fatigue_dict["tip_weight_cfg"]["enable"]      = True
config.fatigue_dict["tip_weight_cfg"]["beta"]        = float(args.beta)
config.fatigue_dict["tip_weight_cfg"]["power"]       = float(args.power)
config.fatigue_dict["tip_weight_cfg"]["start_cycle"] = int(args.start_cycle)

# --- Rebuild archive path with tipw tag --------------------------------------
_fat = config.fatigue_dict
_tw  = _fat["tip_weight_cfg"]
_fatigue_tag = (
    f"_fatigue_on"
    f"_{_fat['accum_type']}"
    f"_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}"
    f"_N{_fat['n_cycles']}"
    f"_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_tipw_tag = f"_tipw_b{_tw['beta']}_p{_tw['power']}"

_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _tipw_tag
)

_PATH_ROOT = HERE
config.model_path             = _PATH_ROOT / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# Re-write model_settings.txt in the corrected archive path
with open(config.model_path / Path("model_settings.txt"), "w") as f:
    f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
    f.write(f"\nneurons: {config.network_dict['neurons']}")
    f.write(f"\nseed: {config.network_dict['seed']}")
    f.write(f"\nactivation: {config.network_dict['activation']}")
    f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
    f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
    f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
    f.write(f"\ndisp_max: {_fat['disp_max']}")
    f.write(f"\nn_cycles: {_fat['n_cycles']}")
    f.write(f"\naccum_type: {_fat['accum_type']}")
    f.write(f"\ndegrad_type: {_fat['degrad_type']}")
    f.write(f"\nalpha_T: {_fat['alpha_T']}")
    f.write(f"\nR_ratio: {_fat['R_ratio']}")
    f.write(f"\ntipw_beta: {_tw['beta']}")
    f.write(f"\ntipw_power: {_tw['power']}")
    f.write(f"\ntipw_start_cycle: {_tw['start_cycle']}")
    f.write(f"\n[runner] run_tipw_umax.py")

print("=" * 72)
print("Tip-weighted loss runner")
print(f"  U_max        = {args.umax}")
print(f"  beta         = {args.beta}")
print(f"  power        = {args.power}")
print(f"  start_cycle  = {args.start_cycle}")
print(f"  n_cycles     = {args.n_cycles}")
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
