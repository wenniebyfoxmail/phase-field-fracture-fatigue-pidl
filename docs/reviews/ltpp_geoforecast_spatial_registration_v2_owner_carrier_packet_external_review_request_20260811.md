# External review request: v2 owner-carrier Tier B packet amendment

## Requested scope

Please review only the narrow source-window amendment in
`docs/experiments/ltpp_geoforecast_spatial_registration_v2_owner_carrier_tier_b_packet_amendment_20260811.md`
and its packet builder. No registration result or final-control record is
available for review.

## Unchanged protocol

The 66-candidate universe, fixed fit/development/final roles, two-person blind
Tier B rule, four-source-pixel consensus limit, model ladder, physical error
thresholds, linear p95 rule, 8/8 requirement, and one-shot final gate remain
unchanged. The user and implementer remain ineligible annotators.

## Exact change

The obsolete automatic `grid_results` crop is replaced by an axis-aligned
source crop derived mechanically from the four locked, owner-accepted outer
frame construction points plus a fixed 48-source-pixel margin. The image is
otherwise copied without rectification or enhancement. Those four points are
used only for packet windowing and never as audit controls or residuals.

## Blocking questions

1. Does the deterministic crop rule preserve the approved Tier B evidence and
   source-pixel coordinate convention without introducing model-selection or
   final-control leakage?
2. Is the separation between owner construction controls and independent Tier
   B audit controls explicit enough?
3. May the immutable review-candidate packet be released to two eligible
   annotators after verifying that all records are still empty and unlocked?

## Allowed decisions

- `APPROVE_OWNER_CARRIER_TIER_B_COLLECTION_ONLY`
- `REVISE_OWNER_CARRIER_PACKET_BEFORE_COLLECTION`

Approval authorizes only independent annotation and mechanical availability
consensus. It does not authorize transform tuning, final-control disclosure,
the final gate, or a 2-D model.
