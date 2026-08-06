# ChatGPT Pro authorization: LTPP enriched-input posterior fit

Date: 2026-08-06

Conversation: `https://chatgpt.com/c/6a744792-7608-83eb-a541-46e5bd3043d7`

Decision: `AUTHORIZE_FROZEN_POSTERIOR_FIT`

## Findings adopted

- Composite v2+v3+v4 pre-fit gates were executed as approved: the 30x11 input
  freeze, fixed LOSO and 24+6 split, amendment/approval hashes, and all 28
  outcome-free prior-predictive checks passed.
- The frozen frequency gate was at most 1% of row-level draws above
  `100.189733 m`; the observed range was `0.0000`--`0.0040`.
- Rare extreme maximum draws remain disclosed but do not create a new
  retrospective maximum-based gate.
- No feature, row, split, prior, likelihood, sampler, seed, metric, threshold,
  ablation order, or claim-boundary change is authorized.

## Authorization boundary

This authorization covers only:

1. the frozen posterior fit;
2. sealed LOSO and future-time evaluation; and
3. preregistered ablation scoring, followed by the predeclared non-confirmatory
   oracle diagnostic after primary M0--M3 outputs are sealed.

It does not authorize exploratory model switching, architecture rescue,
threshold resetting, selective reporting, or claim expansion.
