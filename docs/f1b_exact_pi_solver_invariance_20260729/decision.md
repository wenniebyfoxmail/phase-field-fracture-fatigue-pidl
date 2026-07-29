# F1b Fresh Dimensional Solver-Invariance Decision

## Verdict

**BLOCKED, not passed.** The immutable F1b producer handoff is complete, but no
approved Windows-FEM producer was confirmed reachable during this follow-up and
no fresh dimensional output exists yet.

The pre-launch review found that the earlier v1 handoff retained dimensional
Newton tolerances and demanded replay-level field identity. That v1 contract
was never launched and is superseded. The v2 lock now scales every active
dimensional residual/tangent control and uses solver/mesh-justified fresh-solve
field, support, and event gates frozen before launch.

The Mac did not run PIDL training or substitute itself for Windows-FEM. Codex
producer-thread discovery timed out twice, and the latest committed
Windows-FEM outbox entry is dated 2026-06-10. Therefore `fresh_fem_solve` remains
`false` for the evidence package and the solver-invariance gate remains open.

## Prepared Execution

- Handoff: `producer_handoffs/f1b_exact_pi_20260729/`
- Locked runner: `main_F1b_exact_pi_dimensional.m`
- Locked solver derivative: `solve_fatigue_fracture_f1b.m`
- Locked Newton derivative: `newton_raphson_f1b.m`
- Tolerance audit: `TOLERANCE_AUDIT.md`
- Windows launcher: `launch_F1b_exact_pi.ps1`
- Input contract: `INPUT_LOCK.json`
- Analyzer: `SENS_tensile/analyze_f1b_exact_pi_solver.py`
- Producer request: `docs/handovers/windows_fem_inbox.md`, Request 26

The launcher verifies hashes, requires a clean shared checkout, derives a new
output name from the source commit, and refuses overwrite/resume. The candidate
scales in-plane geometry and thickness by ten, uses `E=3`, `Gc=0.3`,
`ell=0.1`, `Umax=1.2`, `alpha_T=1.5`, and preserves the full formal eta0
plane-strain AT1/AMOR hard-recovery explicit-eight-step contract.

The candidate force residual scale is `300`; the phase residual/tangent scale
is `3000`. The candidate Newton tolerances are therefore `3e-4` and `1.2`, the
hard-recovery diagonal floor is `3e-5`, and staggered convergence uses
`||R_u||/300 + ||R_d||/3000 <= 4e-4`. Same-cycle c20/c40/c60 and first-hit and
confirmed own-event states are all required.

## Claim Boundary

F1a remains only a scaling/I-O replay. F1b has no scientific result until a
fresh producer output is returned and passes the immutable analyzer. Even a
future F1b pass would establish similarity for one homogeneous toy benchmark,
not road validation, layered-road transfer, temperature/rate transfer, or a
cycle-to-traffic mapping.
