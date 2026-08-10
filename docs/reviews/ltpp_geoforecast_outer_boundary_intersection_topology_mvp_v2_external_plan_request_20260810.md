# External plan request — LTPP outer-boundary / intersection-topology MVP v2, 2026-08-10

## Requested decision

Please return `APPROVE`, `REVISE`, or `REJECT` for a **new tooling-only development diagnostic**. Do not evaluate a registration result, reopen v1/v2 final controls, or authorize any crop, transform, residual, final gate, or 2-D model.

## Context

The previously reviewed complete-lattice no-OCR MVP required one connected `11 x 6`, 66-intersection component. Its synthetic adversarial suite passed, but all eight already-seen official development pages returned `NO_CANDIDATE`; printed dashed strokes and scan fragmentation did not yield one component. That negative result is complete and will not be tuned or rerun.

The user’s separate, pre-existing engineering proposal is: **find the four outer printed road-frame sides first; then verify intersections along them**, instead of demanding a full connected grid/table.

## Proposed v2 logical boundary

1. Use only source pixels and non-semantic horizontal/vertical printed-stroke geometry; no OCR, text semantics, cracks, WIM/repair/distress features, manual corners, old overlays, or cross-date information.
2. Build side candidates from observed collinear primitives using a frozen finite gap/coverage rule; form a rectangle only from four observed sides, and derive corners mechanically from their intersections.
3. Require hard eligibility: ordered in-bounds rectangle; physical aspect near `15.24/5.00`; all four sides have defined observed coverage; a fixed local crossing distribution along every side; no inferred side or corner.
4. Rank eligible rectangles by a unique, quantised lexicographic tuple; exact tie or failure of any side/crossing condition is `NO_CANDIDATE__FAIL_CLOSED`.
5. Output only purple rectangle, observed side/intersection evidence, and structural metrics. All eight pages remain development-only. No result can become a v2 control or final evidence.

## Request for exact review guidance

1. Is outer-frame-first plus local intersection validation a genuinely distinct, permissible no-damage tooling hypothesis rather than a disguised relaxation of the failed full-grid method?
2. What exact primitive detector, gap/coverage rule, local-crossing distribution, aspect tolerance, ranking/tie rule, and quantisation should be frozen before the first synthetic or real run?
3. Which synthetic fixtures are essential to prove fail-closed behavior against page borders, side summaries, text underlines, long crack-like lines, WIM/repair rectangles, fragmented dashed frames, incomplete sides, and ties?
4. Confirm that even an 8/8 visually good output can only be `EXPLORATORY_REGISTRATION_IMPROVEMENT__NOT_QUALIFIED`, not registration qualification.
