# ChatGPT Pro final approval for LTPP enriched-input input freeze

Date: 2026-08-06  
Conversation: `chatgpt-conversation://6a744792-7608-83eb-a541-46e5bd3043d7`  
Decision: `APPROVE_FOR_INPUT_FREEZE`

## Exact artifact approved

- Path: `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`
- SHA-256: `3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`
- Confirmation request:
  `docs/reviews/ltpp_geoforecast_enriched_input_chatgpt_pro_confirmation_request_20260806.md`
- Confirmation-request SHA-256:
  `1dd2d711da3860c70caa84b50b84cb13bf323c769300826814d55cff362a2bbe`

The approved preregistration is intentionally left byte-for-byte unchanged.
This receipt records the later approval so that the exact artifact reviewed by
ChatGPT Pro retains its approved hash.

## Reviewer finding

ChatGPT Pro rechecked the post-revision candidate and found that the requested
minimum changes were implemented without changing the endpoint, feature set,
model family, split, success gate, or ablation order. The reviewer specifically
accepted the fixed `nu=4` rationale, positive-growth endpoint rationale,
engineering success-gate rationales, exact fail-closed prior-predictive check,
fold-local scaling rule, and small-sample claim boundary.

The two residual cautions were classified as reporting/data limitations rather
than preregistration defects:

1. the paper must describe the study as an evaluation of incremental
   information value, not as general validation of crack-evolution prediction;
2. the 31-transition sample size must be reported as a dataset limitation.

## Authorization boundary

This decision authorizes only:

1. acquisition of the frozen source-available fields;
2. deterministic construction of the 11-feature, 31-row input package;
3. provenance, source-cutoff, coverage, split, and hash checks; and
4. the preregistered prior-predictive preflight.

It does **not** authorize outcome fitting, posterior fitting, ablation scoring,
threshold changes, feature substitutions, or model-family changes. Fitting may
begin only after every immutable pre-fit gate in the approved preregistration
has passed and its receipt has been recorded.

Local adoption decision:
`APPROVE_INPUT_FREEZE_ONLY__BUILD_AND_HASH_31_ROW_INPUTS__NO_FIT`.
