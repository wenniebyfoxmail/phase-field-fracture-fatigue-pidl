# S09-E009 core code review round 1 — 2026-10-17

## Verdict

`REVISE_AND_REREVIEW`

Haofan ChatGPT Pro reviewed exact commit
`53b9bf9ab12c6fa3bc333b9287483735414ec3ba`. It independently reproduced the
43 selected tests and ran 57 additional contract tests. No optimiser step,
producer access, or real packet read occurred.

The normal finite path was found faithful for replay coefficients, four-arm
gradient geometry, atomic losses and equilibrium autograd, model/AdamW
isolation, layout, zero/NA rules, and decision precedence. Three core blockers
remain:

1. **F1 — nonfinite derived values do not always fail closed.** Finite but very
   large inputs can overflow a norm, dot, ratio, or `Q_damage`; examples returned
   zero, NaN, or Infinity instead of a numerical failure.
2. **F2 — some valid NumPy inputs are not strictly JSON serialisable.** AUC
   counts and fixed-support cycle IDs can remain NumPy scalar types.
3. **F3 — a nonzero projected residue can be labelled
   `FULLY_PROJECTED_TO_ZERO`.** The value is retained correctly, but a norm at or
   below epsilon is not identical to an exactly zero vector.

The reviewer did not treat the absent producer runner as a defect in this
core-only gate. It also noted that future runner integration must preserve
`g_D` from the same forward graph before `arm_direction()` consumes that graph.

## Required next action

Repair F1–F3 without changing the frozen formulas, budget, controls, or
thresholds; add synthetic/no-training counterexample tests; freeze a new exact
commit and rereview. Training remains unauthorised.
