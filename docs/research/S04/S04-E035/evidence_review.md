# Independent evidence review — S04-E035

Verdict: REVIEW_PASS, bounded exploratory evidence only.
Channel: independent read-only Codex reviewer `l2_code_review`; inherited model,
no separate backend identity claimed. No reviewer training/producer execution.
Protocol r1; producer `5f5428d7586f68bd6cace033f99737c2b5d334c4`;
final analysis `5af404906cce279d06d22b2b153ebbcbdbfda143`.

Access verified: all six local raw pairs, original checkpoints/losses/networks,
analysis tables/scripts and final PNGs.

Independent checks actually completed:

- Every initial NPZ field is bitwise identical within each pair; histories
  equal the original preceding checkpoint and remain frozen in both finals.
- All six controls exactly reproduce all final network parameter arrays,
  full loss sequences, three energy components and iteration counts.
- All u/v/d/psi/trial fatigue-history/degradation RMS/max/relative-L2 and
  common-energy changes recompute correctly from saved outputs.
- All12 trial fatigue-history/degradation fields and tri3 retreat diagnostics
  reproduce from saved fields and the original checkpoints.
- Final unloading/optimization/overview/parameter-scale figures are aligned,
  readable, use correct shared scales and explicitly label capped arms.
- Focused follow-up: the six added offline `max(hist_alpha,d)` lines in
  analysis5af40490 and all three new columns match independent calculations
  for all six states. At c1/c40 unload the additional nodes with history
  damage>0.5 are11.5922%/6.32581%, nodal fractions, not area fractions.

Interpretation accepted: state-dependent finite-solve sensitivity, severe
disruption in two capped unloading solves and large weight growth. Early
stopping is loss stagnation, not physical stationarity. Parameter-gradient
norms change with parameterization and are not equilibrium residuals.
Canonical L2 in the zero arm is hypothetical, not an actual loss term.
Retain the float32 sign-product underflow caveat; it does not affect the
field differences or exact control replay.

Blocked claims: subsequent rollout, changed initialization/pretraining,
physical convergence, generalization, or a statement that all zero-L2 states
fail/slow down. Deterministic trial damage-history commits are not a rollout.
No new solve is needed to interpret this completed bounded exploration.
