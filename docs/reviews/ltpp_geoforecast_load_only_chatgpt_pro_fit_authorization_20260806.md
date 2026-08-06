# ChatGPT Pro fit authorization: LTPP load-only track

Date: 2026-08-06

## Authorization headline

`APPROVE_LOAD_ONLY_POSTERIOR_FIT`

## Authorized scope

The frozen 29-row G-versus-G+L posterior fit, LOSO sealed evaluation, fixed
24-development + 5-future-time secondary evaluation, and preregistered scoring
only.

## Frozen inputs

- G = G1 + G2 + G3;
- G+L = G1 + G2 + G3 + T1;
- T1 = latest complete pre-source-year `ANNUAL_ESAL_TREND` under source-active
  construction;
- only excluded transition: `06-1253-T07`;
- no climate, moisture, structure, FWD, AADTT, alternate traffic field,
  interaction, spline, polynomial, feature selection, or architecture search;
- endpoint, model family, fold-local scaling, sampler settings, LOSO/future
  splits, metrics, and thresholds remain frozen;
- 90% coverage gate: exactly 25--27 of 29 rows.

## Explicit prohibitions

After outcome access, do not delete or replace rows, alter ESAL alignment or
construction, add variables, change the endpoint or split, change thresholds,
search architectures, or perform exploratory rescue.

This receipt authorizes no claim of causality and no prediction of crack
placement or two-dimensional geometry.
