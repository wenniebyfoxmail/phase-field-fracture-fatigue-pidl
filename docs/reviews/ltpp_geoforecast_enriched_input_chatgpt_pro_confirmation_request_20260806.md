# ChatGPT Pro confirmation request after minimum revisions

Please recheck only whether the requested minimum revisions have been applied to:

`docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`

Reviewed pre-revision SHA-256:
`92b1f5081bc9db9d2911d72cdce59369941a959bfc11bfb9aa3ee8713e0a7fc8`

Post-revision candidate SHA-256:
`3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`

The candidate now:

1. fixes and explains `nu=4` as an a-priori finite-variance heavy-tail
   robustness choice;
2. explains 10% MAE as the minimum practically meaningful engineering gain;
3. explains four of six as a strict simple majority of unseen sections;
4. explains the 5% CRPS tolerance as protection against material degradation in
   probabilistic accuracy and sharpness;
5. explains why remaining negative signed changes are not treated as physical
   healing and fixes the non-negative inverse predictive transform;
6. adds an exact 500-draw prior-predictive protocol, deterministic seeds,
   reported quantities, a source-only benchmark ceiling, a 1% exceedance gate,
   and fail-closed external re-review rather than prior tuning;
7. reiterates unchanged units and fold-local-only z-scoring;
8. frames the contribution as evaluating information value rather than claiming
   a generally validated predictive model from 31 transitions.

No endpoint, feature, model family, split, ablation order, or result threshold
was changed.

Please return exactly one design status with a short reason:

- `APPROVE_FOR_INPUT_FREEZE`;
- `REVISE_BEFORE_INPUT_FREEZE`; or
- `REJECT_EXPERIMENT_DESIGN`.

`APPROVE_FOR_INPUT_FREEZE` authorizes only acquisition and hashing of the
31-row feature package. It does not authorize outcome fitting; all immutable
input, code, prior-predictive, and no-fit gates must still pass first.
