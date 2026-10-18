# S09-E010 independent design review

## Review identity

- Reviewer: ChatGPT Pro, Haofan account
- Conversation: https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb
- Initial packet: `S09-E010-design-review-packet-v1.zip`
- Initial packet SHA256:
  `ed29dc0a18035f0c44c2bc490e5421245d92d437c0fa4785d73c54b3a9f3bb03`
- Focused rereview packet: `S09-E010-design-rereview-packet-v2.zip`
- Focused rereview packet SHA256:
  `6b72504dc7122e9db6bb4db5641aaf256099f0262bf438ff40337f6b1551273c`

## Final verdict

`DESIGN_READY_PASS`

The reviewer read the v2 ZIP, matched its SHA256 and verified both manifest
entries. The only first-round blocker is closed. The permitted next chain is
limited to local implementation, deterministic no-step preflight and
exact-commit review. This verdict is neither Code Ready nor training
authorisation.

## First-round finding and repair

The first review returned `DESIGN_BLOCKED` because Level 6 could be implemented
independently of Level 5. In that reading, a candidate could satisfy the old
E009 relative clauses and persistence inequality while failing a
contemporaneous-`A25` protected ratio, then incorrectly bypass
`TARGETED_RANKING_SIGNAL_WITH_TRADEOFF`.

Protocol v2 states that `NOMINATE_CONFIRMATORY_P1` requires all conditions of
`ORIGINAL_RELATIVE_REPAIR_SIGNAL`, explicitly including the primary criterion
and all four contemporaneous-`A25` protected ratios, before the persistence
inequality is evaluated. The reviewer confirmed that this closes the ambiguity
without changing E009, any loss, coefficient, arm, threshold, dataset or
budget.

The unchanged `Delta_AUC >= 0.08` criterion is also expressed as
`Delta(2W+T) >= 4` over the fixed 25 pair comparisons. The reviewer confirmed
that the integer condition is strictly equivalent and prevents a direct
floating-point subtraction from rejecting an exact boundary result.

## Method findings retained from the full review

- The stated mapping is a fixed-native-mesh field-to-field state transition
  from the initial damage/history state and prescribed loading path to the
  peak damage/history/displacement state. The full prescribed path is an input,
  not a future state label.
- The physics term is limited to the native-Q4 AMOR mechanical-equilibrium
  residual on free displacement DOFs at the predicted peak. It does not enforce
  damage stationarity, fatigue-history evolution or the full incremental
  variational inequality. The limited-PINO claim is therefore appropriate.
- `L_S`, `L_A`, their fixed scale, mask threshold, empty/zero rules and
  supervision-only target boundary are specified sufficiently for
  implementation. Per-cycle losses must be formed before the frozen update
  reduction; pooling masks or squaring an averaged amplitude error would change
  the protocol.
- The projected multi-objective rule preserves `L_D` as a first-order anchor
  for finite nonstationary gradients. It does not guarantee that every loss
  decreases after an AdamW step or establish Pareto optimality.
- The primary AUC threshold has discrete headroom on this development packet.
  Passing it remains a development effect, not significance or generalisation
  evidence. The four protected ratios cover only their named behaviours.
- The exact-replay gate, fail-closed ordering and minimum evidence contract are
  adequate as design requirements. Their implementation remains unverified.

## Implementation checks requested by the reviewer

The no-step preflight must check finite gradients before stationary-branch or
norm arithmetic, preserve the per-cycle reduction, and verify
`G_B25-G_B0=0.25*q_P` at the same model state before the final global clip. The
classifier must use the integer pair-count condition and cumulative Level 6
logic exactly as frozen above.
