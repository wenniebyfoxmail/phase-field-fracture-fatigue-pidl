# LTPP lattice-envelope frame-range MVP result — 2026-08-10

## Result

`EXPLORATORY_LATTICE_ENVELOPE_FRAME_RANGE_MVP__NOT_QUALIFIED`

The preregistered lattice-envelope rule was run once on all eight already-seen development pages. It yielded eight visual candidates; it did not run any registration transform, residual calculation, crop, control extraction, or final gate.

## Observed comparison with the superseded solid-only candidates

| Date | Lattice-envelope output | Status for next step |
|---|---|---|
| 19910610 | Candidate extends below the accepted 1991 lower boundary. | Review required; do not use. |
| 19951024 | Candidate available. | Owner review required. |
| 19970228 | Candidate available. | Owner review required. |
| 19980407 | First candidate produced, where solid-only rule had none. | Owner review required. |
| 20010913 | Still ends at the internal `y=0.5 m` line rather than the `y=0` baseline. | Known failure; do not use. |
| 20030514 | No longer collapses to the prior tiny lower-right rectangle. | Owner review required. |
| 20071106 | Candidate remains visibly truncated at its right/lower sides. | Known failure; do not use. |
| 20120417 | Left edge is relocated from the prior incorrect page edge to the grid-envelope-side candidate. | Owner review required. |

## Interpretation

The lattice envelope is a useful non-damage initializer: it removed the specific 2003 tiny-box failure, emitted a candidate for 1998, and changed the 2012 left-side candidate. It is not a usable universal frame-range method: it retains the known 2001 baseline failure, fails 2007, and regresses 1991's bottom range. Consequently it is quarantined as an exploratory candidate generator pending human review, not promoted to cropping or registration.

## Evidence

The immutable local package is `local_archive/real_road_acquisition/ltpp_06_1253_lattice_envelope_frame_range_mvp_20260810/`, with full-resolution purple-frame reviews, overview, metric table, input/code SHA-256 receipt, manifest, and decision note.
