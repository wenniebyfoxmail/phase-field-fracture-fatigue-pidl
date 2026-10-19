# S09-E016 exact-commit implementation review request

Review the exact commit named in the submission against:

- `docs/research/S09/S09-E016/experiment.md`, protocol
  `v2-strict-zero-effective-increment`;
- `source/s09_e016_factorisation.py`;
- `scripts/analyse_s09_e016_factorisation.py`;
- `tests/test_s09_e016_factorisation.py`.

Check numerical correctness, zero-event behavior, saturation clipping versus
round-trip separation, `C_F/C_B/C_J` coverage, A25 scalar-only boundaries,
source identity locks, output completeness and the absence of hidden training,
model forwards or new holdout access.

Return exactly one top-line verdict:

- `E016_IMPLEMENTATION_READY_PASS`, or
- `E016_IMPLEMENTATION_REVISE` with concrete blocking findings.

The review must bind its verdict to the exact Git commit. It does not interpret
real-data results because the analysis has not yet been executed.
