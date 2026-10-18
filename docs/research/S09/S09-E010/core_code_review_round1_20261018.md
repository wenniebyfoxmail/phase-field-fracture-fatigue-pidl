# S09-E010 exact-commit core review — round 1

## Verdict

`REVISE_AND_REREVIEW`

Reviewed candidate: `7b3d46739a4697475e8b5a8299b56b341b69d5c5`

Review package:

- file: `S09-E010-core-review-7b3d46739a46-20261018.zip`
- bytes: `34,655`
- SHA256: `0965b9895eca341fc6ec22f2fa4fd3de8ed431bfbf10fa58fdeb70813cc7b033`
- manifest: `8/8` content hashes and byte counts verified by ChatGPT Pro
- conversation: <https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb>

## Blocking findings

### F1 — accepted AUC float was not canonicalised from pair counts

`_validated_auc()` accepted values within `1e-15` of the value determined by
the integer counts, but returned the supplied float. `classify_e010()` then
passed that float to the inherited E009 classifier, whose relative-repair rule
contains `AUC >= 0.80`.

Consequently, records with the same `20 wins, 0 ties, 5 losses` were both
accepted but could classify differently when their supplied values were `0.8`
and `math.nextafter(0.8, 0.0)`. The required repair is to keep the consistency
check and return the value reconstructed from `2W+T` for all downstream
classification.

### F2 — frozen-example loss agreement was not independently checked

The 16-cycle preflight recorded the core function's `L_S` and `L_A`, but did
not independently recompute them from predicted peak damage, target peak
damage, prestate and nodal weights. Because norm matching removes a positive
scalar rescaling of an auxiliary gradient, the existing direction checks
could miss a loss-value scaling error while still issuing
`NO_STEP_PREFLIGHT_PASS`.

The required repair is a separate NumPy float64 formula for both losses on
every frozen cycle, with fixed comparison tolerance, per-cycle reference and
difference records, and fail-closed maximum-error checks. This must reuse the
existing forward results and add no optimiser or training work.

## Findings that passed review

- The definitions of `L_S` and `L_A`, truth-support boundary and frozen damage
  scale were not challenged.
- `L_D` remains the anchor; auxiliary objectives are independently norm
  matched and projected.
- The B0/B25 construction, zero-amplitude subgradient rule, A25 control entry
  point, cumulative Level 5/6 order, validity precedence and no-training core
  boundary were accepted in static review.
- The reviewer independently reproduced 26 scalar classifier assertions and
  recomputed the existing receipt's 16-row summaries. The review environment
  lacked PyTorch and the full inherited runtime/packet, so it did not rerun
  the local model, gradients, 61-test suite or model hash.

## Optional improvements

The reviewer separated two non-blocking suggestions: prove a nonzero `L_A`
gradient by differentiating `L_A` alone on the synthetic nonzero-increment
fixture, and consider intercepting the actual vector passed to the global
clip when strengthening the same-state B25/B0 regression.

## Resolution scope

The narrow revision canonicalises AUC from validated integer counts, adds the
frozen-cycle independent `L_S/L_A` reference checks, and adds the standalone
nonzero `L_A` gradient assertion. It does not change the protocol, E009,
loss definitions, thresholds, arms, update budget or any producer path.

This review did not authorise training, holdout access or producer launch.
