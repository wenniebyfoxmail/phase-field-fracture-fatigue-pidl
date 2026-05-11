#!/usr/bin/env python3
"""run_fourier_features_umax.py — C10 Fourier-feature input layer (Tancik 2020 / Xu 2025).

Prepends a frozen random Fourier feature map γ(x) = [cos(2π B x), sin(2π B x)] before the NN
to mitigate spectral bias on tip-zone high-frequency content. Anchored on:
  - Tancik et al. 2020 NeurIPS "Fourier features let networks learn high frequency functions"
  - Xu, Zhang, Cai 2025 JCP review §4.2 "On understanding and overcoming spectral biases..."

Sigma sizing rationale:
  Phase 1 toy units, ℓ=0.01 mm, FEM peak width h_FEM ~ 0.001 mm
  → target frequency ≈ 1/h ≈ 1000
  → choose σ such that 2π · σ · 5 ≈ 1000 (5σ tail)
  → σ ≈ 30 (default), sweep σ ∈ {10, 30, 100} for production smoke

Usage:
  python run_fourier_features_umax.py 0.12 --n-cycles 10 --seed 1 --sigma 30
  python run_fourier_features_umax.py 0.12 --n-cycles 10 --seed 1 --sigma 100 --n-features 256

Output:
  archive at hl_8_..._Umax<u>_fourier_sig<σ>_nf<nf>/
"""
import sys
import argparse
from pathlib import Path


p = argparse.ArgumentParser()
p.add_argument("umax", type=float)
p.add_argument("--n-cycles", type=int, default=10)
p.add_argument("--seed", type=int, default=1)
p.add_argument("--sigma", type=float, default=30.0,
               help="Fourier feature std σ (default 30; try 10, 100 for sweep)")
p.add_argument("--n-features", type=int, default=128,
               help="Number of Fourier frequencies (default 128 → 256 inner dim)")
p.add_argument("--fourier-seed", type=int, default=0,
               help="Seed for B matrix (independent of network seed)")
args = p.parse_args()

# Inject sys.argv so main.py sees expected positional args
sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Pre-import config, mutate, then exec main.py
import config

# 1) Override fatigue dict
config.fatigue_dict["disp_max"] = args.umax
config.fatigue_dict["n_cycles"] = args.n_cycles
config.rebuild_disp_cyclic()

# 2) Enable Fourier features
config.fourier_dict["enable"] = True
config.fourier_dict["sigma"] = args.sigma
config.fourier_dict["n_features"] = args.n_features
config.fourier_dict["seed"] = args.fourier_seed

# 3) MANUALLY REBUILD model_path / trainedModel_path / intermediateModel_path
#    using overridden values (same pattern as run_baseline_umax.py)
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_fourier_tag = f"_fourier_sig{args.sigma}_nf{args.n_features}"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _fourier_tag
)
config.model_path = config.PATH_ROOT / Path(_dir_name)
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path = config.model_path / Path("best_models/")
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# 4) Persist runner-specific settings to model_settings.txt for reproducibility
def _rewrite_model_settings():
    f_dict = config.fatigue_dict
    fr_dict = config.fourier_dict
    with open(config.model_path / Path("model_settings.txt"), "w") as f:
        f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
        f.write(f"\nneurons: {config.network_dict['neurons']}")
        f.write(f"\nseed: {config.network_dict['seed']}")
        f.write(f"\nactivation: {config.network_dict['activation']}")
        f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
        f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
        f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
        f.write(f"\ndisp_max: {f_dict['disp_max']}")
        f.write(f"\nn_cycles: {f_dict['n_cycles']}")
        f.write(f"\naccum_type: {f_dict['accum_type']}")
        f.write(f"\ndegrad_type: {f_dict['degrad_type']}")
        f.write(f"\nalpha_T: {f_dict['alpha_T']}")
        f.write(f"\nR_ratio: {f_dict['R_ratio']}")
        f.write(f"\nfourier: {fr_dict}")
        f.write(f"\n[runner] run_fourier_features_umax.py\n")

_rewrite_model_settings()

print("=" * 72)
print("C10 Fourier-feature PIDL runner")
print(f"  U_max       = {args.umax}  |  n_cycles = {args.n_cycles}  |  seed = {args.seed}")
print(f"  σ           = {args.sigma}  (target frequency band ~ {2 * 3.1416 * args.sigma * 5:.0f})")
print(f"  n_features  = {args.n_features}  (inner NN input dim = {2*args.n_features})")
print(f"  fourier_seed= {args.fourier_seed}  (B matrix random init seed)")
print(f"  archive     = {_dir_name}")
print(f"  full path   = {config.model_path}")
print("=" * 72)
print()

# 5) Exec main.py (carries all our config mutations into the run)
exec(open(HERE / "main.py").read())
