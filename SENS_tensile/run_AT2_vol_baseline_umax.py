#!/usr/bin/env python3
"""run_AT2_vol_baseline_umax.py — AT2 + volumetric split pure baseline.

All optional features disabled (SDF/Fourier/adaptive/spAlphaT/Williams/exact_bc/symY2).
Compare with run_baseline_umax.py (AT1) to isolate PFF model effect.

Usage:
    python run_AT2_vol_baseline_umax.py <umax> [--n-cycles N] [--seed S]
Example (smoke):
    python run_AT2_vol_baseline_umax.py 0.12 --n-cycles 30 --seed 1
"""
import sys, argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("umax", type=float)
p.add_argument("--n-cycles", type=int, default=300)
p.add_argument("--seed", type=int, default=1)
args = p.parse_args()

sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import config

# 1) Switch to AT2 (se_split stays 'volumetric' by default)
config.PFF_model_dict["PFF_model"] = "AT2"

# 2) Override fatigue params
config.fatigue_dict["disp_max"] = args.umax
config.fatigue_dict["n_cycles"] = args.n_cycles
config.rebuild_disp_cyclic()

# 3) Confirm all optional features are off (defensive)
config.williams_dict["enable"]          = False
config.ansatz_dict["enable"]            = False
config.symmetry_prior                   = False
config.exact_bc_dict["enable"]          = False
config.fourier_dict["enable"]           = False
config.adaptive_sampling_dict["enable"] = False
config.fatigue_dict["tip_weight_cfg"]["enable"]    = False
config.fatigue_dict["spatial_alpha_T"]["enable"]   = False
config.fatigue_dict["psi_hack"]["enable"]          = False

# 4) Rebuild model_path
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])   # AT2
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

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
    f.write(f"\n[runner] run_AT2_vol_baseline_umax.py")

print("=" * 72)
print("AT2 + volumetric PIDL baseline runner")
print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
print(f"  PFF_model = {config.PFF_model_dict['PFF_model']} | se_split = {config.PFF_model_dict['se_split']}")
print(f"  archive   = {_dir_name}")
print(f"  full path = {config.model_path}")
print("=" * 72)

main_path = HERE / "main.py"
exec(compile(main_path.read_text(), str(main_path), "exec"), {"__name__": "__main__", "__file__": str(main_path)})
