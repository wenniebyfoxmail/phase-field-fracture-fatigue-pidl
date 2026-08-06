# LTPP enriched-input preregistration v3 amendment candidate

Date: 2026-08-06

Status: `CANDIDATE_FOR_EXTERNAL_REVIEW__NO_FEATURE_REFREEZE__NO_FIT`

## Composite protocol

This amendment is interpreted only together with the exact approved v2 file:

- base: `ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`;
- base SHA-256:
  `3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`.

Every v2 clause remains binding except the explicit overrides below. This
amendment does not authorize fitting and is not adopted until external review.

## Reason for amendment

V2 reached its predeclared `BLOCKED_INPUT_COVERAGE` state before
prior-predictive checking or outcome fitting. The exact missing join is:

`06-2041-T01 -> TRF_TREND(CONSTRUCTION_NO=3, YEAR=1995)`.

The exclusion below is based solely on an absent source-time input required by
v2. No enriched-input model, prior-predictive result, ablation score, or
alternative traffic rule has been evaluated. The transition outcome did exist
in the earlier geometry benchmark; therefore external review must explicitly
judge the remaining post-observation selection risk.

## Override 1: fixed qualified row set

The confirmatory row set is fixed to the original 31 transition IDs minus only
`06-2041-T01`:

- 30 transitions across the same six sections;
- 24 development transitions;
- six frozen future-time transitions;
- no other row may be removed for missingness, sampler behavior, leverage, or
  result.

This is a fixed named exclusion, not a general complete-case algorithm that can
remove additional rows. If any of the remaining 30 rows lacks any required
feature, v3 returns `BLOCKED_INPUT_COVERAGE`.

## Override 2: split receipts

LOSO remains the primary axis with the same six held-out sections. The
`06-2041` held-out fold contains its six remaining transitions; other held-out
folds are unchanged. Every training fold excludes `06-2041-T01`.

The future-time axis trains on the 24 remaining development transitions and
tests on the same six frozen final-time transitions. A new split receipt must
be generated and hashed before feature fitting. Random or transition-level
splits remain prohibited.

## Override 3: row-dependent gates

All point and probabilistic thresholds remain unchanged. For 30 pooled LOSO
predictions, nominal-90% coverage must be from 85% through 95%, which means
exactly 26--28 covered observations.

The section-wise majority remains at least four of six sections. The 10% MAE
gain and no-more-than-5% CRPS worsening rules remain unchanged.

The source-only prior-predictive ceiling remains
`100.189733 m` because excluding `06-2041-T01` does not change the maximum
source crack length. Seeds and the 1% exceedance gate remain unchanged.

## Override 4: matched comparison set

Persistence, M0, M1, M2, and M3 must all be evaluated on the identical named
30-row set. The original 31-row results cannot be mixed with v3 metrics. Any
baseline or split-derived receipt must be regenerated for the fixed 30 rows and
linked back to the original immutable transition manifest.

The O3 diagnostic remains non-confirmatory and is rebuilt only after primary
outputs are sealed. Its realized-traffic set is fixed to 29 rows: the original
30-row O3 set minus `06-2041-T01`. It cannot rescue v3.

## Override 5: claim wording

If approved and executed, v3 must be described as a separately reviewed
complete-input sensitivity experiment following a terminal v2 input failure.
It must not be presented as the untouched v2 confirmatory run. The paper must
disclose that the removed transition outcome existed in an earlier benchmark,
while no enriched model had been fitted when the input-only exclusion was
proposed.

## Unchanged clauses

The endpoint, 11 feature definitions, source cutoff, transforms, Bayesian
Student-t model, priors, sampler, fold-local scaling, unseen-section random
effect, ablation order, oracle boundary, 10%/four-of-six/CRPS gates,
prohibitions, and noncausal claim boundary remain exactly as in v2.

## External-review decision required

The reviewer must return exactly one status:

- `APPROVE_V3_30_ROW_INPUT_FREEZE`;
- `REVISE_V3_BEFORE_INPUT_FREEZE`; or
- `REJECT_V3_CONFIRMATORY_RESCUE`.

Approval authorizes only creation and hashing of the named 30x11 table, new
split receipt, code/environment receipt, and prior-predictive preflight. It
does not authorize outcome fitting until all composite v2+v3 gates pass.
