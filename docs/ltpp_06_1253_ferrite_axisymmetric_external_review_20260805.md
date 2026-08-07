# Independent planning review: LTPP 06-1253 Ferrite diagnostic

Reviewed: 2026-08-05

Reviewer: independent high-reasoning planning agent `019fcfef-1621-7423-85b0-a47ed0125ad9`.
The reviewer did not edit files or run Ferrite/PIDL.

## Recommendation

Use a new 2D axisymmetric, quasi-static, layered-elastic Ferrite solver. Do not
reuse the existing SENT plane-strain phase-field producer and do not start with
a 3D quarter-domain. The circular plate, horizontal layers, and radial FWD
offsets make axisymmetry the smallest model aligned with the observations.

The weak form must include the axisymmetric measure and hoop strain. Sensor
records must align by physical `CENTER_OFFSET`, not by sensor number. The 2003
`-305 mm` sensor is an axisymmetry check against `+305 mm`, not an independent
radial location.

## Recommended mechanical abstraction

- Merge the 0.2-inch chip seal with the 3.6-inch AC layer, giving a 96.52 mm
  effective surface layer.
- Use a 388.62 mm crushed-gravel base.
- Continue the subgrade material to the numerical far field; do not introduce a
  rigid boundary at the recorded 14.8-inch sampling depth.
- Invert at most `E_surface_20C`, surface temperature coefficient, `E_base`, and
  `E_subgrade`.
- Hold Poisson ratios fixed and repeat low/nominal/high sensitivity scenarios.
- Treat all recovered values as conditional effective moduli.

## Recommended validation

- Six leave-one-date-out folds over 1989-1998.
- Entire 2003-05-15 event as final code-level temporal holdout.
- Group repeated drops by date, point, lane, and drop height; do not treat four
  repeated drops as independent samples.
- Lock thresholds, mesh, weights, and parameter bounds before evaluating 2003
  individual-basin errors.
- Compare against an observation-only robust regression using pressure,
  temperature, and physical offset.
- Retain an ensemble of near-optimal solutions and report non-identifiability
  rather than one convenient modulus vector.

## Recommended numerical falsification gates

- Homogeneous half-space benchmark.
- Reaction versus `pressure * pi * radius^2`.
- Displacement linearity under doubled pressure.
- Coarse/medium/fine mesh comparison.
- Finite-domain comparison against a 1.5-times larger radial/depth domain.
- Observation-side load-linearity audit before inversion.

## Claim boundary

Even a passing diagnostic supports only the claim that a conditional,
three-medium, quasi-static axisymmetric model predicts later FWD peak-deflection
basins on the same LTPP section. It does not qualify phase-field damage/history,
traffic/moisture mechanisms, a FEM teacher, crack prediction, or cross-road
generalization.

## Local decision

Adopted with two explicit qualifications:

1. The 2003 event is not analyst-blind because aggregate properties were already
   inspected; it is a frozen code-level temporal holdout.
2. SDR 39 backcalculation rows have `RECORD_STATUS=D` and are excluded from the
   success criterion; they may only initialize or contextualize parameter
   ranges.

