# LTPP owner-reviewed outer-corner carrier MVP preregistration — 2026-08-10

## Classification and purpose

This is an independent `EXPLORATORY_REGISTRATION_IMPROVEMENT` construction-control
experiment. It does not continue, replace, or reinterpret spatial-registration
audit v1. The immutable v1 result remains
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

The immediate question is deliberately narrow: can the four intersections of
the printed outer road-grid boundary be recorded reproducibly on each of the
eight already-isolated 0–50 ft map images, so that a later engineering MVP can
render them on one physical carrier?

The owner has seen prior registration diagnostics. Therefore these clicks are
construction controls only. They are not blind, independent final controls and
cannot qualify registration or reopen the 2-D modelling route.

## Frozen inputs

Only `segment_0_50_white.png` from the frozen map archive is used. The eight
survey dates and source SHA-256 values are:

| Date | Image size (px) | SHA-256 |
|---|---:|---|
| 19910610 | 3006 × 964 | `b8943157993279f2f84bd04570b9328965c02c053148285af1efcf2557cc5212` |
| 19951024 | 2895 × 929 | `cef8a827e4f85e8b9be75b9e0480db8861ffc5220454d61296238e39de5a7fb8` |
| 19970228 | 2982 × 951 | `782c32c76cf85b17fe21e2500e0ee5fccc0afbf7c63d1918df3000c05a09bd5c` |
| 19980407 | 2987 × 961 | `8d82c6f1bb2d1fc9aa4d57c41e99690d79ec631e5b72c8148c645bc4dbe2d8da` |
| 20010913 | 2982 × 958 | `78671332803fa7e7b36a371c59bb580ccba63f9a6114c9f78c3eb78e93c47221` |
| 20030514 | 2956 × 948 | `060ec9143db4260cf556118fbdfbc3b5c6ece1e9a6f4544c557c43265c9acd0d` |
| 20071106 | 2984 × 954 | `0ddb2c388f8701c7a8a0fb45a8654a78767e6493dcb7c1006a957264c0dd6c06` |
| 20120417 | 3153 × 1033 | `17a2c90d478aabba45e1c673d1d9542697b03a69a81f44fe7035005f6d28f90b` |

No PDF page discovery, crack vector, WIM box, repair mark, distress label,
cross-date crack shape, or previous automatic frame candidate may be loaded by
the annotation tool.

## Frozen corner rule

For every date the owner clicks exactly four points in this fixed clockwise
order:

1. `TL`: intersection of the left outer solid boundary and top outer solid
   boundary — physical coordinate `(0 ft, 15 ft)`;
2. `TR`: intersection of the right outer solid boundary and top outer solid
   boundary — `(50 ft, 15 ft)`;
3. `BR`: intersection of the right outer solid boundary and bottom outer solid
   boundary — `(50 ft, 0 ft)`;
4. `BL`: intersection of the left outer solid boundary and bottom outer solid
   boundary — `(0 ft, 0 ft)`.

The target is the centreline intersection of the two outer **solid** printed
strokes. Dashed grid intersections, cracks crossing grid lines, handwriting,
dimension ticks outside the rectangle, and disease/repair marks are ignored.
If a stroke is thick, click its visual centreline. The interface provides a
zoom control, loupe, fixed-order labels, undo, and reset.

Before a date can be locked, the four source-pixel points must be unique,
in bounds, clockwise and convex, with the expected left/right and top/bottom
ordering. These checks detect click-order mistakes only; they do not establish
annotation correctness.

## One-way review sequence

1. A date may be saved, undone, or reset while unlocked.
2. Locking a date makes its record immutable inside this packet.
3. After all eight dates are locked, the tool creates per-date large-marker
   overlays and a contact sheet with same-stem figure sidecars and a SHA-256
   manifest.
4. The owner visually reviews those assets. No warp is produced before that
   review.
5. If the locked points are judged wrong, this packet is retained as a failed
   exploratory packet. Corrections require a separately named packet and must
   not be described as independent validation.

## Physical-coordinate note

The printed rectangle is 50 ft × 15 ft, equal to 15.24 m × 4.572 m. This
annotation experiment freezes those physical endpoints but deliberately does
not freeze a raster quantisation. A later, separately recorded rendering step
must state its output dimensions and metre-per-pixel convention explicitly.

## Allowed outcomes and stop rule

Before all eight records are locked and visually accepted, status is
`OWNER_CORNER_COLLECTION_INCOMPLETE__EXPLORATORY_ONLY`.

After visual acceptance, the strongest allowed corner-stage status is
`OWNER_CORNER_CARRIER_READY__EXPLORATORY_ONLY`.

Neither status is a registration qualification. This stage computes no
median, p95 or maximum physical registration error and never runs the v2 final
gate.
