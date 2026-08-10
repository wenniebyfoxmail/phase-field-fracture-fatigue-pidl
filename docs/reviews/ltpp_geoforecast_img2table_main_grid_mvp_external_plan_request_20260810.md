# External planning request — LTPP main-grid outer-frame MVP, 2026-08-10

## Requested decision

Please assess whether the following is an acceptable *tooling-only, exploratory* diagnostic. Requested verdict: `APPROVE_TOOLING_MVP`, `REVISE`, or `REJECT`. This does not request a v2 final-gate run, transform tuning, or a 2-D-model authorization.

## Context

Two prior full-page frame heuristics were run and owner-reviewed. The fixed solid-frame rule was rejected on 2001 (missed `y=0–0.5 m`), 2003, 2007, and 2012. A separate lattice-envelope rule corrected 2012 but still failed 1991, 2001, and 2007; the owner also rejected its 2003 candidate. These completed results remain immutable.

## Proposed one-run MVP

Use the open-source `img2table` package in its OpenCV-only mode with OCR disabled. On each original official 0–50 ft white-composited page:

1. extract every bordered-table/grid candidate from visible horizontal and vertical printed strokes;
2. exclude candidate selection inputs derived from cracks, distress/WIM/repair marks, handwritten annotations, OCR text, or manual corners;
3. choose one candidate only by a frozen geometric rule based on its connected ruled-cell graph: largest number of regular row/column separators, then largest candidate area, then a fixed physical road-frame aspect admissibility check;
4. obtain four corners solely by intersecting that candidate's outermost horizontal and vertical separators;
5. emit `NO_CANDIDATE` for ties, incomplete outer separators, or any candidate failing the frozen structure rule;
6. produce purple candidate overlays and metrics only. No crop, control extraction, transform fitting, residual calculation, or final gate is permitted.

All eight pages are development-only because prior visual results have been seen. No outcome can establish independent validation or alter `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## Reviewer questions

1. Is OpenCV table/grid extraction without OCR an acceptable non-damage source for this tooling-only MVP?
2. What deterministic candidate score/tie rule and synthetic tests must be frozen before its one run?
3. Are the listed fail-closed conditions sufficient to prevent selecting an internal distress rectangle or side summary table?
4. Confirm that any visually improved candidate remains outside the v2 final-control and registration-gate path.
