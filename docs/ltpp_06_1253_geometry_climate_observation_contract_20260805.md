# LTPP 06-1253 observation-only geometry/climate contract

## Purpose

Continue the real-road Freeze-Then-Select route after rejection of the
pressure-linear Ferrite branch without fabricating phase-field mechanics.

This is an alternative input schema, not a relaxed version of the mechanical
preflight. Its evidence label is `ltpp_observation_only_geometry_climate`.

## Required transition fields

- physical cell coordinates and positive cell areas on the qualified
  `15.24 m x 5 m` grid;
- frozen start/end damage fields in `[0,1]`;
- valid-observation mask;
- start/end field hashes and field-adapter hash;
- adapter fit dates and explicit future-geometry leakage flag;
- observed monthly climate forcing with coverage, units, and source hashes;
- candidate-status map distinguishing observed, sparse-unusable, absent,
  unavailable-resolution, and forbidden channels.

The transition schema contains no displacement, strain energy, active driver,
fatigue history, degradation, phase-field length, or fracture toughness.

## Candidate authorization

| Candidate | Status |
|---|---|
| low-temperature exposure below 10 C, annualized | observed |
| absolute monthly-mean temperature change, annualized | observed |
| monthly-bin precipitation, overlap-prorated and annualized | observed |
| traffic rate / cumulative traffic | sparse-unusable |
| moisture / humidity | absent |
| seven-day rain | unavailable resolution |
| traffic interactions | forbidden |

Only observed candidates may enter the pointwise library that is subsequently
integrated by a weak-form system. Missing channels must raise an error rather
than become zero columns.

Primary interval semantics are source-exclusive and target-inclusive. Boundary
months are prorated by overlapping calendar days under a declared uniform
within-month approximation. Low-temperature sensitivity uses 5/10/15 C in
separate runs; 10 C is primary. The incomplete 2012-2015 interval is geometry
only and cannot enter confirmatory climate selection.

## Temporal modes

- Selection mode: adapter fit dates may not exceed the transition end date.
- Strict forecast mode: adapter fit dates may not exceed the transition start
  date.
- In both modes, `future_geometry_used` must be false.

## Geometry gate

The physical grid is qualified, but rectified ink is explicitly not a crack
mask. Field adaptation remains locked until:

1. primary and secondary annotations are independently locked;
2. post-lock pairing metrics pass;
3. uncertain disagreements are adjudicated without future-map leakage;
4. all nine geometry records and hashes are frozen in a qualified manifest.

## What passing would mean

Passing this route permits a same-section, geometry-climate comparison of FTS,
single-shot selection, and genuine joint training. It does not satisfy the full
traffic-temperature-moisture objective or prove cross-road generalization.
