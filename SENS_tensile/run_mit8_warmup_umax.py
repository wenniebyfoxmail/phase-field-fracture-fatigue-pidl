#!/usr/bin/env python3
"""
run_mit8_warmup_umax.py — MIT-8 (Apr 25 2026)

Half-data-driven FEM-supervised warm-up. Joint loss = physics + λ·MSE(log10
ψ⁺_PIDL_raw, log10 ψ⁺_FEM_raw_interp) for cycles 1..K, then release (λ=0)
for cycles K+1..N_f.

Tests Auditor Hit 3: does the NN's u-field have the REPRESENTATIONAL
capacity to hold FEM-like ψ⁺ trajectory after release?
  - If PIDL ψ⁺ tracks FEM through K and DECAYS rapidly post-K: NN can
    represent FEM-like state but physics-only loss can't find it
    (optimization landscape problem, not representation).
  - If PIDL ψ⁺ collapses to baseline ~5 even DURING supervision: NN
    fundamentally can't represent FEM-like ψ⁺ (representation problem).
  - If PIDL ψ⁺ holds FEM-like POST-K: optimization landscape would have
    benefited from a hand-supervised initialization.

Implementation: Option B (per Auditor Hit 8) — supervise ψ⁺ via autograd
through u-field. PIDL ψ⁺_raw is computed as E_el_p (undegraded) and
matched against FEM psi_elem (raw, from `_pidl_handoff_v2/
psi_snapshots_for_agent/u<umax>_cycle_<NNNN>.mat`).

Usage:
    python run_mit8_warmup_umax.py <U_max> --K <int> [--lambda 1.0]

Archive dir auto-named:
    hl_8_..._Umax<UMAX>_mit8_K<K>_lam<LAM>/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="MIT-8 FEM-supervised warm-up runner.")
parser.add_argument("umax", type=float,
                    help="Loading amplitude (must match available FEM snapshots: 0.08 or 0.12).")
parser.add_argument("--K", type=int, required=True,
                    help="Last cycle with supervision (release at K+1). E.g. 40 or 70.")
parser.add_argument("--lambda", dest="lam", type=float, default=1.0,
                    help="Supervised loss weight λ (default 1.0).")
parser.add_argument("--loss-kind", default="mse_log",
                    choices=["mse_log", "mse_lin", "mse_rel"],
                    help="Supervised loss type. mse_log handles ψ⁺ orders-of-magnitude variation.")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300; smoke test: e.g. 10).")
parser.add_argument("--supervised-every", type=int, default=1,
                    help="Compute supervised loss every N epochs (default 1 = "
                         "every epoch; use 10 for 10x speedup with amortization).")
# ★ 2026-05-14: sparse boundary anchor mask
parser.add_argument("--mask-kind", default="full",
                    choices=["full", "boundary", "crack_path", "boundary_or_crack"],
                    help="Element subset for supervised loss. full = all PIDL elems "
                         "(historical MIT-8). boundary = elements within x_centroid > "
                         "mask-x-min. crack_path = along |y_centroid| < mask-y-abs-max "
                         "AND x_centroid > mask-x-min. boundary_or_crack = union.")
parser.add_argument("--mask-x-min", type=float, default=0.45,
                    help="x_centroid lower bound for 'boundary' mask (default 0.45 = right edge zone).")
parser.add_argument("--mask-y-abs-max", type=float, default=0.05,
                    help="|y_centroid| upper bound for 'crack_path' mask (default 0.05 = crack propagation strip).")
# ★ 2026-05-14: supervision target — ψ⁺ (historical) or α direct
parser.add_argument("--target", default="psi",
                    choices=["psi", "alpha"],
                    help="Supervision target: 'psi' = ψ⁺ MSE (historical MIT-8); "
                         "'alpha' = direct phase-field α MSE against FEM d_elem "
                         "(per-element via NN T_conn averaging).")
args = parser.parse_args()

if args.umax not in (0.08, 0.12):
    raise SystemExit(f"umax={args.umax} has no FEM snapshots. Use 0.08 or 0.12.")
if not (1 <= args.K <= args.n_cycles):
    raise SystemExit(f"K={args.K} must be in [1, n_cycles={args.n_cycles}]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_mit8_warmup_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# --- Override config dicts ---------------------------------------------------
import config  # noqa: E402
import torch   # noqa: E402

# Disable everything else
config.ansatz_dict["enable"]   = False
config.williams_dict["enable"] = False

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

# --- Build archive path with mit8 tag ----------------------------------------
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
_mit8_tag = f"_mit8_K{args.K}_lam{args.lam}"
# ★ 2026-05-14: append target tag when 'alpha' (default psi keeps historical naming)
if args.target == "alpha":
    _mit8_tag = _mit8_tag + "_targetalpha"
# ★ 2026-05-14: append mask tag when not 'full' (default), keep backward-compat naming
if args.mask_kind != "full":
    _mit8_tag = _mit8_tag + f"_mask{args.mask_kind}_xmin{args.mask_x_min}"
    if args.mask_kind in ("crack_path", "boundary_or_crack"):
        _mit8_tag = _mit8_tag + f"_yabsmax{args.mask_y_abs_max}"

_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _mit8_tag
)

config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# --- Build FEM supervision + PIDL element centroids -------------------------
from fem_supervision import FEMSupervision
from input_data_from_mesh import prep_input_data
from construct_model import construct_model
import numpy as np

print("=" * 72)
print("MIT-8 FEM-supervised warm-up")
print(f"  U_max     = {args.umax}")
print(f"  K (release after this cycle) = {args.K}")
print(f"  lambda    = {args.lam}")
print(f"  loss_kind = {args.loss_kind}")
print(f"  supervised_every = {args.supervised_every} epochs")
print(f"  n_cycles  = {args.n_cycles}")
print(f"  archive   = {_dir_name}")
print(f"  device    = {config.device}")
print("=" * 72)

# Load FEM snapshots
fem_sup = FEMSupervision(umax=float(args.umax))
print(f"  FEM cycles available: {fem_sup.cycles}")

# Build model + mesh once to compute PIDL element centroids
pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device,
    williams_dict=config.williams_dict,
    fourier_dict=config.fourier_dict       # ★ 2026-05-14: pass through (disabled by default)
)
inp_for_centroids, T_conn_for_centroids, _, _ = prep_input_data(
    matprop, pffmodel, config.crack_dict, config.numr_dict,
    mesh_file=config.fine_mesh_file, device=config.device
)
inp_np = inp_for_centroids.detach().cpu().numpy()
T_np = (T_conn_for_centroids.cpu().numpy()
        if isinstance(T_conn_for_centroids, torch.Tensor)
        else T_conn_for_centroids)
cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
pidl_centroids = np.stack([cx, cy], axis=1)
print(f"  PIDL elements: {pidl_centroids.shape[0]}  "
      f"(FEM elements: {fem_sup.fem_centroids.shape[0]})")

# --- Build sparse boundary anchor mask (★ 2026-05-14) ----------------------
mit8_mask = None
if args.mask_kind != "full":
    cx_t = torch.from_numpy(pidl_centroids[:, 0])
    cy_t = torch.from_numpy(pidl_centroids[:, 1])
    if args.mask_kind == "boundary":
        mit8_mask = (cx_t.abs() >= args.mask_x_min)
    elif args.mask_kind == "crack_path":
        mit8_mask = (cy_t.abs() <= args.mask_y_abs_max) & (cx_t >= args.mask_x_min)
    elif args.mask_kind == "boundary_or_crack":
        boundary = (cx_t.abs() >= args.mask_x_min)
        crack = (cy_t.abs() <= args.mask_y_abs_max) & (cx_t >= 0.0)
        mit8_mask = boundary | crack
    n_active = int(mit8_mask.sum().item())
    print(f"  [mask] kind={args.mask_kind}  active_elems={n_active} / {len(cx_t)} "
          f"({100*n_active/len(cx_t):.2f}%)")

# --- Build mit8_dict --------------------------------------------------------
mit8_dict = {
    "enable": True,
    "K": int(args.K),
    "lambda": float(args.lam),
    "fem_sup": fem_sup,
    "pidl_centroids": pidl_centroids,
    "loss_kind": args.loss_kind if args.target == "psi" else "mse_lin",
    "every_n_epochs": int(args.supervised_every),
    "mask": mit8_mask,    # ★ 2026-05-14: None for full domain, tensor for sparse
    "target_kind": args.target,    # ★ 2026-05-14: 'psi' (default) or 'alpha'
}

# Sanity: print FEM ψ⁺ stats interpolated to PIDL at first FEM cycle
psi_target_c1 = fem_sup.psi_target_at_cycle(1, pidl_centroids)
print(f"  FEM ψ⁺ at PIDL elems @ cycle 1: "
      f"max={psi_target_c1.max().item():.3e}  "
      f"top10-mean={torch.topk(psi_target_c1, 10).values.mean().item():.3e}  "
      f"mean={psi_target_c1.mean().item():.3e}")
if max(fem_sup.cycles) >= 40:
    psi_target_cK = fem_sup.psi_target_at_cycle(min(40, args.K), pidl_centroids)
    print(f"  FEM ψ⁺ at PIDL elems @ cycle 40: "
          f"max={psi_target_cK.max().item():.3e}  "
          f"top10-mean={torch.topk(psi_target_cK, 10).values.mean().item():.3e}  "
          f"mean={psi_target_cK.mean().item():.3e}")

# --- Build field_comp (re-using the network already constructed) ------------
from field_computation import FieldComputation
from model_train import train

field_comp = FieldComputation(
    net=network, domain_extrema=config.domain_extrema,
    lmbda=torch.tensor([0.0], device=config.device),
    theta=config.loading_angle,
    alpha_constraint=config.numr_dict["alpha_constraint"],
    williams_dict=config.williams_dict,
    l0=config.mat_prop_dict["l0"],
    exact_bc_dict=config.exact_bc_dict,        # ★ 2026-05-14: C4 (disabled by default)
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
    mit8_dict=mit8_dict,                              # ★ MIT-8
)
