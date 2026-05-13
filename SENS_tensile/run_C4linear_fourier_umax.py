#!/usr/bin/env python3
"""run_C4linear_fourier_umax.py — C4 with side^1 (linear gating) + C10 Fourier.

Diagnostic for the "side² over-constrains propagation" hypothesis discovered
2026-05-14 across Run A/B/E (E2 ψ⁺ + C4F, MIT-8 ψ⁺ MSE + C4F, Direction 5
enriched ansatz + C4F): in ALL three runs, crack_tip stayed pinned at (0, 0)
and α never reached the boundary, regardless of supervision or output
enrichment. The common factor: C4's side² gating that damps NN influence
across the whole side zone, not just at the boundary.

This wrapper invokes run_exact_bc_fourier_umax.py with --side-power 1.0
so the correction bubble becomes tb · side · NN_corr (linear instead of
quadratic). V7 (σ_xx=σ_xy=0 at boundary) is NO LONGER PASS BY CONSTRUCTION
— it will likely WARN or FAIL. Quantifying that trade-off is part of the
diagnostic.

Math:
- Historical C4: side² — V7 PASS by construction; aggressive interior damping
- C4-linear:     side  — V7 maybe WARN; less interior damping, maybe allows propagation

Usage:
    python run_C4linear_fourier_umax.py 0.12 --n-cycles 100 --seed 1 --sigma 30 --nu 0.3
"""
import sys
from pathlib import Path

# Force --side-power 1.0 into the args; pass everything else through.
sys.argv = sys.argv + ["--side-power", "1.0"]

HERE = Path(__file__).parent
main_path = HERE / "run_exact_bc_fourier_umax.py"
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
     {"__name__": "__main__", "__file__": str(main_path)})
