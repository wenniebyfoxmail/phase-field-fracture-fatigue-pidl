# S09-E009 protocol v2 rereview request — 2026-10-16

Requested first-line verdict: `DESIGN_READY_PASS` or `REVISE_AND_REREVIEW`.

Please review `experiment.md` as the complete replacement protocol. Round-1
verdict and every requested amendment are in `design_review_round1_20261016.md`.

The revision adopts:

- four arms `R/S/A0/A25`, with `A0` as the matched beta-zero control;
- a narrowed mechanism question and restricted comparison meanings;
- exact replay coefficients and a numeric replay tolerance;
- 500 fixed final updates plus non-selective update-496 evaluation, with a
  2,000-update total cap;
- byte-identical initial model parameters/buffers and separate empty AdamW
  states;
- pre-projection norm equalisation, no post-projection renormalisation, and
  distinct zero auxiliary / anchor-stationary / execution-failure policies;
- explicit actual-parameter-displacement alignment and no AdamW no-harm claim;
- graded outcomes, persistence-baseline sanity check, zero-denominator rules,
  AUC tie accounting and a separate spatial-template label;
- corrected physics wording: predicted `u_peak` and predicted `d_peak` jointly
  enter the AMOR equilibrium residual, with no damage stationarity or fatigue
  evolution residual.

Please determine whether all round-1 blockers are now closed and whether the
protocol is specific enough for implementation without scientific choices by
the implementer. Do not run training. A PASS authorises only local
implementation, synthetic/no-training testing and a later exact-commit Code
Ready review.
