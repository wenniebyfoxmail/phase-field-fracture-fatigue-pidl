#!/usr/bin/env python3
"""run_A_oracle_psi_c4f_umax.py — Run A of the C4+supervision diagnostic set.

A = E2-reverse ψ⁺ drop-in (process zone) + C4 exact-BC + C10 Fourier features.

Tests hypothesis: "C4 over-constrains displacement in the side² gating zone
→ suppresses ψ⁺ near boundary → blocks ᾱ accumulation → no fracture.
If we inject FEM ψ⁺ in the process zone (B_{2ℓ₀}(tip)), does C4+Fourier
recover N_f match while preserving V7 closure?"

Stack:
- C4 exact-BC: enforces σ_xx=σ_xy=0 at x=±0.5 by construction (V7 PASS)
- C10 Fourier σ=30: spectral lift for tip-zone fine features
- E2 oracle ψ⁺: drop-in replacement of ψ⁺ in B_{2ℓ₀}(tip) with FEM ψ⁺

Usage (same args as run_e2_reverse_umax.py):
    python run_A_oracle_psi_c4f_umax.py 0.12 --n-cycles 100
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Save the user CLI args (needed for the inner runner's argparse)
_user_argv = list(sys.argv)

# Temporarily stub sys.argv with config-friendly positionals so `import config`
# doesn't crash on `int(sys.argv[1])` when our first positional is the umax float.
sys.argv = ["run_A_oracle_psi_c4f_umax.py", "8", "400", "1", "TrainableReLU", "1.0"]

import config  # noqa: E402
config.exact_bc_dict["enable"] = True
config.exact_bc_dict["mode"] = "sent_plane_strain"
config.exact_bc_dict["nu"] = config.mat_prop_dict["mat_nu"]

config.fourier_dict["enable"] = True
config.fourier_dict["sigma"] = 30.0
config.fourier_dict["n_features"] = 128
config.fourier_dict["seed"] = 0

# Restore user argv for the inner runner's argparse
sys.argv = _user_argv

print("=" * 72)
print("Run A: E2 oracle ψ⁺ + C4 exact-BC + C10 Fourier σ=30 stack")
print(f"  exact_bc_dict.enable = {config.exact_bc_dict['enable']}")
print(f"  fourier_dict.enable  = {config.fourier_dict['enable']} (σ={config.fourier_dict['sigma']})")
print("=" * 72)

main_path = HERE / "run_e2_reverse_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
