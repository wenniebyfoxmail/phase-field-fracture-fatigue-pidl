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

Usage (same as run_e2_reverse_umax.py + same args):
    python run_A_oracle_psi_c4f_umax.py 0.12 --n-cycles 100 --seed 1

Note: this wrapper enables C4 + Fourier in config, then execs the patched
run_e2_reverse_umax.py (which now passes both dicts through to construct_model
and FieldComputation).
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Enable C4 + Fourier in config BEFORE the runner imports them
import config
config.exact_bc_dict["enable"] = True
config.exact_bc_dict["mode"] = "sent_plane_strain"
config.exact_bc_dict["nu"] = config.mat_prop_dict["mat_nu"]

config.fourier_dict["enable"] = True
config.fourier_dict["sigma"] = 30.0
config.fourier_dict["n_features"] = 128
config.fourier_dict["seed"] = 0

print("=" * 72)
print("Run A: E2 oracle ψ⁺ + C4 exact-BC + C10 Fourier σ=30 stack")
print(f"  exact_bc_dict.enable = {config.exact_bc_dict['enable']}")
print(f"  fourier_dict.enable  = {config.fourier_dict['enable']} (σ={config.fourier_dict['sigma']})")
print("=" * 72)

# Hand off to the patched E2 reverse runner via exec
main_path = HERE / "run_e2_reverse_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
