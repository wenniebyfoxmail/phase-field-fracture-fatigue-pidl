#!/usr/bin/env python3
"""
run_alpha1_umax.py — α-1 mesh-adaptive Variant A
                     (per design_alpha1_mesh_adaptive_apr27.md, Apr 27)

Replaces the legacy `meshed_geom2.msh` with a pre-refined corridor mesh
(`meshed_geom_corridor_v1.msh`) that has:
  - h_c = 0.001 (= FEM tip refinement) inside corridor x∈[0,0.5], |y|<0.04
  - h_f = 0.020 in the far field
  - Total ~153k triangles (vs 67k legacy)

Targets the "amplitude" half (a) of the two-part ᾱ_max gap framing per
`finding_oracle_driver_apr27.md`. Closes the ~1.8× mesh contribution to
the 5.8× single-element ψ⁺ peak gap (per α-0 finding).

NO source/ change: uses the same Deep Ritz functional as baseline. Mesh
refinement only — variational consistency preserved (Dir 3 lesson:
energy WEIGHTING distorts the functional; mesh refinement does NOT).

All other interventions disabled (williams, ansatz, spAlphaT, psiHack,
fem_oracle).

Usage:
    python run_alpha1_umax.py <U_max> [--n-cycles 300] [--mesh-variant corridor_v1]

Archive auto-named:
    hl_8_..._N{N}_R0.0_Umax{U}_alpha1_{mesh_variant}/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="α-1 mesh-adaptive runner.")
parser.add_argument("umax", type=float,
                    help="Loading amplitude. Any positive U_max.")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300, range [10, 5000]).")
parser.add_argument("--mesh-variant", default="corridor_v1",
                    help="Mesh variant tag — looks for meshed_geom_<tag>.msh "
                         "in SENS_tensile/. Default 'corridor_v1' "
                         "(h_c=0.001 corridor along propagation path).")
args = parser.parse_args()

if not (10 <= args.n_cycles <= 5000):
    raise SystemExit(f"n_cycles={args.n_cycles} out of [10, 5000]")
if not (0.01 <= args.umax <= 1.0):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.01, 1.0]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_alpha1_umax.py",
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
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False
# Critical for α-1: NO oracle override either
if "fem_oracle" in config.fatigue_dict:
    config.fatigue_dict["fem_oracle"] = {"enable": False}
config.rebuild_disp_cyclic()

# --- Override mesh path to the refined corridor mesh ------------------------
mesh_path = HERE / f"meshed_geom_{args.mesh_variant}.msh"
if not mesh_path.is_file():
    raise SystemExit(f"Mesh file not found: {mesh_path}\n"
                     f"Generate it via:  python make_alpha1_mesh.py "
                     f"--variant {args.mesh_variant}")
config.fine_mesh_file = str(mesh_path)

# --- Build archive path -----------------------------------------------------
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_alpha1_tag = f"_alpha1_{args.mesh_variant}"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag + _alpha1_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# --- Banner -----------------------------------------------------------------
print("=" * 72)
print("α-1 mesh-adaptive runner (Variant A)")
print(f"  U_max         = {args.umax}")
print(f"  n_cycles      = {args.n_cycles}")
print(f"  mesh variant  = {args.mesh_variant}")
print(f"  mesh file     = {mesh_path.name}")
print(f"  archive       = {_dir_name}")
print(f"  device        = {config.device}")
print("=" * 72)

# --- Build pipeline + train --------------------------------------------------
from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from model_train import train

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device, williams_dict=config.williams_dict,
)
print(f"Building input data from {mesh_path.name}…")
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
