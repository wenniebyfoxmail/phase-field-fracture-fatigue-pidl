# ChatGPT Pro approval: LTPP enriched-input v4 prior amendment

Date: 2026-08-06

Conversation: `chatgpt-conversation://6a744792-7608-83eb-a541-46e5bd3043d7`

Decision: `APPROVE_V4_PRIOR_PREFLIGHT_ONLY`

## Exact artifact approved

- v4 prior amendment:
  `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v4_prior_amendment_candidate_20260806.md`
- amendment SHA-256:
  `d8fa9840581b1aa0ad9a19a11bd892fdf3ac6d5325ecacb1454f2c9a7f955565`

The reviewed amendment remains byte-for-byte unchanged. This receipt records
the later approval without modifying that artifact.

## Reviewer findings adopted

- One transparent, externally reviewed prior amendment is admissible because
  the v3 failure occurred before any outcome likelihood, posterior fit,
  held-out enriched prediction, or ablation score.
- The four fixed replacement scales are sufficiently justified for one
  controlled preflight: `Normal(0,1)`, `Normal(0,0.1)`, `HalfNormal(0.5)`, and
  `HalfNormal(0.5)`.
- Applying the same replacement priors to all M0--M3 models and folds preserves
  matched comparisons.
- The one-run terminal rule closes iterative prior tuning.
- No additional design change is authorized or required.

## Authorization boundary

This approval authorizes exactly one amended prior-predictive preflight using:

- the frozen 30x11 table and existing split receipt;
- the four replacement prior scales above;
- 500 draws and the existing deterministic seeds;
- the unchanged `100.189733 m` cap and at-most-1% gate.

It does not authorize posterior fitting, held-out enriched prediction, ablation
scoring, a second prior set, threshold relaxation, or any row/feature/split/
likelihood change.
