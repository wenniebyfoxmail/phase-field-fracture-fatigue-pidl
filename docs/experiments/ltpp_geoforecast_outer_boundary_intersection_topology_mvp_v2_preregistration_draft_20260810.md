# LTPP outer-boundary / intersection-topology MVP v2 — preregistration draft, 2026-08-10

## Independent status

`EXPLORATORY_REGISTRATION_IMPROVEMENT__DRAFT_PENDING_EXTERNAL_REVIEW`

This is a new, independently named tooling experiment. It does not continue, alter, or rescue either the v1 spatial-registration audit or the completed no-OCR complete-main-grid MVP. The latter remains `EXPLORATORY_MAIN_GRID_TOOLING_MVP__NOT_QUALIFIED`; v1 remains `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## Mechanism question

Can the four outer printed road-frame sides be detected as a rectangle first, and then supported by local printed-grid intersections, without requiring the complete dashed grid to survive as one connected `11 x 6` table component?

## Motivation and non-use of failed output

The preceding complete-lattice MVP was deliberately stricter: it required one connected `11 x 6`, 66-intersection component. It returned `NO_CANDIDATE` on every seen development page, so its numerical parameters may not be loosened and rerun. The new hypothesis is architecturally different: outer-frame topology comes before interior-grid connectivity. It does not use any preceding candidate, owner verdict, crack overlay, or result geometry as input.

## Permitted and prohibited evidence

- Permitted: original official white-composited pixels; visible non-semantic printed horizontal/vertical strokes; the known physical frame aspect ratio `15.24 / 5.00`.
- Prohibited: cracks, crack labels, distress/WIM/repair marks, hand-written or printed text meaning, OCR, old overlays, manual corners, cross-date transfer, transform fitting, residuals, and candidate adjustment from visual review.

## Proposed frozen logical form (numbers await external review)

1. Detect source-pixel horizontal and vertical printed-stroke primitives only; OCR and semantic layout classification are absent.
2. Build horizontal and vertical *side candidates* from collinear primitives under a predeclared, finite gap/coverage rule. This is permitted only for a candidate side, never as a gridline or rectangle completion.
3. Form a rectangle candidate only from four observed side candidates. Its four corners are their line intersections; no corner extrapolation is permitted.
4. Require the fixed physical aspect ratio within a predeclared tolerance, ordered sides, source bounds, and a predeclared minimum long-side/short-side coverage for every outer side.
5. Validate a rectangle locally: observed grid/tick crossings must occur along each side according to a predeclared count and distribution rule. An unconnected dashed interior grid is not required to form one table component.
6. Rank only eligible rectangles by a frozen lexicographic tuple and return `NO_CANDIDATE__FAIL_CLOSED` for zero eligible candidates or an exact quantised tie.
7. Emit purple frame / observed intersection dots / structural metrics only. No crop, controls, registration transform, or qualification result is produced.

## Required review questions

Before code or real image execution, external review must fix the primitive detector, gap/coverage definition, local-crossing rule, exact rank/tie tuple, synthetic adversarial suite, and evidence-package requirements. It must specifically test that a side summary, text underlines, long crack-like lines, WIM/repair rectangles, and a page border cannot become a selected road frame merely because they form a rectangle.

## PIDL Experiment Gate

- Mechanism question: whether outer-frame-first geometry avoids the known disconnected-dashed-grid failure without semantic damage information.
- Claim changed if success: only development-page feasibility of this distinct boundary-topology recipe.
- Claim changed if failure: this v2 recipe is quarantined; v1 and v2 final-gate status are unchanged.
- Cheaper diagnostic first: reviewed synthetic drawings with page-border, summary, rectangle, underline, and fragmented-grid adversaries.
- Minimal output asset: purple-frame plus observed-boundary-intersection review panels and per-date structural metrics.
- Code/producer alignment: local deterministic image diagnostic; no training.
- Success/failure criteria: frozen only after external approval; real run is one development-only execution, with `NO_CANDIDATE` preserved.
- Registry destination: spatial-registration track.
- Decision: await external plan review; do not execute code or real images.
