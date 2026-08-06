# ChatGPT Pro review request: LTPP load-only incremental track

Please review:

`docs/experiments/ltpp_geoforecast_load_only_incremental_track_20260806.md`

This is a candidate for a new, narrow LTPP experiment after the completed
enriched-input track produced a valid negative result. Do not authorize a fit
unless the protocol is sufficiently specified.

Please answer:

1. Is the G versus G+L comparison scientifically interpretable as a one-channel
   incremental-prediction test?
2. Is the fixed 29-row, six-section set acceptable after the single pre-fit
   exclusion of `06-1253-T07` for crossing the 2011-06-01 Out-of-Study terminal
   boundary, or must it be treated only as an exploratory sensitivity analysis?
3. Are G1 source length, G2 source area, and G3 horizon the correct minimal
   baseline for isolating load?
4. Is `TRF_TREND.ANNUAL_ESAL_TREND` with latest complete pre-source year and
   source-active construction the correct single load feature?
5. Are the proposed LOSO, 24-development + 5-future-time split,
   positive-growth endpoint, model family, and 25--27 coverage gate for 29 rows
   acceptable?
6. Is the input-only preflight sufficient, and what additional fail-closed
   check is minimally required?

Classify each issue as Critical, Major, or Minor. If approved, return the exact
headline `APPROVE_LOAD_ONLY_INPUT_PREFLIGHT` or
`APPROVE_LOAD_ONLY_POSTERIOR_FIT` and state precisely what is authorized. If
not approved, give only the minimum changes; do not propose a multi-factor
model or an architecture search.
