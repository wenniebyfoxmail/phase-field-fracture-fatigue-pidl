# Stage A5 active-measure normalization attempt

Date: 2026-08-04

## Scope

Oracle-only diagnostic of a support-preserving weak-row transformation. Each
weak equation recorded the common active measure `integral(w d psi_plus)` and
divided both its response and every candidate by the same floored positive
quantity. No rows or candidate columns were removed, and raw and normalized
selectors used identical windows, splits, thresholds, and random seeds.

Independent methods review was unavailable. The protocol therefore prohibited
advancement beyond this oracle diagnostic even if it passed.

## Verification

- Fourteen focused tests passed without warnings.
- The fixed seed-11, eight-environment, 256-window, 24-trial oracle smoke ran.
- No reconstructed field, forecast, producer, joint-training baseline, or
  confirmation seed was used.

## Result

- Raw median oracle support Jaccard: 0.7083
- Normalized median oracle support Jaccard: 0.2429
- Normalized exact-support fraction: 0.1250
- Normalized pairwise LOSO support stability: 0.2500
- Normalized true-term frequencies: 0.500, 0.625, and 0.250
- Normalized maximum false-term frequency: 0.625
- Normalized maximum candidate correlation: 0.9986
- Weak-row count preservation: true

The transformation preserved the exact equation algebraically but changed the
statistical weighting of noisy/approximate weak equations. It amplified low
active-measure windows and worsened both support accuracy and stability without
reducing the dominant candidate correlation.

## Decision

Quarantine Stage A5. Do not alter the active-measure floor or rerun. Do not
advance this normalization into reconstructed-field, forecast, producer, or
confirmation experiments.

Combined with Stages A2-A4, this rejects further threshold, weighting, row-count,
and shared-envelope normalization work on the current ten-term library. The next
scientifically useful action is an explicit support-equivalence/identifiability
audit and a producer-data availability audit, not another selector variant.
