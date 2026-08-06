# ChatGPT Pro approval: LTPP enriched-input v3 amendment

Date: 2026-08-06

Conversation: `chatgpt-conversation://6a744792-7608-83eb-a541-46e5bd3043d7`

Decision: `APPROVE_V3_30_ROW_INPUT_FREEZE`

## Exact artifact approved

- v3 amendment:
  `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v3_amendment_candidate_20260806.md`
- amendment SHA-256:
  `f2490cd99b07912567ab52aabcf2ba9472b9514de3dd0fe1c1b1bba4e85ec70d`
- unchanged v2 base SHA-256:
  `3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`

The approved amendment is intentionally left byte-for-byte unchanged. This
receipt records the later approval without changing the reviewed artifact.

## Reviewer findings adopted

- The single named exclusion `06-2041-T01` is acceptable because it was
  triggered by the v2 source-time input rule before any enriched prior-
  predictive, posterior fit, or ablation score.
- The remaining 30 rows are fixed. No further row removal, traffic realignment,
  cross-construction ESAL borrowing, ESAL imputation, or rescue comparison is
  allowed.
- For 30 pooled predictions, 85%--95% coverage means exactly 26--28 covered.
- The endpoint, 11 features, source cutoff, model, priors, sampler, seeds,
  scaling, ablation order, and other success gates remain unchanged.
- The experiment must be reported as a separately reviewed complete-input
  sensitivity experiment after terminal v2 input failure, not as untouched v2.
- No replacement section is required; claims remain limited to these six
  sections and the named complete-input protocol.

## Authorization boundary

This approval authorizes only:

1. the fixed 30-row by 11-feature input freeze;
2. regenerated split and code/environment receipts;
3. hash and source-cutoff checks; and
4. the fixed prior-predictive preflight.

It does not authorize posterior fitting or ablation scoring. Those remain
blocked until every composite v2+v3 pre-fit gate passes.
