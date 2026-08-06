# ChatGPT Pro review: LTPP enriched-input preregistration v2

Date: 2026-08-06  
Conversation: `chatgpt-conversation://6a744792-7608-83eb-a541-46e5bd3043d7`  
Reviewed preregistration SHA-256:
`92b1f5081bc9db9d2911d72cdce59369941a959bfc11bfb9aa3ee8713e0a7fc8`  
Reviewer status: `REVISE_BEFORE_INPUT_FREEZE`

## Reviewer assessment

The reviewer judged the design approximately 90--95% frozen and close to a
Registered Report Stage-1 preregistration. The source-only primary task, oracle
demotion, exact feature table, unique FWD definition, scalar output boundary,
LOSO/future-time axes, fail-closed missingness, and non-causal claim boundary
were adopted. No new research direction or algorithm was requested.

## Minimum revisions requested

1. Explain why Student-t degrees of freedom are fixed at `nu=4`.
2. Explain why a 10% MAE improvement is the practical-success threshold.
3. Explain why improvement is required on four of six held-out sections.
4. Explain why CRPS may worsen by no more than 5%.
5. Explain why positive rather than signed crack growth is confirmatory.
6. Add a 500-sample prior-predictive check with no post-check prior tuning.
7. Restate that units remain unchanged and only fold-local z-scoring is used.
8. Frame the contribution as evaluating information value, not claiming a
   generally validated predictive model from 31 transitions.

## Local decision

All requests are adopted. The reviewer suggested a qualitative “physically
plausible magnitude” prior check; locally this is made more restrictive and
reproducible by fixing the draw count, seeds, reported quantities, source-only
benchmark ceiling, 1% exceedance gate, and a fail-closed external re-review path.
The prior check cannot be used to tune priors after outcomes are fitted.

No endpoint, feature, model family, split, or result threshold was changed. The
revised preregistration remains `NO_FIT_AUTHORIZED` until the immutable input
and prior-predictive gates pass.
