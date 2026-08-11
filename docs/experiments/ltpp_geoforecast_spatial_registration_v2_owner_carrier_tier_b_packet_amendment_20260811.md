# LTPP spatial-registration v2 owner-carrier Tier B packet amendment — 2026-08-11

## Status

`FROZEN_PENDING_EXTERNAL_REVIEW__DO_NOT_ANNOTATE`

This is a narrow source-window amendment to the independently reviewed v2
Tier B availability protocol. It does not alter the frozen v1 result
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`, disclose final controls,
fit or select a transform, compute residuals, or run the one-shot final gate.

## Reason for the amendment

The first blind packets were cut from obsolete automatic `grid_results`
rectangles. Subsequent full-source work recovered the official map pages, and
the owner then locked and visually accepted the four outer printed-frame
corners for all eight 0–50 ft maps. The old blind packets therefore do not
audit the source carrier now used by the engineering MVP and must remain
historical evidence only.

## Frozen inputs

The replacement packet builder accepts exactly the locked owner-corner packet:

`local_archive/real_road_acquisition/ltpp_06_1253_owner_corner_carrier_mvp_v3_20260810/`

- `owner_corners.json` SHA-256:
  `3f86fc7c0d28d578387d5e8d99295faf8e9bc4d45e437f4d1e181940e96a4803`
- `manifest.sha256` SHA-256:
  `b609aba4d3026929e8120e06ae81116cdbf1e1e898f64b403a564cacab8233f2`
- dates, in fixed order: `19910610`, `19951024`, `19970228`, `19980407`,
  `20010913`, `20030514`, `20071106`, `20120417`.

The owner clicks are construction controls used only to choose a source
window. They are neither fit, development, nor final audit controls and may
not contribute to any registration residual.

## Deterministic source-window rule

For each locked source image, take the axis-aligned bounding box of the four
accepted source-pixel corners. Expand it by exactly 48 source pixels on every
side and clip only to the source-image bounds. Bounds use
`left=floor(min(x))-48`, `top=floor(min(y))-48`,
`right=ceil(max(x))+48+1`, and `bottom=ceil(max(y))+48+1`, with NumPy-style
half-open slicing `[top:bottom, left:right]`.

The image is not rectified, rescaled, thresholded, enhanced, denoised, or
masked. The extra margin ensures the protocol's 12-source-pixel arms remain
visible at outer candidates. Packet clicks are stored in crop pixels and are
converted back only by adding the sealed integer crop origin.

## Rules retained without change

- The candidate universe remains exactly the 66 `G[i,j]` controls and their
  physical coordinates remain `(15.24*i/10, 5.00*j/5)` metres.
- Fit, development, and final identities are unchanged.
- Seeds remain `20260807` for annotator A and `20260808` for annotator B;
  candidate ordering remains `seed + map_index*97`.
- Two eligible, independent, blind human annotators are required. The user and
  implementer are ineligible because they have seen v1 outcomes.
- Each annotator sees only one blinded map at a time and may use only printed
  grid/frame/tick ink under the frozen Tier B annotation protocol.
- Consensus remains two `usable` clicks within `4.0` source pixels, followed
  by arithmetic averaging. There is no rescue, replacement, snapping, or
  third annotator.
- Final-control roles and date mappings remain sealed until the authorized
  one-shot gate.

## Stop rules

Before external approval, a generated replacement packet is a review
candidate only and its records must remain unlocked and empty. Any annotation,
consensus, transform fitting, or final-control unsealing before approval
invalidates it.

After approval, any failure to preserve source hashes, exact crop rule,
blinding, two-person independence, or the original Tier B consensus protocol
terminates this packet. Missing required controls terminates the route as
`INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`; it does not authorize detector
tuning or a more flexible registration model.
