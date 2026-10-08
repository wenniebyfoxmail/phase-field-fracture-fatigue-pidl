# S04-E012 decision

Status: formal read-only run **PASS**; independent Evidence review pending.

The locked E008 c82s4 and E006 c83s4 UV-rebalanced arrays satisfy the frozen conditional UV-derived-reference contract when reassembled by the reviewed E012 runner. The original fields fail `rho_u <= 1e-3`, while the rebalanced fields pass:

- c82s4: `1.35334531796` → `4.58098492064e-11`.
- c83s4: `0.0413314797153` → `4.39640742997e-11`.
- c82s5: parent-reported read-only control `2.70286978692e-14`; no polished field was created or inferred.

Both original and polished c82s4/c83s4 fields satisfy all 596 prescribed essential UV values with zero maximum absolute error at the `1e-12` gate. The fixed damage identity passes. The c83 locked prior, target trial-fatigue, free-damage set, and exact `0 <= previous_damage <= target_damage <= 1` checks pass. Hard-KKT provenance remains asymmetric by design: c82 uses the locked E008 parent report, c83 is recomputed from the locked E003 prior and target fatigue, and c82s5 is a locked E010 parent control.

The required UV correction is state dependent. At c82s4, UV mass RMS/Us is `0.0932593%`, strain relative L2 is `0.472069%`, and active-driver relative L2 is `18.5616%`. At c83s4 the corresponding changes are `0.000965909%`, `0.0278802%`, and `0.063566%`. Thus the c82 pre-transition peak needs a much larger active-driver correction than the c83 transition state, even though both can be UV-rebalanced below the same residual gate.

Adopt the two polished fields only as **fixed-damage, frozen-fatigue, UV-rebalanced derived references** for the UV block. Their native phase residual and native joint acceptance were not reassembled after changing UV. They are not coupled equilibria, true solutions, mesh-converged references, full trajectories, or qualified FEM teachers. Every row therefore retains `full_teacher=NOT_QUALIFIED`.
