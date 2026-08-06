# LTPP load-only incremental forecast track

Status: `DRAFT__PRO_REVIEW_REQUIRED__NO_FIT`

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

The candidate row set is the already qualified v3 30-transition set across the
same six sections. No row may be added, removed, imputed, or requalified for
this proposal. If the load-only input audit finds a missing or invalid value,
the track returns to `BLOCKED_INPUT_COVERAGE__NO_FIT` and no rescue is tried.

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

## Proposed success rule (not yet frozen)

For Pro review, the candidate retains the previous engineering gate:

- at least 10% pooled MAE reduction;
- improvement in at least 4 of 6 held-out sections;
- 90% interval coverage of exactly 26--28 of 30 rows;
- CRPS worsening no greater than 5%.

If the matched G/G+L comparison fails, the load channel is reported as not
showing stable incremental predictive value in this panel. A passing result
would justify a separately preregistered replication or a predeclared second
factor; it would not establish causality.

## Cheaper preflight before any fit

The following input-only checks must pass first:

1. Verify all 30 rows have valid G1--G3 and T1 under the exact source-year and
   construction join rule.
2. Verify T1 is positive, finite, and not constant in any LOSO training fold.
3. Produce a row-level coverage/join receipt and hash it.
4. Verify the runner, environment lock, and split receipt without reading the
   outcome field.

Any failure is fail-closed. No T1 imputation, construction substitution,
traffic realignment, row deletion, or alternate traffic variable is allowed.

## Minimal output and registry handoff

The minimum output is one input-audit receipt followed, only after Pro
authorization, by one matched G-versus-G+L result table and one decision note.
The result must be registered in this track and in `docs/research_frontier.md`;
it must not be folded into the closed enriched-input result as if it were the
same confirmatory experiment.

## Open review questions

This document is a candidate protocol, not a frozen preregistration. ChatGPT
Pro review is required for:

- whether the 30-row reuse is acceptable for this sensitivity track;
- whether G1--G3 are the correct minimal baseline;
- whether T1 alone is the right load representation;
- whether the inherited success gate is appropriate;
- whether any input audit can proceed before outcome access.

Until those questions are answered, status remains
`DRAFT__PRO_REVIEW_REQUIRED__NO_FIT`.
