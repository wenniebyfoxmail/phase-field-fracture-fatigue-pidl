# External review — LTPP main-grid tooling MVP, 2026-08-10

## Verdict

`REVISE_TOOLING_MVP_BEFORE_RUN`

The external method reviewer accepted the claim boundary: visible printed ruled geometry is a permissible non-damage input for a *tooling-only* development diagnostic, and the MVP remains outside all v2 final-control, final-gate, transform-fitting, and 2-D-model paths.

The reviewer did **not** authorize a real eight-page run. The existing v1 result remains `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## Required revisions before the one real-data run

1. Pin the exact `img2table` version/artifact, OpenCV version, no-OCR entrypoint, input, and every processing parameter. The public extraction API must not be described ambiguously as “OCR disabled”: either prove it yields the required geometry without OCR or name the internal geometry-only routine explicitly.
2. Replace the informal “most separators, then area, then aspect” wording with a deterministic eligibility gate, lexicographic ranking, frozen quantisation, and exact-tie `NO_CANDIDATE` rule.
3. Make the road aspect and lattice completeness/regularity hard eligibility gates, rather than late tie-breakers. A side summary table or a collection of disconnected rectangles must fail closed.
4. Pass a frozen synthetic adversarial suite before the one real eight-page development-only run.

## Adopted scope

The revision will use the exact geometry-only internal routine
`img2table.tables.bordered.lines.identify_straight_lines`, rather than the OCR-dependent public `Image.extract_tables` path. This uses no OCR object, text content, borderless-table detection, implicit row/column inference, manual corner, crack, WIM, repair, or distress feature.

This adoption is not yet external approval. The revised protocol requires re-review before any image from the eight official dates is processed.

## External-review record

The reviewer’s decision was obtained in the named ChatGPT external-review conversation on 2026-08-10. This file records the decision and adopted constraints; it is not a new experimental result.
