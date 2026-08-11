# LTPP geometry-assisted grid-control pilot preregistration — 2026-08-11

## Status and purpose

`EXPLORATORY_AI_ASSISTED_CONTROL_PILOT__NOT_INDEPENDENT`

This separately named pilot makes the 66-point annotation task operationally
easier. It does not modify the immutable owner-carrier Tier B A/B packet and
cannot create fit, development, final, Tier A, or Tier B controls.

## Frozen assistance rule

For each date, use the four locked owner-accepted outer-frame construction
points to compute one projective mapping from the logical rectangle to the
source image. Suggest every `G[i,j]` at logical coordinates
`(i/10, (5-j)/5)` in image row convention. Crop only by the already frozen
four-corner bounding box plus 48 source pixels.

No crack, distress, WIM, repair, handwriting, cross-date image, v1 residual,
or final-control role is read. There is no feature matching, learned model,
line detector, threshold selection, or candidate replacement. “AI-assisted”
here means deterministic geometry-assisted pre-positioning, not independent
computer-vision ground truth.

## Human interaction

The interface must state that `i` increases left-to-right and identifies the
vertical printed line, while `j` increases bottom-to-top and identifies the
horizontal printed line. It displays all suggestions, highlights the selected
row and column, and lets the user accept, move, or mark the point
`missing_print`, `occluded`, or `ambiguous`.

## Claim and stop boundary

The user has seen v1 outcomes, so these corrected points are development-only
pilot records. They may test the annotation UI and the end-to-end engineering
carrier, but they may not enter the approved blind A/B packet, availability
consensus, model selection, residual calculation, final gate, or 2-D model.

The formal A/B packet must remain empty while this pilot runs. Any future
scientific Tier B route still requires two different eligible blind humans
using the immutable approved packet.
