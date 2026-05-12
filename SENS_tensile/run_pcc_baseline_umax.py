#!/usr/bin/env python3
"""run_pcc_baseline_umax.py — Phase 2A units-transition smoke runner.

PCC concrete physical parameters (Baktheer 2024) translated to PIDL-normalized
units via `source.scaling.PCCScaling`. Same AT1+Carrara kernel as Phase 1 toy,
swapped material constants only.

## Scope: this is a units-transition prototype, NOT a Baktheer anchor

Three confounds make this smoke NOT a clean discriminator between Phase 2A
(AT-Carrara) and Phase 2B (Wu PF-CZM) framework adequacy:

1. **Loading is an intact-bar displacement label, not a calibrated nominal
   stress** (expert review P1, 2026-05-14): `disp_ratio_intact=0.75` maps to
   the prescribed displacement that WOULD give 0.75·f_t in an uncracked bar.
   In the cracked SENT (a₀/W=0.5), realized nominal stress is LESS — actual
   ratio not calibrated. Don't quote against Baktheer's S^max=0.75·f_t.

2. **Geometry differs from FEM PCC line** (expert review P2): this runner
   reuses the Phase 1 toy mesh (`meshed_geom1.msh`, a₀/W=0.5 half-width
   notch) because it matches the normalized domain [-0.5, 0.5]² out of the
   box. Earlier FEM PCC line used a₀=5 mm (a₀/W=0.05). The geometries are
   NOT equivalent — geometry effects and units-transition effects are
   confounded in this runner.

3. **Phase 2A null result cannot be uniquely attributed** (expert review P4):
   if this smoke shows no fracture, the cause is some combination of (a) PCC
   physics genuinely being deep VHCF (Carrara structural asymmetry as Phase 1
   FEM lit pointed to), (b) the intact-bar loading actually under-loading the
   cracked specimen, (c) the toy-vs-PCC geometry mismatch above. **Do not
   write "Phase 2A confirms framework insufficiency" off this smoke alone.**

## What this smoke CAN do

- Validate that the PIDL training loop runs at PCC-normalized parameter
  values without numerical pathology (NaN, exploding gradients, etc.).
- Give a baseline ᾱ accumulation trajectory at the new dimensionless scale,
  which can be compared to Phase 1 toy trajectories.
- Surface any infrastructure bugs (NN output scaling, mesh quadrature, etc.)
  before more expensive Phase 2B work.

## Expected trajectory (under corrected w1_norm=c_w, expert P0 fix 2026-05-14)

At `disp_ratio_intact=0.75` with σ_char Griffith scaling:
- ψ_per_cycle_norm ≈ (0.058)²/2 ≈ 1.7e-3   (deep subcritical)
- α_T_norm = 100 (Baktheer-cal)
- Linear-regime cycles to ᾱ→α_T: ~6×10⁴ (well beyond paper-feasible PIDL run)
- → smoke at N=50 expected to show ᾱ ≈ 0.085 (= 0.085% of α_T), no fatigue
  activation, no observable d localization. **This is a stretched-timescale
  diagnostic, not a fracture run.**

## Usage

    python run_pcc_baseline_umax.py 0.75 --n-cycles 50 --seed 1
    # 0.75 = disp_ratio_intact (intact-bar mapping to nominal stress = 0.75·f_t)
"""
import sys, argparse
from pathlib import Path

p = argparse.ArgumentParser(description="Phase 2A units-transition smoke runner")
p.add_argument("disp_ratio_intact", type=float,
               help="Intact-bar displacement ratio: prescribes u_top such that "
                    "an uncracked bar would have σ = ratio·f_t. "
                    "NOT a calibrated cracked-geometry nominal stress.")
p.add_argument("--n-cycles", type=int, default=50)
p.add_argument("--seed",     type=int, default=1)
p.add_argument("--pff-model", choices=["AT1", "AT2"], default="AT1",
               help="Phase-field model variant (default AT1, matches Phase 1)")
args = p.parse_args()

# Inject sys.argv so main.py / config.py sees expected positional args
sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Pre-import config (loads toy defaults) + PCCScaling (PCC params + non-dim)
import config
from scaling import PCCScaling

# ── 1. Build PCC scaling and apply overrides ────────────────────────────────
s = PCCScaling.baktheer_default(pff_model=args.pff_model)

print("=" * 72)
print(s.summary())
print("=" * 72)

# Material props: switch to PCC normalized values
config.mat_prop_dict["mat_E"]  = s.mat_E_norm    # = 1.0
config.mat_prop_dict["mat_nu"] = s.mat_nu_norm   # = 0.18 (PCC, vs toy 0.3)
config.mat_prop_dict["w1"]     = s.w1_norm       # ≈ 0.00344 for AT1 PCC
config.mat_prop_dict["l0"]     = s.l0_norm       # = 0.02 (vs toy 0.01)

