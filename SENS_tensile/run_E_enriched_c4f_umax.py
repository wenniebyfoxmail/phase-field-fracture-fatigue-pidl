#!/usr/bin/env python3
"""run_E_enriched_c4f_umax.py — Run E (FIXED 2026-05-14):
Direction 5 Enriched Ansatz + C4 exact-BC + C10 Fourier features.

Earlier version (commit 941ca93) attempted to enable ansatz_dict via direct
config mutation before exec'ing run_exact_bc_fourier_umax.py. That FAILED
silently: the inner runner unconditionally set `config.ansatz_dict["enable"]
= False` at line 93, wiping Direction 5 before training. The 2026-05-14
"identical to C4+Fourier" result was therefore Direction 5 NEVER ENABLED.

This fixed version invokes the inner runner with the new `--enable-ansatz`
flag (added in commit at same time as --side-power), which properly enables
ansatz_dict and tags the archive `_enriched_ansatz_modeI_v1`.

Stack:
- C4 exact-BC: u = u_lift + tb·side²·NN_corr, σ_xx=σ_xy=0 at x=±0.5
- C10 Fourier σ=30: γ(x) input encoding
- Direction 5: NN output += c·χ(r)·F^I(r,θ) (Williams √r Mode I)

Usage:
    python run_E_enriched_c4f_umax.py 0.12 --n-cycles 100 --seed 1 --sigma 30 --nu 0.3
"""
import sys
from pathlib import Path

# Force --enable-ansatz into the args; pass everything else through.
sys.argv = sys.argv + ["--enable-ansatz"]

HERE = Path(__file__).parent
main_path = HERE / "run_exact_bc_fourier_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
