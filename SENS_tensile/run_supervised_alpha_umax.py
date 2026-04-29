#!/usr/bin/env python3
"""
run_supervised_alpha_umax.py — Path C / A FEM-α-supervised PIDL runner.

Per `design_supervised_alpha_apr29.md`. Adds zone-restricted MSE between
PIDL α field and FEM α field as supervision term. Standard 8×400 NN
unchanged; only loss gets +λ_α·MSE(α_PIDL, α_FEM_interpolated, zone).

Supports three modes via flags:
  --mode pathC        Always-on supervision (Path C, default), constant λ_α
  --mode pathA        Warm-start: λ_α only for cycles 1..K_warm, then 0
  --mode anchor       λ_α only at supplied --train-anchors cycle list

Test cycles can be HELD OUT via --test-anchor (training never sees that
cycle's FEM α; afterwards Mac post-process compares prediction at test
anchor vs FEM truth).

All other interventions disabled (williams, ansatz, spAlphaT, psiHack,
fem_oracle, multihead).

Usage examples:
    # Path C smoke (always-on, λ=1.0, zone radius 0.02, 5 cycles)
    python run_supervised_alpha_umax.py 0.12 --n-cycles 5 \
        --mode pathC --lambda-alpha 1.0 --zone-radius 0.02

    # Path A (warm-start K=5 with λ=10, then free-evolve 5 more cycles)
    python run_supervised_alpha_umax.py 0.12 --n-cycles 10 \
        --mode pathA --lambda-alpha 10.0 --K-warm 5 --zone-radius 0.02

    # Anchor-only (supervise at FEM v2 anchors c1, c40, c82; HOLD OUT c70 for test)
    python run_supervised_alpha_umax.py 0.12 --n-cycles 100 \
        --mode anchor --lambda-alpha 1.0 --train-anchors 1,40,82 --test-anchor 70

Archive auto-named:
    hl_8_..._N{N}_R0.0_Umax{U}_supα_{mode}_lam{λ}_rg{r}_K{K}/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Path C/A FEM-α-supervised PIDL runner.")
parser.add_argument("umax", type=float,
                    help="Loading amplitude. Any positive U_max.")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300).")
parser.add_argument("--mode", choices=["pathC", "pathA", "anchor"], default="pathC",
                    help="Supervision schedule: pathC=always-on, pathA=warm-start K cycles, "
                         "anchor=only at --train-anchors cycles.")
parser.add_argument("--lambda-alpha", type=float, default=1.0,
                    help="Supervision weight λ_α. Scan 0/0.01/0.1/1/10/100.")
parser.add_argument("--zone-radius", type=float, default=0.02,
                    help="Override zone radius B_r around (0,0). 0 = whole domain (no zone restriction). "
                         "Default 0.02 matches oracle zone.")
parser.add_argument("--K-warm", type=int, default=5,
                    help="Path A only: number of warm-up cycles (1..K) with λ_α; cycles >K free-evolve.")
parser.add_argument("--train-anchors", type=str, default="1,40,82",
                    help="Anchor mode only: comma-separated cycle list to supervise at.")
parser.add_argument("--test-anchor", type=int, default=None,
                    help="Optional: cycle to HOLD OUT for test (logged for post-process MSE).")
parser.add_argument("--every-n-epochs", type=int, default=1,
                    help="Amortize supervised loss to every N epochs to save wall (default 1).")
parser.add_argument("--loss-kind", choices=["mse_lin", "mse_log", "mse_rel"], default="mse_lin",
                    help="α-MSE loss form. mse_lin recommended (α∈[0,1] well-behaved).")
parser.add_argument("--fem-data-dir", type=str, default=None,
                    help="Override FEM data dir (default uses fem_supervision auto-discover).")
args = parser.parse_args()

if not (1 <= args.n_cycles <= 5000):
    raise SystemExit(f"n_cycles={args.n_cycles} out of [1, 5000]")
if not (0.01 <= args.umax <= 1.0):
    raise SystemExit(f"umax={args.umax} out of sensible range [0.01, 1.0]")
if args.zone_radius < 0:
    raise SystemExit(f"zone_radius must be >=0 (got {args.zone_radius})")
if args.mode == "anchor" and args.test_anchor is not None:
    train_anchors_set = set(int(x) for x in args.train_anchors.split(","))
    if args.test_anchor in train_anchors_set:
        raise SystemExit(f"--test-anchor {args.test_anchor} cannot be in --train-anchors")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_supervised_alpha_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import config           # noqa: E402
import torch            # noqa: E402
import numpy as np      # noqa: E402

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
if "fem_oracle" in config.fatigue_dict:
    config.fatigue_dict["fem_oracle"] = {"enable": False}
config.rebuild_disp_cyclic()

# Override mesh paths to absolute
config.fine_mesh_file   = str(HERE / config.fine_mesh_file)
config.coarse_mesh_file = str(HERE / config.coarse_mesh_file)

# --- Build archive path -----------------------------------------------------
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_lam_tag = f"lam{str(args.lambda_alpha).replace('.', 'p')}"
_rg_tag = f"rg{str(args.zone_radius).replace('.', 'p')}"
_mode_tag = args.mode
if args.mode == "pathA":
    _mode_tag += f"_K{args.K_warm}"
elif args.mode == "anchor":
    _mode_tag += f"_anchors{args.train_anchors.replace(',','-')}"
    if args.test_anchor is not None:
        _mode_tag += f"_holdc{args.test_anchor}"
_supα_tag = f"_supα_{_mode_tag}_{_lam_tag}_{_rg_tag}"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag + _supα_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# --- Build pipeline ----------------------------------------------------------
print("=" * 72)
print(f"Path C/A supervised α PIDL runner ({args.mode})")
print(f"  U_max         = {args.umax}")
print(f"  n_cycles      = {args.n_cycles}")
print(f"  λ_α           = {args.lambda_alpha}")
print(f"  zone_radius   = {args.zone_radius}  ({'all elements' if args.zone_radius == 0 else f'B_r={args.zone_radius} around (0,0)'})")
print(f"  loss_kind     = {args.loss_kind}")
if args.mode == "pathA":
    print(f"  K_warm        = {args.K_warm}  (cycles 1..{args.K_warm} supervised, >K free-evolve)")
elif args.mode == "anchor":
    print(f"  train anchors = {args.train_anchors}")
    if args.test_anchor is not None:
        print(f"  TEST anchor   = {args.test_anchor}  (HELD OUT, post-process MSE will be computed)")
print(f"  archive       = {_dir_name}")
print(f"  device        = {config.device}")
print("=" * 72)

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from model_train import train
from fem_supervision import FEMSupervision

pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict,
)
print(f"Building input data from {config.fine_mesh_file}…")
inp, T_conn, area_T, _ = prep_input_data(
    matprop, pffmodel, config.crack_dict, config.numr_dict,
    mesh_file=config.fine_mesh_file, device=config.device,
)
print(f"  N collocation points: {len(inp)}")
print(f"  N triangles: {len(T_conn) if T_conn is not None else 'N/A (autodiff)'}")

# Build PIDL element centroids for FEM nearest-neighbor mapping
pidl_centroids_t = (inp[T_conn[:, 0]] + inp[T_conn[:, 1]] + inp[T_conn[:, 2]]) / 3.0
pidl_centroids = pidl_centroids_t.detach().cpu().numpy()
print(f"  PIDL element centroids: {pidl_centroids.shape}")

# Build override zone mask (if zone_radius > 0)
zone_mask = None
if args.zone_radius > 0:
    r_pidl = np.sqrt(pidl_centroids[:, 0] ** 2 + pidl_centroids[:, 1] ** 2)
    zone_np = r_pidl <= args.zone_radius
    zone_mask = torch.from_numpy(zone_np).to(config.device)
    print(f"  Zone mask: {zone_np.sum()} elements in B_r={args.zone_radius}")

# Build FEMSupervision (loads FEM v2 snapshots for this Umax)
print(f"Loading FEM α snapshots for Umax={args.umax}…")
fem_sup = FEMSupervision(umax=args.umax, fem_dir=args.fem_data_dir)
print(f"  FEM cycles available: {fem_sup.cycles}")
if not fem_sup.d_field:
    raise SystemExit("FEM α (alpha_elem/d_elem) not present in snapshots; cannot supervise α.")

# Build cycle-conditional λ schedule
def make_schedule():
    if args.mode == "pathC":
        return lambda j: args.lambda_alpha   # constant
    elif args.mode == "pathA":
        K = args.K_warm
        return lambda j: args.lambda_alpha if 1 <= j <= K else 0.0
    elif args.mode == "anchor":
        anchors = set(int(x) for x in args.train_anchors.split(","))
        return lambda j: args.lambda_alpha if j in anchors else 0.0
    raise ValueError(args.mode)

supervised_alpha_dict = {
    "enable": True,
    "fem_sup": fem_sup,
    "lambda": args.lambda_alpha,                    # base value (overridden by schedule)
    "lambda_schedule": make_schedule(),
    "pidl_centroids": pidl_centroids,
    "zone_mask": zone_mask,
    "loss_kind": args.loss_kind,
    "every_n_epochs": args.every_n_epochs,
    # bookkeeping
    "_mode": args.mode,
    "_test_anchor": args.test_anchor,
}

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
    supervised_alpha_dict=supervised_alpha_dict,
)
