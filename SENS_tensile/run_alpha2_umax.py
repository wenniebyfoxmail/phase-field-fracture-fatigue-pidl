#!/usr/bin/env python3
"""
run_alpha2_umax.py — α-2 multi-head NN with spatial gating
                     (per design_alpha2_multihead_apr28.md, Apr 28)

Closes the (b) STATIONARITY half of the ψ⁺ peak gap via architectural anchoring.
Two-head architecture: main head (smooth far-field) + tip head (anchored at x_tip
via Gaussian spatial gate). Peak stationarity comes from architecture, not loss.

Uses standard legacy mesh (67k triangles). Orthogonal to α-1 mesh refinement;
can be combined later.

All other interventions disabled (williams, ansatz, spAlphaT, psiHack, fem_oracle).

Usage:
    python run_alpha2_umax.py <U_max> [--n-cycles 300]
        [--n-hidden-tip 4] [--neurons-tip 100]
        [--r-g 0.02] [--gate-power 2]

Archive auto-named:
    hl_8_..._N{N}_R0.0_Umax{U}_alpha2_mh{nh_t}x{nn_t}_rg{r_g}/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="α-2 multi-head NN runner.")
parser.add_argument("umax", type=float,
                    help="Loading amplitude. Any positive U_max.")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300, range [10, 5000]).")
parser.add_argument("--n-hidden-tip", type=int, default=4,
                    help="Tip head hidden layers (default 4).")
parser.add_argument("--neurons-tip", type=int, default=100,
                    help="Tip head neurons per layer (default 100).")
parser.add_argument("--r-g", type=float, default=0.02,
                    help="Gate radius r_g (default 0.02 = 2*l0).")
parser.add_argument("--gate-power", type=float, default=2,
                    help="Gate exponent p in exp(-(r/r_g)^p) (default 2).")
parser.add_argument("--no-fatigue", action="store_true",
                    help="Disable fatigue (T2: 1-cycle Deep Ritz sanity check).")
parser.add_argument("--smoke-t2", action="store_true",
                    help="Shortcut: 1 cycle, no-fatigue, nocycle archive tag.")
args = parser.parse_args()

if args.smoke_t2:
    args.n_cycles = 1
    args.no_fatigue = True

if not (1 <= args.n_cycles <= 5000):
    raise SystemExit(f"n_cycles={args.n_cycles} out of [1, 5000]")
if not (0.01 <= args.umax <= 1.0):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.01, 1.0]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_alpha2_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import config           # noqa: E402
import torch            # noqa: E402

# Disable all other interventions
config.ansatz_dict["enable"]   = False
config.williams_dict["enable"] = False

config.fatigue_dict["accum_type"]                = "carrara"
config.fatigue_dict["degrad_type"]               = "asymptotic"
config.fatigue_dict["alpha_T"]                   = 0.5
config.fatigue_dict["disp_max"]                  = float(args.umax)
config.fatigue_dict["n_cycles"]                  = int(args.n_cycles)
config.fatigue_dict["R_ratio"]                   = 0.0
config.fatigue_dict["fatigue_on"]                = not args.no_fatigue
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False
if "fem_oracle" in config.fatigue_dict:
    config.fatigue_dict["fem_oracle"] = {"enable": False}
if config.fatigue_dict["fatigue_on"]:
    config.rebuild_disp_cyclic()
else:
    # T2 smoke: single displacement step
    config.disp_cyclic = [float(args.umax)]

# --- Enable α-2 multihead ---------------------------------------------------
# Inject multihead_dict into config (not present in default config.py)
config.multihead_dict = {
    'enable': True,
    'n_hidden_main': config.network_dict["hidden_layers"],
    'neurons_main': config.network_dict["neurons"],
    'n_hidden_tip': args.n_hidden_tip,
    'neurons_tip': args.neurons_tip,
    'r_g': args.r_g,
    'gate_power': args.gate_power,
    'activation_tip': 'ReLU',
}

# --- Build archive path -----------------------------------------------------
_fat = config.fatigue_dict
if _fat.get('fatigue_on', True):
    _fatigue_tag = (
        f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
        f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
        f"_Umax{_fat['disp_max']}"
    )
else:
    _fatigue_tag = f"_fatigue_off_Umax{_fat['disp_max']}"
_alpha2_tag = (f"_alpha2_mh{args.n_hidden_tip}x{args.neurons_tip}"
               f"_rg{str(args.r_g).replace('.', 'p')}")
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag + _alpha2_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# --- Banner -----------------------------------------------------------------
print("=" * 72)
print("α-2 multi-head NN runner (spatial gating)")
print(f"  U_max         = {args.umax}")
print(f"  n_cycles      = {args.n_cycles}")
print(f"  tip head      = {args.n_hidden_tip}×{args.neurons_tip}")
print(f"  r_g           = {args.r_g}")
print(f"  gate_power    = {args.gate_power}")
print(f"  archive       = {_dir_name}")
print(f"  device        = {config.device}")
print("=" * 72)

# --- Override mesh paths to absolute (config.py uses relative paths) ---------
config.fine_mesh_file   = str(HERE / config.fine_mesh_file)
config.coarse_mesh_file = str(HERE / config.coarse_mesh_file)

# --- Build pipeline + train --------------------------------------------------
from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from model_train import train

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict,
    multihead_dict=config.multihead_dict,
)
print(f"Building input data from {config.fine_mesh_file}…")
inp, T_conn, area_T, _ = prep_input_data(
    matprop, pffmodel, config.crack_dict, config.numr_dict,
    mesh_file=config.fine_mesh_file, device=config.device,
)
print(f"  N collocation points: {len(inp)}")
print(f"  N triangles: {len(T_conn) if T_conn is not None else 'N/A (autodiff)'}")
print(f"  Domain area: {area_T.sum().item():.4f}")

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
