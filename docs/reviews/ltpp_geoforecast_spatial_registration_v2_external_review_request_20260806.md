# External review request: LTPP spatial-registration improvement v2

## Review target

Please review the v2 control-point availability protocol in:

`docs/experiments/ltpp_geoforecast_spatial_registration_improvement_v2_preregistration_20260806.md`

This is a new exploratory registration-improvement experiment. It is not a
continuation or rescue of the failed v1 audit.

## Questions for the reviewer

1. Does the Tier A/Tier B versus historical Tier C separation prevent reuse of
   v1-seen automatic candidates as independent final controls?
2. Are the proposed development/final control minimums and non-collinearity
   checks sufficient for the diagonal-affine, affine, and possible homography
   branches?
3. Is the candidate availability diagnostic allowed to proceed without
   changing any transform or crack label?
4. Should any source-data condition cause immediate
   `INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL` rather than algorithmic
   rescue?
5. Are the all-date thresholds, linear p95 rule, orientation, units, and
   one-shot termination rule adequately frozen for a later audit?

## Current evidence supplied for review

- v1 result: `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`;
- v1 evidence package and manifest under
  `local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_audit_v1_20260806`;
- read-only v2 inventory diagnostic and its tests, once generated;
- no final v2 metrics and no 2-D model training.

## Requested decision

Return exactly one of:

- `APPROVE_V2_AVAILABILITY_DIAGNOSTIC_ONLY`;
- `REVISE_V2_PROTOCOL_BEFORE_DIAGNOSTIC`;
- `REJECT_V2_INSUFFICIENT_INDEPENDENT_CONTROLS`.

No approval here authorizes the final v2 registration gate.
