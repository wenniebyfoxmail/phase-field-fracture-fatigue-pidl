#!/usr/bin/env python3
"""run_baseline_umax.py — wraps main.py to override umax via CLI."""
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

# Override BEFORE config is imported by main.py — but config needs to be importable.
# Pre-import config, mutate, then exec main.py
import config
config.fatigue_dict["disp_max"] = args.umax
config.fatigue_dict["n_cycles"] = args.n_cycles
config.rebuild_disp_cyclic()

# Manually rebuild savefolder name with updated umax/n_cycles
arch = (
    f"hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_{args.seed}_"
    f"PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    f"N{args.n_cycles}_R0.0_Umax{args.umax}_baseline"
)
config.savefolder_name = arch

print("=" * 72)
print(f"Baseline pure-physics PIDL runner")
print(f"  U_max = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
print(f"  archive = {arch}")
print("=" * 72)

# Now exec main.py contents in current namespace (config already overridden)
import builtins
main_path = HERE / "main.py"
exec(compile(main_path.read_text(), str(main_path), "exec"), {"__name__": "__main__", "__file__": str(main_path)})
