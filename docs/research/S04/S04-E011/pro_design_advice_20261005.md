# External design review — S04-E011

Source conversation: `https://chatgpt.com/c/6ac2e1ce-9940-83ed-a562-b17182126205`

Verdict: **DESIGN PASS for discretisation x complete-algorithm; not a pure
solver-factor experiment.**

Adopted:

- Native T3 order-2 GP3 in the fixed barycentric order, with all three
  Carrara channels stored per GP as `[172816,3]`.
- One shared pre-recovery c0 PIDL state and zero native fatigue histories;
  independent pretraining or nonzero Q4-to-T3 history projection is forbidden.
- Within each algorithm row, Q4/T3 share tolerances, budgets, state timing,
  acceptance and stopping logic.  FEM/PIDL algorithmic differences remain
  disclosed factors.
- Common pre-event cycles are primary; own-event fields are secondary.
- Difference-in-differences is descriptive for this seed/case, not a
  population inference.
- A stationarity-failing FEM endpoint limits conclusions to archived-algorithm
  disagreement and topology sensitivity.
- Canonical FEM-Q4 need not be rerun only if every equation/state/stopping
  parameter and the new event evaluation are proved compatible.

Modified locally:

- The review proposed a new connectivity event only because it believed the
  old detector lacked an executable definition.  The sealed handoff contains
  a source-verified existing detector (`x>0.48`, `d>0.95`, at least 3 nodes,
  3-cycle confirmation), so E011 retains that already frozen rule.
- The review left PIDL stopping expression and FEM penalty/stopping values as
  blockers.  Source evidence resolves them in `experiment.md`.
- We choose to rerun FEM-Q4 anyway, because the user authorised a joint rerun
  and full substep output from one driver gives a stricter paired lineage.

Rejected:

- Calling the 2x2 a network-capacity isolation.
- Reusing the old PIDL-Q4 trajectory as the strict paired arm.
- T3 centroid energy with only a GP3 irreversibility term.
- Comparing raw Q4 and T3 GP array indices or choosing cycles after seeing the
  event results.
- Changing budget, seed, eta, diagonal, event threshold or optimizer after a
  failed or distant result.
