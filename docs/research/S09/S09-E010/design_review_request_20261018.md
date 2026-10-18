# S09-E010 design review request

Please review `experiment.md` as a prospective adaptive-development protocol.
Do not change E009 or reinterpret its frozen result. No optimiser execution or
fresh holdout is requested.

## Design summary

- Same fixed Stage-0A state-operator mapping, 16-cycle exposed development
  packet, native mesh, architecture, initial state, optimiser policy,
  mechanical-equilibrium residual, evaluator and 500-update endpoint.
- Three arms: exact E009 `A25` replay, support+amplitude-balanced `beta=.25`,
  and matched support+amplitude-balanced `beta=0`.
- The existing full-field `L_D=l_d+l_dr` remains the primary gradient anchor.
  Active-support and per-cycle amplitude gradients are separately norm-matched
  and conflict-projected against that anchor, exactly like the existing
  auxiliary directions. Their coefficients are fixed at 1.0.
- Target masks/amplitudes are supervision only. Full-field evaluation and all
  physics/hard-constraint paths remain unchanged.
- Primary development signal: `AUC_B25-AUC_A25 >= .08`. A balanced local repair
  additionally protects contemporaneous A25 `G/F` within 5%, `L_P` within 10%
  and `L_judge` within 5%. The original stricter E009 replay-relative outcome is
  retained as a higher, separate level.
- Total budget: 1,500 updates. No separate single-window pilot, sweep or fourth
  arm. A deterministic no-step implementation preflight is mandatory before
  exact-commit review and any run card.

## Questions

1. Is the experiment's single targeted claim appropriate for the E009
   bottleneck, and does the three-arm design identify only what it says?
2. Are `L_S`, `L_A`, `tau_s`, nodal reductions, physical scale, zero/empty rules
   and target-use boundary fully specified and leakage-safe?
3. Is the multi-objective direction well defined, with the unchanged
   full-field damage objective genuinely retained as the anchor?
4. Is `Delta_AUC>=.08` a defensible smallest meaningful development criterion,
   and are the protected ratios and graded hierarchy neither over-demanding nor
   permissive enough to hide trade-offs?
5. Are the exact replay gate, denominator rules, evidence minimum and
   deterministic preflight sufficient before implementation?

Return one of:

- `DESIGN_READY_PASS`, followed by the precise permitted next work; or
- `DESIGN_BLOCKED`, followed by the smallest concrete protocol repair.
