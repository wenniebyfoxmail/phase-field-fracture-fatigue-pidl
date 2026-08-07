# LTPP geoforecast spatial-registration track

## Mechanism question

Can the frozen printed-grid rectification support two-dimensional crack-position
and continuation-tip prediction, or is its coordinate uncertainty too large?

## Claim boundary

This track audits the coordinate carrier only. It does not alter frozen crack
labels, train a forecast model, identify the same physical crack across dates,
or prove that a hand-drawn stroke is a material-point observation.

The existing scalar crack-length track remains separate. A failure here blocks
two-dimensional position/tip claims but does not retrospectively invalidate a
separately reviewed scalar-length analysis.

## Current evidence

- The acquisition receipt records a common nominal `15.24 m x 5.00 m` frame
  but explicitly records `direct_pixel_registration = false`.
- Each survey was independently rectified by deskewing, selecting a printed
  grid rectangle, and resizing to `1524 x 500 px`.
- Same-image primary/secondary agreement is not cross-date registration error.

## Experiment states

| State | Status | Evidence |
|---|---|---|
| Existing nominal rectification | coordinate comparison only | `../ltpp_06_1253_rectification_gate_20260805.md` |
| v1 conditional internal-grid audit | `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL` | `ltpp_geoforecast_spatial_registration_audit_v1_result_20260806.md` |
| v2 independent-control availability work | `APPROVE_V2_AVAILABILITY_DIAGNOSTIC_ONLY`; blind Tier B collection may begin, final gate remains closed | `ltpp_geoforecast_spatial_registration_v2_tier_b_availability_20260807.md` |
| page-frame engineering MVP | `EXPLORATORY_REGISTRATION_MVP_COMPLETED__NOT_QUALIFIED`; delivery path completed, no independent physical controls | `ltpp_geoforecast_spatial_registration_mvp_20260807.md` |

## Active gate

The v1 gate is terminal: only `2/8` dates qualified. Three dates had insufficient
fixed controls and three additional dates failed spatial-error thresholds. The
current carrier cannot enter any 2-D crack-position or tip algorithm. Failure
cannot be rescued by deleting dates, changing the detector, or trying
homography/TPS/piecewise transforms inside v1.
The v2 read-only inventory found no independent final controls. A minimal
external re-review approved only blind Tier A/B availability collection; no
transform fitting, final-control disclosure, or final gate is authorized.
The separate page-frame MVP is a delivery-path smoke only: it may render
common-canvas images but cannot make a physical registration or 2-D claim.

## Next action

Keep scalar-length work separate and explicitly measurement-noise limited. Any
future spatial route requires a new, independently reviewed registration or
acquisition track with external validation; no 2-D model training is authorized
on the current eight-date carrier. The immediate v2 action is independent
Tier A/B control adjudication, not transform tuning.
