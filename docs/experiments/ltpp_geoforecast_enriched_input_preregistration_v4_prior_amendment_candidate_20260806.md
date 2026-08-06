# LTPP enriched-input v4 prior-calibration amendment candidate

Status: `CANDIDATE__EXTERNAL_REVIEW_REQUIRED__NO_FIT`

Date: 2026-08-06

## 1. Composite protocol and disclosure

The v2 preregistration and approved v3 30-row amendment remain in force except
for the four prior-scale overrides in Section 4 below. This candidate was
written after inspection of the v3 prior-predictive failure, but before any
outcome likelihood, posterior fit, held-out enriched prediction, or ablation
score. It is therefore a separately reviewed post-gate sensitivity amendment,
not an untouched confirmatory continuation.

The inspected v3 result must remain public:

- all 28 original model/design prior checks failed;
- above-cap fractions ranged from `0.0820` to `0.2780` against a `0.01` gate;
- no outcome fields were read and no fit was performed;
- report SHA-256:
  `6c615869b1ba6ffc21ce2001825c00e05a9b2d65b1b6a42fb45df5f7317d8049`.

## 2. Immutable inputs and design

The following remain byte-for-byte or semantically unchanged:

- the fixed 30 transition IDs and sole exclusion `06-2041-T01`;
- the frozen 30x11 feature table, SHA-256
  `c0443e1c8f66f0c9bb0f3f45af26cf75fd4366ec70f4ccc3a1e87242ddc99a4d`;
- the LOSO folds and 24+6 future-time split, receipt SHA-256
  `1cb574e0d9e7cb2976f043ad5c83b718c017bff9dff508f1798b603aac4e4a2b`;
- endpoint, transforms, fold-local scaling, zero-variance rule, likelihood,
  hierarchical section effect, unseen-section prediction rule, sampler,
  feature blocks, ablation order, success criteria, and oracle boundary;
- `nu=4`, 500 prior draws, seed map, `100.189733 m` cap, and the requirement
  that every model/fold have at most 1% row-level draws above the cap.

No row, feature, split, cap, threshold, likelihood, or validation metric may be
changed under this amendment.

## 3. Outcome-free calibration basis

All predictors are already transformed and standardized within each training
fold. An outcome-free audit of the frozen input design found that the maximum
Euclidean norm of any evaluation-row predictor vector is `6.818724792015804`
(M3, LOSO holdout `06-2041`, transition `06-2041-T06`). The physical ceiling on
the model scale is `log1p(100.189733) = 4.616997299137536`.

These two frozen-input quantities are disclosed as the basis for selecting one
strongly regularized candidate. No alternative prior sets were simulated,
ranked, or compared before external review.

## 4. Only allowed override: fixed prior scales

Replace the v2 priors

```text
alpha ~ Normal(0, 2.5)
beta_j ~ Normal(0, 1)
sigma ~ HalfNormal(1)
sigma_s ~ HalfNormal(1)
```

with exactly:

```text
alpha ~ Normal(0, 1)
beta_j ~ Normal(0, 0.1)
sigma ~ HalfNormal(0.5)
sigma_s ~ HalfNormal(0.5)
```

The same priors apply to M0--M3 and every fold. They are not tuned by fold,
model, feature group, or observed outcome.

Interpretation on the model scale:

- `alpha` puts 95% of its marginal mass approximately within `[-1.96, 1.96]`;
- one standardized predictor unit changes the linear predictor by SD `0.1`,
  corresponding to a multiplicative factor `exp(0.1) = 1.1052` before the
  non-negative clamp;
- at the worst frozen predictor norm, the coefficient block has marginal SD
  at most `0.6819`;
- the two HalfNormal scales retain section and residual heterogeneity while
  reducing the scale explosion exposed by the original check.

These are regularizing plausibility priors for a 30-row experiment. They are
not estimates of predictive performance or physical causality.

## 5. One-run rule and decision

If externally approved, run the unchanged prior-predictive program exactly once
with the four scales above and the existing deterministic seeds.

- If all 28 checks pass, seal the new report and request a separate explicit
  fit authorization. Passing this amendment alone does not start posterior
  fitting.
- If any check fails, return
  `V4_PRIOR_PREDICTIVE_FAILED__TRACK_BLOCKED__NO_FIT`. Do not test a second prior
  set, relax the cap, change the likelihood, or fit outcomes.

The claim remains limited to whether source-available input blocks have
incremental predictive information in this fixed six-section, 30-transition
sensitivity protocol. No causal, spatial-geometry, or general deployment claim
is authorized.
