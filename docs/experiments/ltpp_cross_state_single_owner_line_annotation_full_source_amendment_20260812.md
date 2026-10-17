# LTPP cross-state single-owner line annotation full-source amendment — 2026-08-12

## Status

`PENDING_NARROW_EXTERNAL_REVIEW__DO_NOT_ANNOTATE`

## Trigger and frozen observation

Before any annotation was entered, the owner reported that the 2001 display
did not show the left map boundary. Inspection confirmed a source-window
failure: the v1 packet copied the prior automatic-rectangle-plus-48-pixel crop.
For `08-1053` on `20011030`, that crop begins near source x=586 while the
printed left frame is visibly farther left on the original 0–50-ft page. The
cropped packet has zero completed line tasks, zero completed spot checks, and
zero locked maps. It is retained unchanged and is superseded for data entry.

## Exact amendment

The scientific claim boundary, 17 line identities, eight fixed spot checks,
status vocabulary, click count, and single-owner classification remain
unchanged. Only the source-window and dependent geometric checks change:

1. Display and hash each complete original `segment_0_50_white.png`; set the
   stored source origin to `(0,0)`. No crop, rescale, deskew, enhancement, or
   rectification is applied.
2. Render the frozen automatic rectangle as a grey dashed suggestion only. It
   may initialise scrolling and suggested lines, and its width/height remains
   the fixed scale for the existing 50% minimum click-span rule. It is not an
   admissible-region boundary.
3. The four owner-labelled outer lines `V0`, `V10`, `H0`, and `H5` define an
   owner frame when all four are usable. Their four intersections must be
   finite, form the expected strict line-family order, and bound a convex
   quadrilateral. A derived point is in bounds when it is on the interior side
   of all four normalised boundary lines, allowing 3 source pixels outward.
4. If any outer line is non-usable or the owner frame is invalid, the map may
   still lock as an availability record, but every otherwise computable point
   is `invalid_derived: owner_frame_unavailable`. There is no fallback to the
   automatic rectangle.
5. Family order is evaluated at the owner-frame centroid when available;
   otherwise at the automatic-rectangle centre. Same-family crossing anywhere
   inside the complete source image blocks locking.

The UI must visibly distinguish the grey automatic suggestion from the
owner-labelled cyan/magenta lines and state that the complete source is shown.

## Required regression tests

Retain the approved synthetic suite and add:

- a true owner frame lying partly outside the automatic suggestion must pass;
- an intersection inside the automatic suggestion but outside the owner frame
  must be invalid;
- one non-usable outer line must yield `owner_frame_unavailable` without
  automatic-rectangle fallback;
- packet initialisation must copy the full source and store origin `(0,0)`;
- both 2001 maps must expose full image dimensions and unchanged source hashes.

## Claim boundary and stop rule

The result remains
`EXPLORATORY_SINGLE_OWNER_LINE_ANNOTATION__NOT_INDEPENDENT`. It cannot create
independent Tier B/final controls, fit a transform, run a final gate, qualify
spatial registration, or authorise a 2-D model. Implementation and data entry
remain blocked until a narrow external review returns approval with no blocker.
