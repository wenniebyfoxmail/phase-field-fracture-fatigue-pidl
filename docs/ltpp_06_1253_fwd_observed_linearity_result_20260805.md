# LTPP 06-1253 observed FWD linearity result

## Decision

`FAIL_OBSERVED_LOAD_LINEARITY`

The preregistered cheaper diagnostic rejects the proposed static
linear-elastic Ferrite inversion before any solver or inverse optimization is
run.

## Frozen evidence

Source package:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_fwd_observed_linearity_v1_20260805`

All four derived files pass their frozen SHA-256 manifest.

| Test | Groups | Median dispersion | P90 dispersion | Gate | Result |
|---|---:|---:|---:|---:|---|
| within-height repeatability | 872 | 0.2845% | 1.2067% | 5% / 10% | pass |
| across-height pressure linearity | 218 | 10.0384% | 15.6204% | 5% / 10% | fail |

The audit used only the 1989-1998 calibration dates and `3,488` qualified
sensor observations. It did not use the 2003 holdout.

## Interpretation

The measurements are technically repeatable within a drop height, but
deflection divided by plate pressure is not sufficiently invariant across load
heights. A single quasi-static linear-elastic parameter vector is therefore not
an authorized model for these observations under the frozen gate.

This result does not identify the cause. Possible causes such as stress-dependent
unbound layers, asphalt nonlinearity, load-dependent contact, or other model
discrepancy remain hypotheses and are not fitted after seeing this result.

## Consequence

- Do not implement or run the preregistered linear-elastic inversion.
- Do not produce a Ferrite mechanical manifest from this branch.
- Do not unlock phase-field/PIDL fields or call the FWD package a qualified
  mechanical teacher.
- Preserve the complete FWD package as real-road observation evidence and a
  negative discriminator.
- Continue the observation-only LTPP geometry-climate route after independent
  crack-vector pairing and adjudication.
- A nonlinear or viscoelastic mechanical branch would require a new independent
  review, new preregistration, and new holdout rules; it is not an automatic
  continuation of this failed branch.

## Claim boundary

Supported: repeated FWD measurements are precise, while a frozen
pressure-linear layered-elastic abstraction fails the calibration-only
linearity gate on this section.

Not supported: the specific nonlinear mechanism, unique layer moduli, Ferrite
field accuracy, crack prediction, or traffic-temperature-moisture selection.

