#!/usr/bin/env python3
"""run_C4linear_fourier_umax.py — C4 with side^1 (linear gating) + C10 Fourier.

Diagnostic for the "side² over-constrains propagation" hypothesis discovered
2026-05-14 across Run A/B/E (E2 ψ⁺ + C4F, MIT-8 ψ⁺ MSE + C4F, Direction 5
enriched ansatz + C4F): in ALL three runs, crack_tip stayed pinned at (0, 0)
and α never reached the boundary, regardless of supervision or output
enrichment. The common factor: C4's side² gating that damps NN influence
across the whole side zone, not just at the boundary.

This runner replaces side² with side^1 (linear) so NN influence is gated
less aggressively. V7 (σ_xx=σ_xy=0 at boundary) is NO LONGER PASS BY
CONSTRUCTION — it will likely WARN or FAIL. Quantifying that trade-off is
part of the diagnostic.

Math:
- Historical C4: u = u_lift + tb · side² · NN_corr
  - At boundary: side=0 AND ∂(side²)/∂x = 2·side·∂side/∂x = 0
  - → u=u_lift AND ∂u/∂x=∂u_lift/∂x exactly → σ_xx = 0 by construction
- C4-linear: u = u_lift + tb · side · NN_corr
  - At boundary: side=0 (u correct)
  - ∂(side)/∂x = ∓2/W ≠ 0 → ∂u/∂x has NN-derived term at boundary
  - σ_xx no longer guaranteed = 0 (but might be small)

If C4-linear allows propagation (Kt rises, α reaches boundary) → confirms
side² over-constrains and a less aggressive gating is the right direction.
If C4-linear ALSO fails → the issue is deeper than gating power.

Usage:
    python run_C4linear_fourier_umax.py 0.12 --n-cycles 100 --seed 1 --sigma 30 --nu 0.3
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_user_argv = list(sys.argv)
sys.argv = ["run_C4linear_fourier_umax.py", "8", "400", "1", "TrainableReLU", "1.0"]

import config  # noqa: E402

# C4 with linear gating (side^1 instead of side^2)
config.exact_bc_dict["enable"] = True
config.exact_bc_dict["mode"] = "sent_plane_strain"
config.exact_bc_dict["nu"] = config.mat_prop_dict["mat_nu"]
config.exact_bc_dict["side_power"] = 1.0  # ★ side^1 instead of side^2

config.fourier_dict["enable"] = True
config.fourier_dict["sigma"] = 30.0
config.fourier_dict["n_features"] = 128
config.fourier_dict["seed"] = 0

sys.argv = _user_argv

print("=" * 72)
print("Run C4-linear: side^1 gating + C10 Fourier σ=30 (V7 PASS by construction LOST)")
print(f"  exact_bc_dict.side_power = {config.exact_bc_dict['side_power']}")
print(f"  fourier_dict.enable      = {config.fourier_dict['enable']} (σ={config.fourier_dict['sigma']})")
print("  Diagnostic for side² over-constraint hypothesis")
print("=" * 72)

main_path = HERE / "run_exact_bc_fourier_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