# PFF model: match scaling choice (must agree on c_w)
config.PFF_model_dict["PFF_model"] = args.pff_model

# Fatigue: PCC alpha_T calibrated by Baktheer, disp from intact-bar mapping
# (NB: realized cracked-geometry nominal stress is LESS than ratio·f_t — see header)
config.fatigue_dict["alpha_T"]  = s.alpha_T_norm                            # ≈ 100
config.fatigue_dict["disp_max"] = s.disp_for_stress_intact(args.disp_ratio_intact * s.ft_phys)
config.fatigue_dict["n_cycles"] = args.n_cycles
config.rebuild_disp_cyclic()

# Domain + crack already match toy [-0.5, 0.5]² + half-width notch when
# L_char = W_phys (by construction). No mesh change needed; toy mesh
# `meshed_geom1.msh` is the right normalized geometry.

# ── 2. Rebuild model_path with explicit _pcc tag ────────────────────────────
_fat = config.fatigue_dict
_mat = config.mat_prop_dict
_pcc_tag = (
    f"_pcc"
    f"_dispR{args.disp_ratio_intact}"   # intact-bar disp ratio (not calibrated nominal stress)
    f"_aT{_fat['alpha_T']:.1f}"
    f"_N{_fat['n_cycles']}"
    f"_R{_fat['R_ratio']}"
    f"_seed{config.network_dict['seed']}"
    f"_{args.pff_model}"
)
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + args.pff_model
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _pcc_tag
    + "_baseline"
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# ── 3. Write model_settings.txt with PCC physical + non-dim provenance ─────
with open(config.model_path / Path("model_settings.txt"), "w") as f:
    f.write(f"[runner] run_pcc_baseline_umax.py  (Phase 2A, 2026-05-14)\n")
    f.write(f"\n--- network ---\n")
    f.write(f"hidden_layers: {config.network_dict['hidden_layers']}\n")
    f.write(f"neurons: {config.network_dict['neurons']}\n")
    f.write(f"seed: {config.network_dict['seed']}\n")
    f.write(f"activation: {config.network_dict['activation']}\n")
    f.write(f"PFF_model: {args.pff_model}\n")
    f.write(f"\n--- PCC physical (Baktheer 2024 cal) ---\n")
    f.write(f"E_phys: {s.E_phys} MPa\n")
    f.write(f"nu_phys: {s.nu_phys}\n")
    f.write(f"G_f_phys: {s.G_f_phys} N/mm\n")
    f.write(f"ft_phys: {s.ft_phys} MPa\n")
    f.write(f"ell_phys: {s.ell_phys} mm\n")
    f.write(f"alpha_T_phys: {s.alpha_T_phys} N/mm²\n")
    f.write(f"Domain: {s.W_phys}x{s.H_phys} mm, a0={s.a0_phys} mm (toy-mesh-reuse, a0/W=0.5; NOT FEM PCC line's a0=5mm)\n")
    f.write(f"disp_ratio_intact: {args.disp_ratio_intact}\n")
    f.write(f"  -> u_top_target_intact: {args.disp_ratio_intact * s.ft_phys / s.E_phys * s.H_phys:.4e} mm "
            f"(intact-bar mapping; realized cracked nominal stress is LESS)\n")
    f.write(f"\n--- characteristic scales ---\n")
    f.write(f"L_char: {s.L_char} mm\n")
    f.write(f"sigma_char (Griffith): {s.sigma_char:.4f} MPa\n")
    f.write(f"u_char: {s.u_char:.4e} mm\n")
    f.write(f"psi_char: {s.psi_char:.4e} MPa\n")
    f.write(f"\n--- non-dim (passed to PIDL) ---\n")
    f.write(f"mat_E_norm: {s.mat_E_norm}\n")
    f.write(f"mat_nu_norm: {s.mat_nu_norm}\n")
    f.write(f"w1_norm: {s.w1_norm:.6f}\n")
    f.write(f"l0_norm: {s.l0_norm}\n")
    f.write(f"alpha_T_norm: {s.alpha_T_norm}\n")
    f.write(f"disp_max_norm: {_fat['disp_max']:.6f}\n")
    f.write(f"n_cycles: {_fat['n_cycles']}\n")

print(f"PCC archive: {config.model_path}")
print(f"Loading u_norm = {_fat['disp_max']:.4f}  (physical: {s.disp_norm_to_phys(_fat['disp_max']):.4e} mm)")
print(f"alpha_T_norm = {_fat['alpha_T']:.2f}  (physical: {s.alpha_T_phys} N/mm²)")
print("=" * 72)

# ── 4. Hand off to main.py ──────────────────────────────────────────────────
main_path = HERE / "main.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
