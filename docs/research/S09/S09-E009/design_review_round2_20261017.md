# S09-E009 design review round 2 — 2026-10-17

## Verdict

`REVISE_AND_REREVIEW`

Haofan / ChatGPT Pro found the four-arm causal design, replay coefficients,
budget, anchor algorithm, actual AdamW displacement diagnostic, persistence
nomination requirement and physics boundary substantively closed. It requested
no additional control, budget increase or stricter success threshold.

Three contract boundaries remained:

1. State explicitly that all four complete update directions receive exactly
   one global L2 clip at the frozen E008 limit 1.0. Replay already clips inside
   its merger; scalar and anchor arms require their own single explicit clip.
2. Define the growth/stagnant amplitude-ratio zero cases, propagate undefined
   ratios through `Q_damage`, and keep the primary spatial median on the fixed
   16-cycle support. Partial undefined correlations make that primary median
   `NA`, with the valid cycles reported separately.
3. Add `NO_REPAIR_SIGNAL` for valid/applicable results with no component gain,
   and operationalise component movement with a frozen numeric tolerance.

All three amendments are adopted in protocol v3. No implementation or training
was authorised by the round-2 result.
