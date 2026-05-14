#!/usr/bin/env python3
"""run_sdf_ribbon_smoke.py — C8 v1 smoke: SDF / discontinuity-ribbon embedding (uv_only)

The "cheap version" of Zhao 2025 DENNs LineCrackEmbedding, per red-team pivot
(2026-05-14):

    γ(x, y) = sign(y) · sigmoid(-(x - x_tip) / ε)

NN sees (x, y, γ) instead of (x, y). γ is +1 above crack, −1 below, in the
cracked region (x < x_tip); smoothly → 0 ahead of the moving tip.

v1 (default, --apply-to uv_only): split NN — uv-net sees (x,y,γ), α-net sees
(x,y). γ NEVER reaches the α head. Tests the pure mechanism question:
"does giving the displacement field a discontinuity prior improve ψ⁺ at the
tip and downstream α evolution?" — without α taking a shortcut by latching
onto γ's sgn(y) jump.

v2 (--apply-to all): single NN, γ feeds all heads via shared weights. Kept for
ablation; do not use as first-pass.

Explicit isolation (per expert May 14): this smoke runs SDF ONLY. All other
mechanisms are forced OFF in the runner regardless of config.py defaults:
  - williams_dict   (Williams 8D feature inputs)
  - ansatz_dict     (Direction 5 enriched ansatz)
  - fourier_dict    (C10 Fourier features)
  - exact_bc_dict   (C4 hard side traction)
  - symmetry_prior  (C5 hard y² mirror)
  - adaptive_sampling_dict (C6 FI-PINN)
  - fatigue_dict.tip_weight_cfg  (Direction 3 tip weighting)

x_tip is updated each cycle from ψ⁺ argmax (top-k=10 centroid, reused from
Williams branch), with red-team C3 monotone clamp (no retreat).

Usage:
    python run_sdf_ribbon_smoke.py 0.12 --n-cycles 5 --seed 1
    python run_sdf_ribbon_smoke.py 0.12 --n-cycles 5 --seed 1 --epsilon 5e-4
    python run_sdf_ribbon_smoke.py 0.12 --n-cycles 5 --seed 1 --apply-to all   # v2

Sphere-of-influence metrics (per user, May 14): ᾱ_max, ψ⁺ peak, Kt, N_f,
V4 d-skew, V7 boundary σ — all saved to archive by existing pipeline.

Design memo: ~/.claude/projects/.../memory/design_sdf_dedem_may14.md
"""
import sys, argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("umax", type=float)
p.add_argument("--n-cycles", type=int, default=5)
p.add_argument("--seed", type=int, default=1)
p.add_argument("--epsilon", type=float, default=1e-3,
               help="sigmoid smoothing width for γ (default 1e-3, ≈ FEM mesh scale)")
p.add_argument("--apply-to", choices=["uv_only", "all"], default="uv_only",
               help="'uv_only' (v1, default, split NN; α-head does NOT see γ) "
                    "or 'all' (v2, single NN, γ reaches all heads)")
args = p.parse_args()

# Inject sys.argv so main.py sees expected positional args
sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Pre-import config, mutate, then exec main.py
import config

# 1) Override fatigue dict (rebuild_disp_cyclic uses these)
config.fatigue_dict["disp_max"] = args.umax
config.fatigue_dict["n_cycles"] = args.n_cycles
config.rebuild_disp_cyclic()

# 2) Enable SDF ribbon embedding (apply_to per CLI; default uv_only per red-team)
config.sdf_ribbon_dict = {
    "enable":   True,
    "epsilon":  args.epsilon,
    "apply_to": args.apply_to,
}

# 2b) ★ Expert isolation (2026-05-14): force every other mechanism OFF so this
#     smoke is a clean test of "SDF ribbon alone". Regardless of defaults in
#     config.py we explicitly disable them here.
config.williams_dict["enable"]            = False
config.ansatz_dict["enable"]              = False
config.fourier_dict["enable"]             = False
config.exact_bc_dict["enable"]            = False
config.symmetry_prior                     = False
config.adaptive_sampling_dict["enable"]   = False
# Direction-3 tip weighting lives inside fatigue_dict
if "tip_weight_cfg" in config.fatigue_dict:
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False

# 3) MANUALLY REBUILD model_path / trainedModel_path / intermediateModel_path
#    using overridden values (config.py already constructed these at import using
#    DEFAULT disp_max/n_cycles/sdf_ribbon_dict, so we must override here).
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_ribbon_tag = f"_sdfRibbon_eps{args.epsilon}_{args.apply_to}"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _ribbon_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# 4) Re-write model_settings.txt in the corrected archive
with open(config.model_path / Path("model_settings.txt"), "w") as f:
    f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
    f.write(f"\nneurons: {config.network_dict['neurons']}")
    f.write(f"\nseed: {config.network_dict['seed']}")
    f.write(f"\nactivation: {config.network_dict['activation']}")
    f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
    f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
    f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
    f.write(f"\ndisp_max (overridden): {_fat['disp_max']}")
    f.write(f"\nn_cycles (overridden): {_fat['n_cycles']}")
    f.write(f"\naccum_type: {_fat['accum_type']}")
    f.write(f"\ndegrad_type: {_fat['degrad_type']}")
    f.write(f"\nalpha_T: {_fat['alpha_T']}")
    f.write(f"\nR_ratio: {_fat['R_ratio']}")
    f.write(f"\n--- sdf_ribbon (C8 v1/v2, 2026-05-14) ---")
    f.write(f"\nsdf_ribbon_enable: {config.sdf_ribbon_dict['enable']}")
    f.write(f"\nsdf_ribbon_epsilon: {config.sdf_ribbon_dict['epsilon']}")
    f.write(f"\nsdf_ribbon_apply_to: {config.sdf_ribbon_dict['apply_to']}")
    f.write(f"\n--- explicitly disabled by runner ---")
    f.write(f"\nwilliams: {config.williams_dict['enable']}")
    f.write(f"\nansatz:   {config.ansatz_dict['enable']}")
    f.write(f"\nfourier:  {config.fourier_dict['enable']}")
    f.write(f"\nexact_bc: {config.exact_bc_dict['enable']}")
    f.write(f"\nsymmetry_prior: {config.symmetry_prior}")
    f.write(f"\nadaptive_sampling: {config.adaptive_sampling_dict['enable']}")
    f.write(f"\n[runner] run_sdf_ribbon_smoke.py (2026-05-14 C8 v1/v2)")

print("=" * 72)
print(f"SDF discontinuity-ribbon PIDL runner — C8 {'v1 uv_only' if args.apply_to=='uv_only' else 'v2 all-heads'} (2026-05-14)")
print(f"  U_max    = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
print(f"  ε        = {args.epsilon}   apply_to = {args.apply_to}")
print(f"  Isolated: williams=F  ansatz=F  fourier=F  exact_bc=F  sym=F  "
      f"adapt_samp=F  tip_w=F")
print(f"  archive  = {_dir_name}")
print(f"  full     = {config.model_path}")
print("=" * 72)

# Exec main.py contents in current namespace (config already overridden)
main_path = HERE / "main.py"
exec(compile(main_path.read_text(), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
