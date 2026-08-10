# External review request — LTPP frame-range amendment candidate, 2026-08-10

## Requested decision

Please return `APPROVE_FOR_EXPLORATORY_DEVELOPMENT`, `REVISE`, or `REJECT` for a *new*, exploratory frame-range protocol. This is not a request to re-open v1 or approve a v2 final registration audit.

## Triggering evidence

The completed frozen outer-solid-rectangle inventory was owner-reviewed as follows:

- `19910610`: accepted as an engineering range reference, with small visible deviations retained.
- `20010913`: rejected because the lower frame begins at `y=0.5 m`, omitting `y=0–0.5 m`.
- `20030514`, `20071106`: rejected because the overall selected range is wrong.
- `20120417`: rejected because the left boundary is wrong.
- `19980407`: no candidate under the frozen rule.
- `19951024`, `19970228`: awaiting owner review.

This demonstrates that a solid-ink/aspect rectangle may select internal horizontal or vertical structures, including summary-table/page geometry, rather than the enclosing road-coordinate frame.

## Proposed amendment scope

The next method may use only printed, non-damage coordinate-carrier evidence: road-frame border strokes, printed coordinate ticks/axis labels, and regular printed grid lines. It must not use cracks, WIM/repair boxes, handwritten annotations, or any distress label.

It will be a new dated experiment with a new output root. The old inventory and all of its accept/reject decisions remain immutable.

## Questions for the reviewer

1. Is it methodologically acceptable to require a candidate frame to be supported jointly by (a) a surrounding printed border/grid geometry and (b) its printed coordinate-axis/tick endpoints, rather than solid-stroke continuity alone?
2. What deterministic, predeclared fail-closed rule should distinguish the outer road-coordinate frame from internal grid/summary structures when either component is absent?
3. Are the following protections sufficient for exploratory development: all current pages are development-only; all user-reviewed failures remain in the development record; no candidate can become a v2 final control or a registration gate input; and no per-date fallback/manual adjustment is allowed?
4. What minimum visual evidence and synthetic test cases must be frozen before the amended detector is executed once across all eight pages?

## Immutable constraints

- Preserve v1: `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.
- Do not run a transform, use crack geometry, extract final controls, or conduct a final gate.
- Do not tune current rule thresholds or replace failed outputs.
- A new method remains `EXPLORATORY_REGISTRATION_IMPROVEMENT` unless an independent v2 protocol and final controls later exist.

## Requested minimum response

State whether the proposal is approved/revise/rejected; list any blocking protocol defects; and specify the exact evidence split and one-shot stop condition required before execution.
