# Stage A3 Uncertainty-Aware Confirmation Protocol

This protocol is declared before any confirmation result exists.

## Evidence split

- Opened development seeds: `11, 23, 37, 51`.
- Sealed confirmation seeds: `67, 79, 101, 131`.
- Observation rates: `0.08, 0.20`.
- Noise levels: `0.01, 0.04`.
- Confirmation matrix: 16 cases with the same grid, cutoff, sections, candidate
  library, weak windows, support gates, and forecast gates as Stage A2.

The old Stage A2 matrices are development/quarantine evidence only. They cannot
confirm A3.

## A3 method fixed before confirmation

- Eight independently bootstrapped and noise-perturbed structured adapters.
- Weak systems computed separately for every frozen adapter.
- 128 uncertainty-aware selection replicates.
- Overall frequency at least 0.70, sign consistency at least 0.90, coefficient
  signal-to-uncertainty at least 2, and low-noise/tip frequency at least 0.50.
- Weak-row inverse uncertainty weights clipped to `[0.20, 5.0]`.
- Tip-window weight floor `0.50`; no uncertain tip row can be deleted.
- Existing independent validation-section 5% near-best minimal-support rule.
- Holdout sections and all external support/IoU/tip/event gates unchanged.

## Launch condition

Do not open confirmation seeds unless a smoke plus a four-case old-seed
development diagnostic shows that A3 support Jaccard exceeds both A2 SVWS and
single-shot without reducing tip weak-weight fraction below 0.10.

## Stop rule

If the sealed confirmation matrix fails once, do not tune thresholds on it.
Conclude that uncertainty-aware Freeze-Then-Select remains insufficiently
robust for sparse PDE term discovery in this synthetic setting.
