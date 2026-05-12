#!/usr/bin/env python3
"""
run_e2_reverse_umax.py — Task 1 oracle-driver MIT-8b (Apr 27)

Replaces PIDL's NN-computed ψ⁺ with FEM-projected ψ⁺ AT THE FATIGUE
ACCUMULATOR INPUT, while leaving PIDL's u/α NN training untouched. Tests
whether single-element peak ψ⁺ amplitude is *sufficient* to close the
ᾱ_max gap (α-0 already showed total tip energy is comparable; question is
whether the spatial sharpness of FEM peak drives ᾱ_max).

Implementation (per `handoff_executor_apr26_addendum.md` Task 1):
- PIDL u/α training proceeds normally (Deep Ritz physics loss).
- After each cycle's training, before fatigue_history.update_fatigue_history
  is called, override psi_plus_elem with FEM-projected ψ⁺ in process zone
  B_2ℓ₀(tip). FEM ψ⁺ is loaded from `_pidl_handoff_v2/psi_snapshots_for_agent/`
  and time-interpolated linearly between FEM snapshot cycles (1/40/70/82
  for Umax=0.12; 1/150/350/396 for Umax=0.08).
- Outside the process zone, psi_plus_elem stays as PIDL's native value
  (so far-field PDE consistency is not perturbed).

Cost reality (per addendum):
- FEM data only at 4 snapshot cycles per Umax. Linear-interp between
  snapshots is the cheap-but-imperfect approximation. Document as such.
- Linear interp may be poor if FEM ψ⁺ grows nonlinearly (it does, fast at
  end). Acceptable as first-pass diagnostic.

Usage:
    python run_e2_reverse_umax.py <U_max> [--n-cycles 300] [--zone-radius 0.02]
                                  [--no-apply-g]

Archive dir auto-named:
    hl_8_..._Umax<UMAX>_oracle_zone<R>/
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- CLI ---------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Task 1 oracle-driver MIT-8b runner.")
parser.add_argument("umax", type=float,
                    help="Loading amplitude. Any U_max for which FEM data is "
                         "discoverable in FEM_DATA_DIR (env) or DEFAULT_FEM_DIR.")
parser.add_argument("--n-cycles", type=int, default=300,
                    help="Total fatigue cycles (default 300).")
parser.add_argument("--zone-radius", type=float, default=0.02,
                    help="Process-zone radius for ψ⁺ override (default 0.02 = 2·ℓ₀).")
parser.add_argument("--no-apply-g", action="store_true",
                    help="Skip g(α) multiplication on FEM ψ⁺_raw before substitution. "
                         "Default applies g(α) to match degraded ψ⁺ that fatigue accumulator expects.")
parser.add_argument("--moving-zone", action="store_true",
                    help="Variant A (Apr 28): override mask follows the current crack "
                         "tip x_tip (L∞ definition: max x where α_elem > 0.5) each cycle. "
                         "Fixes the saturation-cliff plateau of static-zone oracle. "
                         "Archive tag: _movingzone (vs default _zone fixed-origin).")
parser.add_argument("--moving-zone-alpha-thr", type=float, default=0.5,
                    help="Alpha threshold for L∞ tip definition under --moving-zone (default 0.5).")
args = parser.parse_args()

# Note: U_max validity is delegated to FEMSupervision auto-discovery — it will
# raise a descriptive ValueError if no FEM cycle dumps are found for this U_max.
# (Apr 27: dropped the (0.08, 0.12) whitelist after Windows confirmed full
# per-cycle dump exists for all 5 Umax in SENT_PIDL_<NN>_export/psi_fields/.)
if not (10 <= args.n_cycles <= 5000):
    raise SystemExit(f"n_cycles={args.n_cycles} out of [10, 5000]")

# --- Inject CLI args for config.py argv parsing ------------------------------
sys.argv = [
    "run_e2_reverse_umax.py",
    "8", "400", "1", "TrainableReLU", "1.0",
]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import config   # noqa: E402
import torch    # noqa: E402
import numpy as np  # noqa: E402

# Disable other interventions
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
config.rebuild_disp_cyclic()

# --- Build FEM oracle + PIDL element centroids -------------------------------
from fem_supervision import FEMSupervision    # noqa: E402
from input_data_from_mesh import prep_input_data    # noqa: E402
from construct_model import construct_model    # noqa: E402

fem_sup = FEMSupervision(umax=float(args.umax))
print(f"  FEM cycles available: {fem_sup.cycles}")

# Build mesh once to compute PIDL element centroids + override mask
pffmodel, matprop, network = construct_model(
    config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
    config.domain_extrema, config.device, williams_dict=config.williams_dict,
    fourier_dict=config.fourier_dict  # ★ 2026-05-14: pass through (disabled by default)
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
r_to_tip = np.sqrt(cx ** 2 + cy ** 2)
override_mask_np = r_to_tip <= float(args.zone_radius)
override_mask = torch.from_numpy(override_mask_np).to(config.device)
n_override = int(override_mask_np.sum())

# --- Build archive path -----------------------------------------------------
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_oracle_tag = f"_oracle_zone{args.zone_radius}"
if args.no_apply_g:
    _oracle_tag += "_noG"
if args.moving_zone:
    _oracle_tag += "_movingzone"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag + _oracle_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# Sanity: print FEM ψ⁺ at fatigue-relevant cycles
psi_target_c1 = fem_sup.psi_target_at_cycle(1, pidl_centroids)
print("=" * 72)
print("Task 1 oracle-driver MIT-8b")
print(f"  U_max         = {args.umax}")
print(f"  n_cycles      = {args.n_cycles}")
if args.moving_zone:
    print(f"  zone_radius   = {args.zone_radius}  (B_r(x_tip, 0) MOVING override zone, "
          f"x_tip from L∞ alpha>{args.moving_zone_alpha_thr})")
else:
    print(f"  zone_radius   = {args.zone_radius}  (B_r(0,0) STATIC override zone)")
print(f"  apply_g(α)    = {not args.no_apply_g}")
print(f"  PIDL elements in zone: {n_override} / {len(pidl_centroids)}")
print(f"  archive       = {_dir_name}")
print(f"  device        = {config.device}")
print(f"  FEM ψ⁺ @ c1   max={psi_target_c1.max().item():.3e}  "
      f"in-zone-max={psi_target_c1[override_mask.cpu()].max().item():.3e}")
mid_cycle = sorted(fem_sup.cycles)[len(fem_sup.cycles) // 2]
psi_target_mid = fem_sup.psi_target_at_cycle(mid_cycle, pidl_centroids)
print(f"  FEM ψ⁺ @ c{mid_cycle:>3} max={psi_target_mid.max().item():.3e}  "
      f"in-zone-max={psi_target_mid[override_mask.cpu()].max().item():.3e}")
print("=" * 72)

# --- Inject oracle config into fatigue_dict (model_train reads from here) ---
config.fatigue_dict["fem_oracle"] = {
    "enable": True,
    "fem_sup": fem_sup,
    "pidl_centroids": pidl_centroids,
    "override_mask": override_mask,                  # static fallback (used if moving_zone=False)
    "apply_g": not args.no_apply_g,
    "moving_zone": bool(args.moving_zone),
    "moving_zone_alpha_thr": float(args.moving_zone_alpha_thr),
    "zone_radius": float(args.zone_radius),
}

# --- Build field_comp + train ------------------------------------------------
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
)
