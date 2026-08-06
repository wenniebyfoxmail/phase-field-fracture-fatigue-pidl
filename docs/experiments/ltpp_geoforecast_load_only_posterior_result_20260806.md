# LTPP load-only incremental posterior result

Date: 2026-08-06
Status: `PRIMARY_NEGATIVE__LOAD_ONLY_COMPLETE`

## Question and authorization

This separately reviewed sensitivity track asked whether one source-available
load variable adds predictive value beyond source geometry and forecast
horizon. ChatGPT Pro authorized exactly the frozen 29-row G-versus-G+L fit,
LOSO primary evaluation, and fixed 24-development + 5-future-time secondary
evaluation. No other feature, row, alignment, threshold, or model search was
authorized.

## Frozen comparison

- `G`: G1 source crack length + G2 source crack area + G3 forecast horizon;
- `G+L`: G plus T1 `TRF_TREND.ANNUAL_ESAL_TREND` from the latest complete
  pre-source calendar year under source-active construction;
- endpoint: `max(0, target crack length - source crack length)`;
- primary split: LOSO across six sections;
- secondary split: 24 development + 5 future-time rows;
- coverage gate: exactly 25--27 of 29 rows;
- all other traffic, climate, moisture, structure, FWD, interactions, and
  feature selection were excluded.

## Primary LOSO result

| model | MAE (m) | RMSE (m) | mean CRPS (m) | 90% covered |
|---|---:|---:|---:|---:|
| persistence B0 | 4.3864 | 8.0868 | 4.3864 | 14/29 |
| G | 4.4832 | 7.6080 | 394870.3493 | 25/29 |
| G+L | 4.5001 | 7.6334 | 6.5541 | 25/29 |

### Claim-bearing contrast: G+L versus G

- pooled MAE reduction: **-0.376%**;
- improved sections: **2/6**;
- coverage: **25/29**, gate pass;
- CRPS change: **-99.998%**, gate pass because G's frozen posterior had
  extreme tail draws;
- overall gate: **fail**.

The section-bootstrap mean MAE difference (G+L minus G) was `+0.0169 m`, with
descriptive 95% interval `[-0.0218, +0.0627] m` (10,000 draws, seed 260806).
This interval is descriptive and does not replace the preregistered gate.

## Future-time result

| model | MAE (m) | RMSE (m) | mean CRPS (m) | 90% covered |
|---|---:|---:|---:|---:|
| persistence B0 | 6.1378 | 9.8868 | 6.1378 | 3/5 |
| G | 6.2449 | 9.2072 | 1.2627e16 | 4/5 |
| G+L | 6.2541 | 9.2044 | 706.4939 | 4/5 |

This secondary split also shows a small deterioration after adding T1. It is
descriptive and not a second success criterion.

## Sampler validity

All 14 posterior fits passed final diagnostics. Three used the one permitted
retry; no final fit failed. Worst final R-hat was `1.00264`, minimum bulk ESS
`2749.41`, minimum tail ESS `3065.21`, and final divergences were zero. The run
was computationally valid; the scientific gate failed.

The extreme CRPS values are reported unchanged. They reflect the frozen
heavy-tailed posterior predictive behavior and are not repaired after seeing
the outcome. No clipping, prior change, likelihood change, or rescue was done.

## Interpretation

Supported conclusion:

> In this six-section, 29-transition sensitivity protocol, the single annual
> ESAL channel did not provide stable incremental predictive value beyond
> source geometry and forecast horizon under unseen-section validation.

Not supported:

- ESAL or traffic loading is physically irrelevant;
- traffic has no causal effect on cracking;
- other load representations cannot help;
- the result generalizes beyond this panel;
- a more complex architecture would necessarily solve the problem.

This track should be closed as a valid negative single-channel experiment.
Do not add AADTT, climate, moisture, structure, FWD, interactions, or a new
architecture as a post-hoc rescue. A larger independent panel or a spatial
crack-growth target would require a new preregistered track.

## Receipts

- Pro fit authorization: `docs/reviews/ltpp_geoforecast_load_only_chatgpt_pro_fit_authorization_20260806.md`, SHA-256 `fddf3fbbde85c0b955db6b60080a8804abdf4f0a7bc60d2186c6571f99f16601`;
- input manifest: local archive `ltpp_geoforecast_load_only_input_preflight_v1_20260806/load_only_input_manifest.json`;
- feature table SHA-256: `c332037d208baaa23c22288008dc629736f4822549bde6089f25fa6c175bd02e`;
- T1 join receipt SHA-256: `eca8c035572524ee9a7aa797d8e2a0171c9e17897a7f4f28d529d9e62f7d4a44`;
- split receipt SHA-256: `0303868dbd998e8650d72d22bfe95be6f5a0f62416363210ffc186e8823ed452`;
- sealed evaluation SHA-256: `c0f0d2006661b514e332c3446fa8257f536d69010006fd8e8dd2998cb7d4ba03`;
- sealed predictions SHA-256: `3564544b0096f4de660c37dcc33a2df65f4a60799efc71333fe3e2aa4d186f2b`;
- sampler diagnostics SHA-256: `cdbba490c39ae047c348df6f48be767ecb1d1f746dae53a32d026b35d71a4c8c`;
- posterior runner SHA-256: `1b071c0bf2ed1fc3043e837ee99b4ee3d0eb14f7303ce7eedf83514e26413d43`;
- raw posterior archive: `local_archive/real_road_acquisition/ltpp_geoforecast_load_only_posterior_v1_20260806/`.
