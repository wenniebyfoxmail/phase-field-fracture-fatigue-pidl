#!/usr/bin/env python3
"""run_B_mit8_c4f_umax.py — Run B of the C4+supervision diagnostic set.

B = MIT-8 ψ⁺ MSE warmup (gradient-based) + C4 exact-BC + C10 Fourier features.

Tests hypothesis: "Does gradient-based ψ⁺ supervision (vs A's hard drop-in)
push back through u-field NN so that POST-RELEASE the C4+Fourier ansatz
preserves the FEM-like ψ⁺ trajectory? If yes, the side² gating's limitation
is an OPTIMIZATION landscape issue (NN representation can hold FEM-like
ψ⁺ but pure-physics loss can't find it). If post-release decays back to
non-FEM, the limitation is a REPRESENTATION issue."

Stack:
- C4 exact-BC: enforces σ_xx=σ_xy=0 at x=±0.5 by construction
- C10 Fourier σ=30: spectral lift
- MIT-8 ψ⁺ MSE warmup: joint loss = physics + λ·MSE(log10 ψ⁺_PIDL, log10 ψ⁺_FEM)
  for cycles 1..K, then release (λ=0) for K+1..N

Usage (same args as run_mit8_warmup_umax.py):
    python run_B_mit8_c4f_umax.py 0.12 --K 40 --n-cycles 100 --lambda 1.0
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_user_argv = list(sys.argv)
sys.argv = ["run_B_mit8_c4f_umax.py", "8", "400", "1", "TrainableReLU", "1.0"]

import config  # noqa: E402
config.exact_bc_dict["enable"] = True
config.exact_bc_dict["mode"] = "sent_plane_strain"
config.exact_bc_dict["nu"] = config.mat_prop_dict["mat_nu"]

config.fourier_dict["enable"] = True
config.fourier_dict["sigma"] = 30.0
config.fourier_dict["n_features"] = 128
config.fourier_dict["seed"] = 0

sys.argv = _user_argv

print("=" * 72)
print("Run B: MIT-8 ψ⁺ MSE warmup + C4 exact-BC + C10 Fourier σ=30 stack")
print(f"  exact_bc_dict.enable = {config.exact_bc_dict['enable']}")
print(f"  fourier_dict.enable  = {config.fourier_dict['enable']} (σ={config.fourier_dict['sigma']})")
print("=" * 72)

main_path = HERE / "run_mit8_warmup_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
