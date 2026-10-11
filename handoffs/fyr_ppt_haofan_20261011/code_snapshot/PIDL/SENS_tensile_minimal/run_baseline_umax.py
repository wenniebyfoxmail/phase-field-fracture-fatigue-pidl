#!/usr/bin/env python3
"""run_baseline_umax.py — wraps main.py to override umax + n_cycles + seed via CLI.

★ May-4 2026 BUGFIX (commit pending):
   Earlier version set `config.savefolder_name = arch` AFTER `import config`.
   That was a no-op because:
     - config.py builds `model_path` / `trainedModel_path` from individual
       network_dict / fatigue_dict variables AT IMPORT TIME (line 331-345).
     - config.py never reads `savefolder_name`.
   Result: ALL baseline runs (u=0.11/0.13/0.14 across seeds) wrote into the
   SAME archive `Seed_<seed>_..._N300_R0.0_Umax0.12/` and corrupted each
   other (NN + fatigue history resumed across runs at different umax).

   Fix: follow the pattern from `run_e2_reverse_umax.py` (lines 125-140) —
   override config.fatigue_dict, then MANUALLY rebuild config.model_path /
   trainedModel_path / intermediateModel_path using overridden values, then
   exec main.py.
"""
import sys, argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("umax", type=float)
p.add_argument("--n-cycles", type=int, default=300)
p.add_argument("--seed", type=int, default=1)
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

# 2) MANUALLY REBUILD model_path / trainedModel_path / intermediateModel_path
#    using overridden values (config.py already constructed these at import
#    using DEFAULT disp_max/n_cycles, so we must override here).
#    Mirrors the path-construction logic in config.py:330-346 + adds _baseline suffix.
_fat = config.fatigue_dict
_fatigue_tag = (
    f"_fatigue_on_{_fat['accum_type']}_{_fat['degrad_type'][:3]}"
    f"_aT{_fat['alpha_T']}_N{_fat['n_cycles']}_R{_fat['R_ratio']}"
    f"_Umax{_fat['disp_max']}"
)
# Suffix '_baseline' to distinguish from other archive types (oracle, pathC, ...)
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + "_baseline"
)
config.model_path             = HERE / Path(_dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

# 3) Re-write model_settings.txt in the corrected archive (config.py wrote it
#    once at import to the WRONG path; rewrite here).
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
    f.write(f"\n[runner] run_baseline_umax.py (May-4 2026 bugfix version)")

print("=" * 72)
print("Baseline pure-physics PIDL runner (BUGFIXED May-4 2026)")
print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
print(f"  archive   = {_dir_name}")
print(f"  full path = {config.model_path}")
print("=" * 72)

# Now exec main.py contents in current namespace (config already overridden + paths rebuilt)
main_path = HERE / "main.py"
exec(compile(main_path.read_text(), str(main_path), "exec"), {"__name__": "__main__", "__file__": str(main_path)})
