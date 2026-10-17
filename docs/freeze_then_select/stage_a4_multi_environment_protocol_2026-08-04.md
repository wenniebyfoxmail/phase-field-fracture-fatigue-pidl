# Stage A4 predeclared multi-environment identifiability protocol

Date frozen: 2026-08-04

## Purpose

Stage A3 showed that residual-uncertainty weighting preserved crack-tip weak
evidence but did not improve mechanism support. Stage A4 therefore changes the
identifiability intervention rather than retuning thresholds: independently
excited synthetic road sections must identify one invariant correction support.

This remains a synthetic, tooling-only development experiment. It cannot prove
a road mechanism, PIDL benefit, or causal environmental effect.

## Data and leakage boundary

- Use the existing equation-linked synthetic damage generator and candidate
  library without changing the true support.
- Generate eight environments per replicate from a balanced 2^3 traffic/cold/
  moisture excitation design. Add deterministic, mutually distinct temporal
  phases without changing each environment's declared factor level.
- Keep the true correction support invariant. Environment amplitudes may change,
  but no candidate coefficient sign may change.
- Fit every structured adapter only to sparse observations at or before the
  forecast cutoff. Freeze and hash each adapter before weak-system assembly.
- Never use future damage, oracle derivatives, true coefficients, or the held-out
  section response during selection.
- In every leave-one-section-out fold, one environment is the unseen test
  section, one of the remaining environments is a deterministic internal
  validation section, and the other six form the selection pool.
- Require pairwise correlation at most 0.35 among raw designed traffic, cold,
  and moisture forcing over section-time samples before damage generation.

## Row-matched comparisons

All selectors receive exactly the same frozen weak rows and candidate scaling:

1. multi-environment invariant shared-support selection;
2. pooled frequency-only SVWS;
3. pooled single-shot sparse selection.

Report a fourth diagnostic in which the invariant selector receives a
row-matched resample from only one environment. This control tests whether any
gain comes from excitation diversity rather than merely additional rows.

Also report a cloned-environment control, an oracle-frozen multi-environment
ceiling, an all-term ridge forecast, and a true-support coefficient-fit ceiling.

The fixed-physics forecast remains the no-correction forecast baseline. Joint
neural training remains deferred until a producer snapshot exists and must not
be represented by the pooled single-shot selector.

## Shared-support selection

- Standardize candidate columns within each environment, preserving stored
  scales for coefficient recovery.
- Fit coefficients per environment while imposing a common candidate support.
- Score each candidate by cross-environment inclusion frequency, sign
  consistency, robust coefficient SNR, and leave-one-environment-out residual
  improvement.
- Candidate acceptance requires inclusion frequency at least 0.75, sign
  consistency at least 0.90, robust SNR at least 2.0, and positive residual
  improvement in at least three of four training environments.
- Among accepted supports within 5% of the best held-out-environment residual,
  choose the smallest support. Ties use the lower maximum environment residual.
- Crack-tip rows retain a minimum total weak weight fraction of 0.10.

## Identifiability diagnostics

Before interpreting support recovery, record:

- maximum absolute off-diagonal candidate correlation per environment and after
  multi-environment stacking;
- standardized library condition number per environment and after stacking;
- effective rank at relative singular-value tolerance 1e-8;
- whether stacked correlation or conditioning improves over the median
  single-environment value.
- maximum environment leverage share under equal-environment weighting.

No reliability claim is allowed unless balanced stacked candidate correlation
is at most 0.90, the A3-confounded false/true pair drops by at least 0.20 or ends
at most 0.85, effective rank is at least 6 of 10, condition number is at most
1e6, environment leverage is at most 0.40, and diversity improves either maximum
correlation or condition number over the median single environment.

## Development smoke

Use only previously opened development seed 11:

- observation rate: 0.20;
- observation noise sigma: 0.01;
- eight environments;
- 256 weak windows per environment;
- 24 grouped selection replicates;
- forecast cutoff and spatial resolution unchanged from Stage A2/A3.

The smoke passes only if all conditions hold:

- oracle support Jaccard at least 0.90;
- reconstructed invariant support Jaccard at least 0.75 and strictly greater
  than both row-matched pooled baselines;
- leave-one-section-out median pairwise support Jaccard at least 0.70;
- every true-term frequency at least 0.75 and every false-term frequency at
  most 0.45;
- tip total weak-weight fraction at least 0.10;
- unseen-section cutoff reconstruction IoU at damage threshold 0.50 at least
  0.65;
- unseen-section final IoU improves by at least 0.08 over fixed physics and by
  at least 0.04 over pooled single-shot;
- unseen-section crack-tip error is at most 3 grid cells or 10% section length,
  and at least 15% lower than fixed and 10% lower than single-shot;
- initiation/event-time absolute error is at most 2 time steps;
- no section regresses from fixed physics by more than 0.10 IoU or 3 event-time
  steps;
- diversity beats one-environment and cloned row-matched controls by at least
  0.15 support Jaccard and lowers maximum false-term frequency by at least 0.20.

## Stop and confirmation rule

- A smoke failure stops Stage A4. Only an implementation defect may be fixed;
  thresholds, library, forcing schedule, and holdout assignment remain frozen.
- If the smoke passes, run a four-seed by two-observation-rate by two-noise-level
  development matrix using only seeds 11, 23, 37, and 51, observation rates
  0.10 and 0.20, noise sigmas 0.01 and 0.04, and all eight leave-one-section-out
  folds. Use 64 selection trials after the smoke.
- New confirmation seeds 67, 79, 101, and 131 remain sealed until both
  development gates pass.
- A first failure on the sealed confirmation matrix ends the synthetic route;
  do not tune and rerun against those seeds.

## Evidence boundary

Passing Stage A4 would establish only that deliberately diverse synthetic
excitation can make the declared correction library identifiable after sparse
field reconstruction. The full research goal still requires a real producer
snapshot, a genuine joint-training baseline, and road/FEM evidence with the
same support and forecast metrics.
