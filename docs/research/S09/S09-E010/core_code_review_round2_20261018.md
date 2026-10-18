# S09-E010 focused core rereview — round 2

## Verdict

`CORE_CODE_READY_PASS`

The verdict is bound to exact commit
`45d8ec5f158d6fbdc608437f02da4fa43501157f`. It closes both Round-1 blockers
without changing the frozen protocol, E009 implementation or execution scope.

Review package:

- file: `S09-E010-core-rereview-45d8ec5f158d-20261018.zip`
- bytes: `65,403`
- SHA256: `6a74c285ae2a5938dea33f67f3d9db5990bf01cd5838361988b29b7d3e36905f`
- manifest: `14/14` content hashes and byte counts independently verified
- duplicate or unlisted ZIP members: none, apart from the manifest itself
- conversation: <https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb>

## F1 closure — canonical AUC identity

The reviewer confirmed that `_validated_auc()` preserves the prior structural,
integer-count, finite and value/count consistency checks, then returns
`(2*wins+ties)/50` for downstream threshold logic. The integer primary gate,
four protected ratios and cumulative Level 5/6 requirements are unchanged.

Independent checks included:

- the original `0.8` versus `math.nextafter(0.8, 0)` counterexample;
- the new regression fixture and inherited cumulative states;
- rejection of clearly inconsistent or non-finite values;
- all 351 legal `(wins, ties, losses)` combinations, each at the canonical
  value and its two adjacent floating-point neighbours: 1,053 checks passed.

## F2 closure — frozen-example loss agreement

The reviewer confirmed that the 16-cycle preflight now uses detached arrays
from the existing forward and independent NumPy expressions for `L_S` and
`L_A`. The reference formula has separately frozen damage-scale and support
threshold constants, verifies them against the core constants, applies a
fixed absolute tolerance of `1e-12`, and stores per-cycle reference values,
differences and maximum differences.

Independent execution of the extracted reference and rejection logic showed:

- a float64 nonzero-increment fixture agrees with a separately written formula;
- matching observed/reference values pass;
- doubling either observed loss triggers its named mismatch;
- exactly `1e-12` passes, while the next larger representable float fails.

The reviewer recomputed all 32 stored differences from the receipt. The
maximum differences were `2.842170943040401e-14` for `L_S` and
`3.469446951953614e-17` for `L_A`, both matching the receipt and below the
frozen tolerance. Core and protocol hashes in the receipt matched the packet.

## No-regression and evidence boundary

The package changes add no forward, optimizer or step call. The A25 exact
direction difference remains zero; the maximum B25/B0 preclip physics residual
remains `1.3704315460216776e-16`; model-state hashes remain identical;
optimizer construction and steps remain zero; and the initial 16/16 `g_A=0`
records remain visible. The standalone nonzero `L_A` gradient assertion closes
the prior optional evidence-language gap. Intercepting the actual clip input
remains optional because no new blocking counterexample was found.

The reviewer independently verified package integrity, source diffs, extracted
scalar functions, NumPy formula/rejection behaviour and receipt arithmetic.
Its environment lacked PyTorch and pytest, so it did not rerun the complete 62
tests or frozen-packet model forward/autograd. Those remain local execution
evidence, not reviewer-reproduced execution.

## Allowed next scope

This PASS permits runner/config/evidence integration and continued no-training
verification from the reviewed exact commit. It does not authorise training,
an optimizer step, holdout access or producer launch, and it does not change
the frozen E009 scientific result.
