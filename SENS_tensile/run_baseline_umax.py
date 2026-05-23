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
p.add_argument("--adaptive-lambda-hist", action="store_true",
               help="Enable Wang-style adaptive weighting for the irreversibility penalty.")
p.add_argument("--lambda-hist-min", type=float, default=1e-3,
               help="Lower clip for adaptive lambda_hist.")
p.add_argument("--lambda-hist-max", type=float, default=1.0,
               help="Upper clip for adaptive lambda_hist.")
p.add_argument("--lambda-hist-smooth", type=float, default=1.0,
               help="Moving-average update fraction for lambda_hist (1.0 = no smoothing).")
p.add_argument("--lambda-hist-initial", type=float, default=1.0,
               help="Initial lambda_hist before the first adaptive update.")
p.add_argument("--lambda-hist-update-every", type=int, default=1,
               help="Update lambda_hist every N cycles when adaptive mode is enabled.")
p.add_argument("--lambda-hist-start-cycle", type=int, default=0,
               help="First cycle eligible for scheduled lambda_hist updates.")
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
config.fatigue_dict["adaptive_lambda_hist"] = {
    "enable": bool(args.adaptive_lambda_hist),
    "initial": float(args.lambda_hist_initial),
    "min": float(args.lambda_hist_min),
    "max": float(args.lambda_hist_max),
    "smooth": float(args.lambda_hist_smooth),
    "update_every": int(args.lambda_hist_update_every),
    "start_cycle": int(args.lambda_hist_start_cycle),
    "eps": 1e-30,
}
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
_baseline_suffix = "_baseline"
if args.adaptive_lambda_hist:
    _baseline_suffix += "_adapthist"
_dir_name = (
    "hl_" + str(config.network_dict["hidden_layers"])
    + "_Neurons_" + str(config.network_dict["neurons"])
    + "_activation_" + config.network_dict["activation"]
    + "_coeff_" + str(config.network_dict["init_coeff"])
    + "_Seed_" + str(config.network_dict["seed"])
    + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
    + "_gradient_" + str(config.numr_dict["gradient_type"])
    + _fatigue_tag
    + _baseline_suffix
)
config.model_path             = config.resolve_archive_dir(HERE, _dir_name)
config.trainedModel_path      = config.model_path / Path("best_models/")
config.intermediateModel_path = config.model_path / Path("intermediate_models/")
config.model_path.mkdir(parents=True, exist_ok=True)
config.trainedModel_path.mkdir(parents=True, exist_ok=True)
config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
try:
    config.writer.close()
except Exception:
    pass
config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))

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
    alh = _fat.get("adaptive_lambda_hist", {})
    f.write(f"\nadaptive_lambda_hist_enable: {alh.get('enable', False)}")
    f.write(f"\nadaptive_lambda_hist_initial: {alh.get('initial', 1.0)}")
    f.write(f"\nadaptive_lambda_hist_min: {alh.get('min', 1e-3)}")
    f.write(f"\nadaptive_lambda_hist_max: {alh.get('max', 1.0)}")
    f.write(f"\nadaptive_lambda_hist_smooth: {alh.get('smooth', 1.0)}")
    f.write(f"\nadaptive_lambda_hist_update_every: {alh.get('update_every', 1)}")
    f.write(f"\nadaptive_lambda_hist_start_cycle: {alh.get('start_cycle', 0)}")
    f.write(f"\n[runner] run_baseline_umax.py (May-4 2026 bugfix version)")

print("=" * 72)
print("Baseline pure-physics PIDL runner (BUGFIXED May-4 2026)")
print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
if args.adaptive_lambda_hist:
    print(
        f"  λ_hist   = adaptive | initial={args.lambda_hist_initial} | "
        f"clip=[{args.lambda_hist_min}, {args.lambda_hist_max}] | "
        f"smooth={args.lambda_hist_smooth} | "
        f"update_every={args.lambda_hist_update_every}"
    )
else:
    print("  λ_hist   = 1.0 (fixed)")
print(f"  archive   = {_dir_name}")
print(f"  full path = {config.model_path}")
print("=" * 72)

# Now exec main.py contents in current namespace (config already overridden + paths rebuilt)
main_path = HERE / "main.py"
exec(compile(main_path.read_text(), str(main_path), "exec"), {"__name__": "__main__", "__file__": str(main_path)})
