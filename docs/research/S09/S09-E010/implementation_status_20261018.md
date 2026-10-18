# S09-E010 core implementation status

## Current state

`CORE_CODE_READY_PASS`

The design-reviewed per-cycle support loss, amplitude loss, B0/B25 projected
gradient rule, exact E009 A25 control and cumulative result classifier are now
implemented in `source/s09_e010_support_amplitude.py`. The module has no
optimizer step, schedule, checkpoint writer, producer resolver or launch path.

The first exact-commit review returned `REVISE_AND_REREVIEW` for two narrow
issues: accepted AUC floats were not canonicalised from their validated pair
counts before the inherited E009 threshold, and the frozen-packet preflight
did not independently recompute `L_S/L_A`. Both are repaired locally and the
focused rereview returned `CORE_CODE_READY_PASS` for exact commit
`45d8ec5f158d6fbdc608437f02da4fa43501157f`.

## Implemented contract

- `L_S` and `L_A` are formed independently for one cycle before any update
  reduction, using the frozen damage scale and `tau_s=1e-15`.
- The truth mask and target amplitude enter the supervised losses only. They
  are not added to model inputs, outputs or evaluation filtering.
- `L_D` remains the primary anchor. `L_S`, `L_A`, `L_U`, `L_H` and `L_P` are
  separately norm-matched and projected only when they conflict with `L_D`.
- B0 and B25 differ before the final clip by the declared `0.25*q_P` term at
  the same model state. Each complete direction receives one global L2 clip.
- The A25 control calls the reviewed E009 A25 implementation directly.
- The classifier uses the integer `2W+T` AUC boundary, enforces execution or
  method validity before performance, and preserves the cumulative Level 5/6
  requirements.

## Deterministic checks

The selected new and inherited suite passes 62 tests. It covers direct
NumPy/Torch loss agreement, empty/invalid support, finite gradients, parameter
reach, zero-gradient handling, same-state physics decomposition, exact A25
direction replay, single clipping, strict JSON output, pair-count boundaries,
protected-ratio trade-offs and cumulative result levels.

The added classifier regression proves that `0.8` and
`math.nextafter(0.8, 0.0)` classify identically when both encode the same
`20/0/5` pair counts. The nonzero-increment fixture now differentiates `L_A`
alone and verifies a finite nonzero gradient.

The read-only preflight then evaluated all 16 cycles of the frozen 86,756-node
development packet on CPU. It performed no optimizer construction or step and
left the model-state hash unchanged. All support masks were non-empty and the
strict-positive, `1e-15` and `1e-14` masks had identical counts. The maximum
A25 direction difference from the E009 implementation was exactly zero. The
largest numerical residual in the same-state
`B25_preclip-B0_preclip=0.25*q_P` check was `1.3704315460216776e-16`.
An independent NumPy float64 expression now recomputes both new losses on
every frozen cycle. The maximum absolute differences were
`2.842170943040401e-14` for `L_S` and `3.469446951953614e-17` for `L_A`, below
the fixed `1e-12` acceptance tolerance.

One implementation property must remain visible in review and future logs. At
the exact initial model, predicted damage increment is zero. PyTorch therefore
uses the zero subgradient of `abs(p)` in `L_A`, so `g_A` is zero for all 16
initial cycle states and is logged as
`AUXILIARY_NORM_AT_OR_BELOW_EPSILON`. `L_S`, `L_D`, `L_U`, `L_H` and `L_P`
all have nonzero initial gradients. The direct differentiability test now
differentiates `L_A` alone and confirms a finite nonzero gradient away from
zero increment. This
behaviour is permitted by the frozen protocol; it means the first balanced
update receives the new intervention through `L_S`, while `L_A` can become
active only after the prediction leaves zero.

## Evidence

- Frozen-packet receipt: `no_step_preflight_20261018.json`
- Core tests: `tests/test_s09_e010_support_amplitude.py`
- Read-only preflight: `scripts/s09_e010_no_step_preflight.py`
- Attempt: `S09-E010-A002-core-implementation`

## Boundary and next gate

This establishes a reviewed Code Ready numerical core. It is not runner
integration, Run Ready or scientific evidence. The allowed next gate is
runner/config/evidence integration with continued no-training verification. A
producer run requires later reviewed execution machinery, a frozen run card
and direct authorisation for that E010 execution.
