#!/usr/bin/env python3
"""
run_g4_sensitivity.py — Parameterized runner for expert-review G4 sensitivity sweeps.

Covers three sweeps via a single runner:
  (A) Seed std sweep   : vary --seed at multiple Umax (baseline coeff=1)
  (B) ℓ₀ sensitivity   : vary --l0 at fixed Umax=0.10
  (C) α_T sensitivity  : vary --alpha_T at fixed Umax=0.10

Architecture is plain baseline (no Williams, no Enriched, no spAlphaT, no
psi_hack, Carrara accumulator). Only the swept parameter changes between
runs in each sub-sweep.

Usage:
    # (A) Seed sweep at Umax=0.08, seed=2:
    python run_g4_sensitivity.py 0.08 --seed 2

    # (B) ℓ₀ sensitivity at Umax=0.10, ℓ₀=0.005:
    python run_g4_sensitivity.py 0.10 --l0 0.005

    # (C) α_T sensitivity at Umax=0.10, α_T=0.3:
    python run_g4_sensitivity.py 0.10 --alpha_T 0.3

Defaults match baseline: seed=1, l0=0.01, alpha_T=0.5.
Archive name auto-tagged with the swept parameter so 25 sweep jobs do
NOT collide on disk.

Purpose (paper):
- (A) gives ±std error bars on N_f / ᾱ_max for the existing 5-Umax baseline
  S-N curve. Reviewer-level requirement (G4).
- (B) gives ℓ₀ sensitivity at a representative mid-Umax — answers
  "is your reported gap robust to phase-field regularization length?"
- (C) gives α_T sensitivity at the same Umax — answers
  "is your fatigue threshold choice α_T=0.5 driving the conclusion?"
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="G4 baseline sensitivity sweeps (seed / l0 / alpha_T).")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (e.g., 0.08, 0.10, 0.12).")
parser.add_argument("--seed", type=int, default=1,
                    help="Network init seed (default 1, baseline).")
parser.add_argument("--l0", type=float, default=0.01,
                    help="Phase-field regularization length (default 0.01, baseline).")
parser.add_argument("--alpha_T", type=float, default=0.5,
                    help="Fatigue threshold (default 0.5, baseline).")
parser.add_argument("--n_cycles", type=int, default=700,
                    help="Cyclic load cycles (default 700, ample for low Umax).")
args = parser.parse_args()

if not (0.05 <= args.umax <= 0.20):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")
if not (0.001 <= args.l0 <= 0.5):
    raise SystemExit(f"l0={args.l0} out of sensible range [0.001, 0.5]")
if not (0.05 <= args.alpha_T <= 5.0):
    raise SystemExit(f"alpha_T={args.alpha_T} out of sensible range [0.05, 5.0]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_g4_sensitivity.py",
    "8", "400", str(args.seed), "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# --- Override config dicts ---------------------------------------------------
import config  # noqa: E402
import torch   # noqa: E402

# Architectural toggles: all OFF (plain baseline)
config.ansatz_dict["enable"]   = False
config.williams_dict["enable"] = False

# Material: l0 swept (rest baseline)
config.mat_prop_dict["l0"] = float(args.l0)

# Fatigue: clean Carrara baseline; alpha_T + Umax swept
config.fatigue_dict["accum_type"]                = "carrara"
config.fatigue_dict["degrad_type"]               = "asymptotic"
config.fatigue_dict["alpha_T"]                   = float(args.alpha_T)
config.fatigue_dict["disp_max"]                  = float(args.umax)
config.fatigue_dict["n_cycles"]                  = int(args.n_cycles)
config.rebuild_disp_cyclic()  # rebuild loading vector after disp_max change
config.fatigue_dict["R_ratio"]                   = 0.0
config.fatigue_dict["enable_E_fallback"]         = False
config.fatigue_dict["spatial_alpha_T"]["enable"] = False
config.fatigue_dict["psi_hack"]["enable"]        = False

# --- Rebuild archive path with G4 sensitivity tags --------------------------
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

# G4 sensitivity tag — only appended if non-default to keep clean baseline naming
_g4_parts = []
if abs(args.l0 - 0.01) > 1e-6:
    _g4_parts.append(f"l0{args.l0:g}")
if abs(args.alpha_T - 0.5) > 1e-6:
    _g4_parts.append(f"aT{args.alpha_T:g}")
_g4_tag = ("_g4_" + "_".join(_g4_parts)) if _g4_parts else ""

_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _g4_tag
)

_PATH_ROOT = HERE
config.model_path             = _PATH_ROOT / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("G4 sensitivity sweep (baseline + single-parameter variation)")
print(f"  U_max        = {args.umax}")
print(f"  seed         = {args.seed}        (baseline=1)")
print(f"  l0           = {args.l0}      (baseline=0.01)")
print(f"  alpha_T      = {args.alpha_T}     (baseline=0.5)")
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
