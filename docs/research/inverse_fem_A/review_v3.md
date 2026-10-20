# Independent offline-interface delta review v3

- Date: 2026-10-20, Europe/London.
- Reviewer: independent read-only Codex subagent `/root/q4_inverse_review`.
- Exact reviewed commit: `4c0c78b559af98e5349ea28f5517add93e08bc0b`.
- Verdict: **MODIFY_AND_REREVIEW**. The prior c525455c review carries forward;
  baseline source/tests were unchanged and were not rerun.

## Findings

1. P2: bind one material direction for the whole sensitivity tape. Per-step
   parameters could change while old history tangents persisted; omitting them
   defaulted to zero. The resulting chain mixed unrelated perturbations.
2. P2: reject wrong-sign bound multipliers outside the weak band. Classification
   by absolute multiplier alone allowed a small negative lower multiplier or
   positive upper multiplier inside a broader primal tolerance to be called
   strongly active, incorrectly enforcing sticking without dual feasibility.

## Independent checks and limits

The new focused suite independently passed **15 tests in 0.17s**. The reviewer
inspected all new modules, tests, source/header binding tool and saved result,
source timing anchors, and offline documentation. A supplied small-array
counterexample reproduced finding 2. Sparse block equations and the scaled
LU-comparison/residual bound construction were coherent within the explicitly
stated float64 numerical-evidence contract. No other actionable finding was
reported in the bounded review.

No primal FEM, native-size solve, trajectory replay, inversion, parameter
candidate evaluation, remote work or reviewer file change occurred. Native
performance/bound usefulness, switched-path uniqueness, initial-array equivalence
and material recovery remain unverified. Repairs require exact-version focused
rereview; this verdict is not execution authority.
