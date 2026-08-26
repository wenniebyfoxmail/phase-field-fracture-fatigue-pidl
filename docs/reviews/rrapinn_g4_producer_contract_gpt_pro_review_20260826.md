# GPT Pro planning review — RRaPINN G4 producer contract

Source conversation: `6a8ebdd2-17f4-83eb-b230-8a32f50022a0`

Review verdict: `REVISE`

The review identified three planning blockers:

1. Freeze whether alpha enforcement is export-only qualification or a
   model/state transformation.
2. If the model changes, define restart scientific-state equivalence and the
   branch between `REQUALIFIED_SAME_STATE` and
   `NEW_STATE_REQUIRES_NEW_CANDIDATE`.
3. Make the bounded observer smoke purely infrastructural and non-decisional;
   its scientific outputs cannot drive tuning, selection, or promotion.

## Adopted minimal resolution

- Alpha enforcement is `export_admissibility_only`. The historical
  `NonsmoothSigmoid` decoder, training loss and state evolution are unchanged.
  Out-of-range alpha causes a producer FAIL receipt; values are never clipped or
  repaired by this contract.
- Because the model/state transition is unchanged, the bounded-alpha restart
  requalification branch is deleted. The v4 lock binds the existing canonical
  restart manifest SHA and the existing exact A-replay sentinel remains the
  state-continuity check.
- Observer-smoke scientific outputs are non-decisional. Smoke PASS means only
  `PRODUCER_INFRASTRUCTURE_QUALIFIED`; it cannot tune a model, promote a
  candidate, rehabilitate ME85, or authorize G5.
- The historical G4 timing result remains `FAIL_NO_PROMOTION`: FEM c83,
  A c89, B right-censored through c92. Future producer repairs do not rewrite
  that result.

These resolutions remove the three blockers without introducing a new model,
restart branch, or scientific candidate.
