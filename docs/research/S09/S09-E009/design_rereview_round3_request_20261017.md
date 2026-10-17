# S09-E009 protocol v3 narrow rereview request — 2026-10-17

Requested first-line verdict: `DESIGN_READY_PASS` or `REVISE_AND_REREVIEW`.

Please review `experiment.md` only for the three round-2 contract-completion
items recorded in `design_review_round2_20261017.md`:

1. exactly one frozen global L2 clip (limit 1.0) for every arm, with no replay
   double clip, per-objective clip or extra averaging;
2. deterministic amplitude-ratio zero cases, undefined-`Q_damage` propagation,
   and fixed-support spatial-correlation NA handling;
3. a `NO_REPAIR_SIGNAL` branch, frozen component-movement tolerance, explicit
   precedence and diagnostic-only status for `S/A0`.

Please determine whether v3 now removes remaining scientific choices from the
implementation contract. Do not run training. A PASS authorises only local
implementation, synthetic/no-training tests and a later exact-commit Code Ready
review.
