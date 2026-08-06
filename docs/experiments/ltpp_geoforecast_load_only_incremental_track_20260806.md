# LTPP load-only incremental forecast track

Status: `INPUT_PREFLIGHT_PASS__FIT_AUTHORIZATION_REQUIRED__NO_FIT`

This is a new, deliberately narrow experiment. It does not reopen, retune, or
rescue the completed enriched-input track. No outcome fitting is authorized by
this document.

## Mechanism question

After conditioning only on the source crack state and forecast horizon, does
one source-available load-exposure variable provide stable incremental
predictive information about the next positive crack-length growth on unseen
LTPP sections?

This is an incremental-prediction question, not a causal claim about ESAL.

## Why this track exists

The previous experiment entered climate, traffic, structure, and FWD in a
sequential enriched model. Its negative result cannot identify whether the
failure came from a particular channel, feature compression, or the combined
small-sample design. This track isolates one channel so a failure or success is
interpretable.

## Candidate data and fixed comparison

The candidate row set starts from the qualified v3 30-transition set across the
same six sections, then applies one named input-only eligibility exclusion:
`06-1253-T07` is excluded because it crosses the 2011-06-01 Out-of-Study
terminal monitoring boundary. This is not evidence of maintenance and the
exclusion was chosen before any load-only outcome fitting. The proposed frozen
set is therefore 29 transitions, with 24 development transitions and 5 fixed
future-time transitions. No further row may be added, removed, imputed, or
requalified. If the load-only input audit finds a missing or invalid value, the
track returns to `BLOCKED_INPUT_COVERAGE__NO_FIT` and no rescue is tried.

Evidence and decision record:
`docs/experiments/ltpp_geoforecast_natural_episode_audit_20260806.md` and
`docs/experiments/ltpp_geoforecast_load_only_t07_exclusion_amendment_20260806.md`.
The completed enriched-input result is unchanged and is not retroactively
requalified.

Two models are proposed:

| model | predictors | purpose |
|---|---|---|
| G | `G1` source crack length, `G2` source crack area, `G3` forecast horizon | geometry-only baseline |
| G+L | G plus `T1` only | test one load channel |

Exact candidate definitions:

- `G1`: `source_geometry.crack_line_length_m` at source survey, `log1p`;
- `G2`: `source_geometry.crack_area_m2` at source survey, `log1p`;
- `G3`: `(target_date-source_date)/365.25` years, untransformed;
- `T1`: `TRF_TREND.ANNUAL_ESAL_TREND` for the latest complete calendar year
  strictly before the source survey year and the source-active
  `CONSTRUCTION_NO`, `log1p`.

`AADTT`, class-specific traffic, GESAL, GVW, future-year traffic, realized
interval traffic, climate, moisture, structure, FWD, interactions, splines,
polynomials, PCA, and feature selection are excluded.

## Proposed model and validation

Subject to external review, both models would use the same strong-regularized
hierarchical positive-growth model as the completed track. Only the predictor
matrix changes. The primary split would remain leave-one-section-out (LOSO),
with the existing fixed future-time split reported secondarily. Fold-local
standardization and all sampler settings would remain identical.

The endpoint would remain:

`Delta_L = max(0, target_crack_length - source_crack_length)`.

The proposed primary comparison is G+L versus G on pooled LOSO MAE. The
existing persistence result remains a contextual control, not a replacement
for the matched G versus G+L comparison.

## Frozen success rule

The Pro input-preflight review accepted the inherited engineering gate with the
29-row integer coverage conversion:

- at least 10% pooled MAE reduction;
- improvement in at least 4 of 6 held-out sections;
- 90% interval coverage of exactly 25--27 of 29 rows;
- CRPS worsening no greater than 5%.

If the matched G/G+L comparison fails, the load channel is reported as not
showing stable incremental predictive value in this panel. A passing result
would justify a separately preregistered replication or a predeclared second
factor; it would not establish causality.

## Completed outcome-free input preflight

The authorized input-only checks passed on 2026-08-06:

1. All 29 retained rows have valid G1--G3 and T1 under the exact source-year
   and construction join rule.
2. T1 is positive, finite, and non-constant within every section.
3. `06-1253-T07` is the only excluded transition; the fixed 29-row list and
   split receipt were generated once.
4. The row-level coverage/join receipt and split receipt are hashed.
5. The outcome-free manifest records that no outcome columns were present.

Receipt root:
`local_archive/real_road_acquisition/ltpp_geoforecast_load_only_input_preflight_v1_20260806/`

Hashes:

- feature table: `c332037d208baaa23c22288008dc629736f4822549bde6089f25fa6c175bd02e`;
- T1 join receipt: `eca8c035572524ee9a7aa797d8e2a0171c9e17897a7f4f28d529d9e62f7d4a44`;
- split receipt: `0303868dbd998e8650d72d22bfe95be6f5a0f62416363210ffc186e8823ed452`.

Any failure is fail-closed. No T1 imputation, construction substitution,
traffic realignment, row deletion, or alternate traffic variable is allowed.

## Minimal output and registry handoff

The minimum output is one input-audit receipt followed, only after Pro
authorization, by one matched G-versus-G+L result table and one decision note.
The result must be registered in this track and in `docs/research_frontier.md`;
it must not be folded into the closed enriched-input result as if it were the
same confirmatory experiment.

## Fit authorization state

ChatGPT Pro issued `APPROVE_LOAD_ONLY_INPUT_PREFLIGHT`, not fit
authorization. The next and only requested decision is
`APPROVE_LOAD_ONLY_POSTERIOR_FIT` for the frozen G versus G+L comparison.
Until that headline is issued, posterior fitting and ablation scoring remain
prohibited.
