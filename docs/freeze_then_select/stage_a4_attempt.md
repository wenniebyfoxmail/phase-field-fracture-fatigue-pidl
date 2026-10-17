# Stage A4 multi-environment identifiability attempt

Date: 2026-08-04

## Scope

Stage A4 tested whether an eight-environment balanced 2^3 traffic/cold/moisture
design could resolve the candidate-library collinearity that defeated Stage A3.
Each leave-one-section-out fold used six selection environments, one internal
validation environment, and one untouched forecast environment.

Mandatory controls were oracle frozen selection, pooled SVWS, pooled single-shot
STLSQ, an equal-row one-environment selector, cloned environments, all-term ridge,
true-support coefficient fitting, and fixed physics.

## Verification

- Full focused suite: 13 tests passed without warnings before the smoke.
- After replacing warning-prone BLAS products in the new A4 module with explicit
  finite sums, the four A4 tests passed.
- The exact predeclared seed-11 smoke was rerun with observation rate 0.20,
  noise sigma 0.01, 256 weak windows per environment, and 24 trials.
- Confirmation seeds were not opened and no PIDL/producer training was run.

## Result

- Raw designed forcing maximum correlation: 0.0283
- Balanced weak-library maximum correlation across folds: 0.9701 to 0.9982
- Effective rank: 10 of 10 in every fold
- Median condition number: 51.1
- Maximum environment leverage: 0.3837
- Shared support Jaccard: 0.5000
- Pooled SVWS support Jaccard: 0.5000
- Pooled single-shot support Jaccard: 0.4643
- Oracle shared-support Jaccard: 0.7083
- Shared support pairwise LOSO stability: 0.2500
- True-term frequencies: 0.625, 0.750, and 0.625
- Shared false-term maximum frequency: 0.250
- Median cutoff IoU at damage threshold 0.50: 1.000
- Final IoU at threshold 0.50: shared 0.8542, single-shot 0.8730, fixed 0.6125

The designed exogenous forcings were nearly orthogonal, but multiplication by
the common damage and active-energy envelopes recreated severe candidate
collinearity. Full matrix rank and moderate condition number were insufficient:
the oracle selector itself failed its support gate, and reconstructed shared
selection was unstable across held-out environments.

## Decision

Quarantine Stage A4. Do not run its 128-case development matrix and do not open
seeds 67, 79, 101, or 131. The positive forecast gain over fixed physics cannot
support a mechanism-selection or SVWS-superiority claim because all-term ridge
and single-shot forecasting were at least as competitive while support recovery
remained unstable.

The next intervention must change the physical candidate parameterization or
the information supplied to identification. More environmental rows, weighting,
or threshold tuning inside the current damage-weighted library is not justified.
