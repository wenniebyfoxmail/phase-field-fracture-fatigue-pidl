#!/usr/bin/env python3
"""run_E_enriched_c4f_umax.py — Run E: pure-physics output-end singularity injection.

E = Direction 5 Enriched Ansatz + C4 exact-BC + C10 Fourier features.

Tests hypothesis: "C4+Fourier alone cannot represent the √r crack-tip singular
displacement field, so ᾱ near boundary is artificially suppressed and the crack
cannot propagate to the free edge. Hard-inject the Mode I Williams term
c·χ(r)·F^I(r,θ) into NN output (XFEM-style enrichment) — if THIS unblocks
boundary propagation while preserving V7 closure, then the limitation is a
fundamental NN representation issue, NOT a supervision issue. Solves the
problem in PURE-PHYSICS (no FEM supervision needed)."

Stack (3-way composition):
- C4 exact-BC:   u = u_lift + tb·side²·NN_corr, σ_xx=σ_xy=0 at x=±0.5 by construction
- C10 Fourier σ=30: γ(x) = [cos(2πBx), sin(2πBx)] input to NN_corr
- Direction 5 Enriched Ansatz: NN_corr → NN_corr + c·χ(r)·F^I(r,θ)
  - F^I = Mode I Williams principal singular eigenfunction (∝ √r)
  - χ(r) = exp(-r/r_cutoff), localized at tip
  - c = nn.Parameter (learnable K_I scalar)
  - x_tip fixed at (0, 0)

If E succeeds (Kt rises, ᾱ propagates to boundary, fracture triggers near
baseline N_f=82), this is the PAPER-GRADE pure-physics closure of the
fracture mechanism — saves the C4+Fourier stack story.

If E fails (Kt still stuck at 6-7), supervision (A/B) is needed.

Usage (same as run_exact_bc_fourier_umax.py):
    python run_E_enriched_c4f_umax.py 0.12 --n-cycles 100 --seed 1
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Stub sys.argv for config.py import
_user_argv = list(sys.argv)
sys.argv = ["run_E_enriched_c4f_umax.py", "8", "400", "1", "TrainableReLU", "1.0"]

import config  # noqa: E402

# Enable C4 exact-BC
config.exact_bc_dict["enable"] = True
config.exact_bc_dict["mode"] = "sent_plane_strain"
config.exact_bc_dict["nu"] = config.mat_prop_dict["mat_nu"]

# Enable C10 Fourier σ=30
config.fourier_dict["enable"] = True
config.fourier_dict["sigma"] = 30.0
config.fourier_dict["n_features"] = 128
config.fourier_dict["seed"] = 0

# Enable Direction 5 Enriched Ansatz (output-end Williams singular injection)
config.ansatz_dict["enable"] = True
config.ansatz_dict["x_tip"] = 0.0
config.ansatz_dict["y_tip"] = 0.0
config.ansatz_dict["r_cutoff"] = 0.1   # ≈ 10·l₀
config.ansatz_dict["nu"] = config.mat_prop_dict["mat_nu"]
config.ansatz_dict["c_init"] = 0.01
config.ansatz_dict["modes"] = ["I"]

# Restore user argv for inner runner argparse
sys.argv = _user_argv

print("=" * 72)
print("Run E: Direction 5 Enriched Ansatz + C4 exact-BC + C10 Fourier σ=30")
print(f"  exact_bc_dict.enable = {config.exact_bc_dict['enable']}")
print(f"  fourier_dict.enable  = {config.fourier_dict['enable']} (σ={config.fourier_dict['sigma']})")
print(f"  ansatz_dict.enable   = {config.ansatz_dict['enable']} (Mode {config.ansatz_dict['modes']}, "
      f"r_cutoff={config.ansatz_dict['r_cutoff']}, c_init={config.ansatz_dict['c_init']})")
print("  → PURE-PHYSICS (no FEM supervision)")
print("=" * 72)

# Hand off to the C4+Fourier runner (which handles main.py + path tagging)
main_path = HERE / "run_exact_bc_fourier_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
