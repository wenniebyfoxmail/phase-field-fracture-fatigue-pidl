# LTPP lattice-envelope frame-range MVP preregistration — 2026-08-10

## Status and claim boundary

`EXPLORATORY_REGISTRATION_IMPROVEMENT__NOT_QUALIFIED`

This is a post-owner-review engineering diagnostic. It cannot revise the completed outer-solid inventory, alter v1, create v2 controls, fit a transform, or authorize a 2-D model.

## Mechanism question

Can a road-frame candidate supported by the largest regular printed-grid lattice, with border strokes searched only near the lattice endpoints, avoid the known failure mode where a global solid-stroke/aspect heuristic selects an internal line or page-summary structure?

## Frozen sources and roles

The original official `segment_0_50_white.png` page is used for all eight v1 dates. All eight pages are development-only because the earlier reviews were already visible to the implementer. There is no independent validation set and no success claim of any kind.

## Frozen non-damage evidence

Permitted: deskew orientation, darkness of printed grid/border strokes, regular line spacing, and page geometry. Prohibited: crack geometry, crack labels, WIM/repair boxes, handwritten notes, side-table content, or manually supplied corners.

## Frozen algorithm

1. Reuse the native printed-grid MVP's fixed deskew and periodic pitch/phase extraction.
2. Within each direction's phase-compatible positions, select the longest run whose adjacent gap is no more than `1.65 × pitch`.
3. Permit exactly one preceding position across a gap in `[1.65, 2.35] × pitch`, to bridge one missing printed gridline; no other extrapolation or per-date fallback is allowed.
4. Treat the run endpoints as provisional frame anchors. Within a fixed `1.10 × pitch` window around each anchor, select the strongest continuous orthogonal dark-stroke support. This search may snap to a printed border but cannot inspect cracks.
5. Emit `NO_CANDIDATE__FAIL_CLOSED` unless both axes have at least six run positions, the four snapped sides are ordered, and the resulting aspect lies in `[2.5, 4.0]`.

## Output and review

The one run will write a full-resolution purple-frame review per date, a contact sheet, all lattice and snap metrics, SHA-256 receipts, and an immutable manifest. The visual question is only whether purple encloses the printed road coordinate grid, including the `y=0` baseline, while excluding page summaries.

## PIDL Experiment Gate

- Mechanism question: whether lattice support prevents internal-frame selection.
- Claim changed if success: only the feasibility of a later engineering range diagnostic.
- Claim changed if failure: this lattice-envelope variant is quarantined.
- Cheaper diagnostic first: existing lattice evidence and full-resolution owner review.
- Minimal output asset: eight-panel purple-frame review and per-date range table.
- Code/producer alignment: deterministic local image analysis; no training.
- Success criteria: a candidate is available for visual review; no registration criterion is evaluated.
- Failure criteria: missing lattice support, invalid geometry, or owner-rejected frame.
- Registry destination: spatial-registration track.
- Decision: run one exploratory diagnostic only.
