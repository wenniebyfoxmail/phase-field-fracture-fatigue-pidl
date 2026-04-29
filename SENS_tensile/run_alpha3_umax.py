#!/usr/bin/env python3
"""
run_alpha3_umax.py — α-3 XFEM-jump enrichment runner.

Per `design_alpha3_xfem_jump_apr29.md`. Math-rigid version of α-2 (multi-head):
replaces smooth Gaussian gate with Heaviside discontinuity in x-direction at
moving x_tip.

Architecture:
    u(x) = u_continuous(x) + H(x - x_tip) · u_jump(x)
where H is differentiable Heaviside (sigmoid surrogate by default).

Targets BOTH (a) per-element ψ⁺ amplitude (singular ε at jump) AND
(b) ψ⁺ peak stationarity (modal → 1.0 by construction since the
discontinuity location IS x_tip, naturally pinning argmax).

All other interventions disabled (williams, ansatz, spAlphaT, psiHack,
fem_oracle, multihead).

Usage:
    python run_alpha3_umax.py <U_max> [--n-cycles 300]
        [--n-hidden-j 4] [--neurons-j 100]
        [--heaviside-kind soft] [--heaviside-eps 0.0005]
        [--no-fatigue] [--smoke-t2]

Archive auto-named:
    hl_8_..._N{N}_R0.0_Umax{U}_alpha3_xfem_{kind}_eps{e}/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="α-3 XFEM-jump runner.")
parser.add_argument("umax", type=float,
                    help="Loading amplitude. Any positive U_max.")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300, range [1, 5000]).")
parser.add_argument("--n-hidden-j", type=int, default=4,
                    help="Jump head hidden layers (default 4).")
parser.add_argument("--neurons-j", type=int, default=100,
                    help="Jump head neurons per layer (default 100).")
parser.add_argument("--heaviside-kind", choices=["soft", "hard"], default="soft",
                    help="Heaviside form: 'soft' = sigmoid(d/eps); 'hard' = step + STE backward.")
parser.add_argument("--heaviside-eps", type=float, default=0.0005,
                    help="Smooth-Heaviside eps. Default 0.0005 = h_mesh/4 for legacy 67k mesh.")
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
if args.heaviside_eps <= 0:
    raise SystemExit(f"heaviside_eps must be > 0 (got {args.heaviside_eps})")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_alpha3_umax.py",
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

# --- Enable α-3 XFEM-jump --------------------------------------------------
config.xfem_dict = {
    'enable': True,
    'n_hidden_c': config.network_dict["hidden_layers"],
    'neurons_c': config.network_dict["neurons"],
    'n_hidden_j': args.n_hidden_j,
    'neurons_j': args.neurons_j,
    'heaviside_kind': args.heaviside_kind,
    'heaviside_eps': args.heaviside_eps,
    'jump_relative_input': True,
    'activation_j': 'ReLU',
}

# --- Build archive path ----------------------------------------------------
_fat = config.fatigue_dict
if _fat.get('fatigue_on', True):
    _fatigue_tag = (
        f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
        f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
        f"_Umax{_fat['disp_max']}"
    )
else:
    _fatigue_tag = f"_fatigue_off_Umax{_fat['disp_max']}"
_eps_tag = str(args.heaviside_eps).replace('.', 'p').replace('-', 'm')
_alpha3_tag = (f"_alpha3_xfem_{args.heaviside_kind}"
               f"_jump{args.n_hidden_j}x{args.neurons_j}_eps{_eps_tag}")
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag + _alpha3_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# --- Banner ---------------------------------------------------------------
print("=" * 72)
print("α-3 XFEM-jump enrichment runner")
print(f"  U_max         = {args.umax}")
print(f"  n_cycles      = {args.n_cycles}")
print(f"  jump head     = {args.n_hidden_j}×{args.neurons_j}")
print(f"  Heaviside     = {args.heaviside_kind}, eps = {args.heaviside_eps}")
print(f"  archive       = {_dir_name}")
print(f"  device        = {config.device}")
print("=" * 72)

# --- Override mesh paths to absolute (config.py uses relative) -------------
config.fine_mesh_file   = str(HERE / config.fine_mesh_file)
config.coarse_mesh_file = str(HERE / config.coarse_mesh_file)

# --- Build pipeline + train -------------------------------------------------
from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from model_train import train

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict,
    xfem_dict=config.xfem_dict,
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
