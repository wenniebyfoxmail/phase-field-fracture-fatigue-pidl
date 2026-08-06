# LTPP spatial-registration improvement v2: read-only diagnosis

## Status

`EXPLORATORY_REGISTRATION_IMPROVEMENT`

This is a read-only inventory of the historical v1 grid candidates. It is not
a transform experiment, final registration audit, or 2-D model authorization.

## Evidence and provenance

- Protocol: `ltpp_geoforecast_spatial_registration_improvement_v2_preregistration_20260806.md`.
- Inventory code: `scripts/ltpp_inventory_registration_controls_v2.py`.
- Input: `local_archive/real_road_acquisition/ltpp_06_1253_rectified_grid_v3_20260805/grid_gate_results.json`.
- Output package: `local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_improvement_v2_20260806/`.
- The output receipt records SHA-256 values for the protocol, code, and input;
  its `manifest.sha256` verifies all generated files.

## Diagnostic rule

The inventory uses the frozen v1 expected line positions and candidate window
only to count missing and ambiguous historical candidates. It does not fit a
translation, affine transform, homography, or local warp. It does not read
crack labels or use distress geometry.

Because v1 control candidates and outcomes were already observed, every such
candidate is explicitly labelled `non_independent_of_v1`. No candidate is
eligible as a final v2 control without a new Tier A/B independent adjudication.

## Per-date inventory

| Date | v1 mode | Missing candidate lines | Unique candidates | Ambiguous candidates | Independent final controls | Diagnosis |
|---|---|---:|---:|---:|---|---|
| 1991-06-10 | dense internal grid | 0 | 9 | 8 | No | Historical grid exists, but candidate identity is ambiguous |
| 1995-10-24 | outer border pair | 9 | 8 | 0 | No | Internal vertical references unavailable in the receipt |
| 1997-02-28 | dense internal grid | 0 | 14 | 3 | No | Candidate identity remains ambiguous at selected lines |
| 1998-04-07 | dense internal grid | 0 | 15 | 2 | No | Candidate identity remains ambiguous at selected lines |
| 2001-09-13 | dense internal grid | 3 | 12 | 2 | No | Missing and ambiguous vertical references |
| 2003-05-14 | dense internal grid | 0 | 13 | 4 | No | Several candidate identities are ambiguous |
| 2007-11-06 | dense internal grid | 4 | 10 | 3 | No | Missing/ambiguous references, including a missing horizontal line |
| 2012-04-17 | dense internal grid | 0 | 17 | 0 | No | Candidate set is internally unique but remains v1-dependent |

## Interpretation

The diagnostic separates two problems:

1. **Potentially algorithmic:** line-center extraction, candidate disambiguation,
   and the choice between diagonal affine and higher models can be studied on
   a development set after independent controls are frozen.
2. **Not currently source-proven:** whether missing/ambiguous lines are truly
   present in the source, occluded by annotations, absent because the survey
   frame differs, or distorted by scanning. The current receipt cannot decide
   this without independent Tier A/B review.

The result is therefore not evidence that a homography or non-rigid warp will
solve the route. It is evidence that the current v1 receipt cannot supply the
independent final audit controls required by v2.

## Decision

`EXPLORATORY_REGISTRATION_IMPROVEMENT`

The route is **not ready for a final v2 audit**. The next permitted action is an
external review of the v2 protocol followed by independent Tier A/B control
adjudication for all eight dates. If any date cannot supply the frozen
development and final controls, the route terminates as
`INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`.

The v1 negative result remains unchanged, and `docs/research_frontier.md` is
not updated at this exploratory stage.
