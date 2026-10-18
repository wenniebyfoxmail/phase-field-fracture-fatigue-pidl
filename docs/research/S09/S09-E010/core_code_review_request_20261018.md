# S09-E010 exact-commit core code review request

Please review the attached ZIP as an exact-commit implementation candidate for
the already design-reviewed S09-E010 protocol.

## Identity

- Exact commit: `7b3d46739a4697475e8b5a8299b56b341b69d5c5`
- Bundle: `S09-E010-core-review-7b3d46739a46-20261018.zip`
- Bundle bytes: `34,655`
- Bundle SHA256:
  `0965b9895eca341fc6ec22f2fa4fd3de8ed431bfbf10fa58fdeb70813cc7b033`
- Manifest entries: 8

Please verify the ZIP SHA256 and every manifest entry before reviewing code.

## Review question

Does this exact commit implement the frozen per-cycle support/amplitude losses,
three-arm gradient geometry, exact E009 A25 control and cumulative result
classifier correctly and fail closed, while remaining a no-training core with
no optimizer or producer path?

Please check specifically:

1. `L_S` and `L_A` use the projected per-cycle damage increment, frozen scale,
   truth-active mask and weighted amplitude exactly as protocol v2 specifies;
   there is no pooled-cycle calculation or target-derived inference path.
2. All gradients are checked finite before norm/projection arithmetic. `L_D`
   remains the anchor; each auxiliary is independently norm-matched and has
   only its negative anchor component removed. B0/B25 differ at the same state
   by `0.25*q_P` before the single final clip.
3. A25 calls the reviewed E009 implementation exactly. The frozen-packet
   receipt's zero direction difference and unchanged model hash are credible.
4. The integer `2W+T` primary boundary, four protected ratios, validity
   precedence and cumulative Level 5/6 classifier cannot be bypassed by missing
   evidence, floating-point AUC values or an earlier lower-level failure.
5. Empty support, nonpositive target amplitude, nonfinite values, stationary
   anchor, zero auxiliary gradients and strict JSON boundaries fail or record
   exactly as declared.
6. At the exact initial model, all 16 `g_A` vectors are zero because predicted
   increment is zero and `abs` uses its zero subgradient. Confirm that the code
   records this permitted condition without silently replacing the objective,
   and that the direct nonzero-increment test establishes a usable gradient
   away from zero.
7. No function in the candidate can perform an optimizer step, training loop,
   checkpoint selection, holdout access or producer launch.

The local evidence is 61 selected tests passed, plus
`NO_STEP_PREFLIGHT_PASS` on all 16 frozen development cycles. This evidence is
provided for reproduction, not as a substitute for review.

Please return one of these exact first lines:

- `CORE_CODE_READY_PASS`
- `REVISE_AND_REREVIEW`

For a PASS, state the exact commit and checks reproduced. A PASS permits only
runner/config/evidence integration and further no-training verification. It
does not authorise a producer run or support a scientific claim.

For revision, list each blocking counterexample with the file/function,
minimal reproducer, expected behaviour and observed behaviour. Separate
blocking defects from optional improvements.
