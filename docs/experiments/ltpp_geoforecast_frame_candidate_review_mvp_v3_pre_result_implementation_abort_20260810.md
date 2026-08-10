# LTPP frame-candidate-review MVP v3 — pre-result implementation abort, 2026-08-10

The owner-confirmed checklist finalizer created a new output directory but
aborted while writing `canonical_owner_submission.csv`. The special `19980407-A`
`NO_CANDIDATE` row introduced four fields absent from the other rows, so the
CSV writer rejected its non-uniform schema. No per-date decision, result JSON,
decision note, visual decision board, or manifest was produced; the partial
directory is retained as an aborted implementation artifact.

The repair removes those output-only fields and treats two accepted named A/B
sources conservatively as distinct (therefore ambiguous), because v3 does not
carry editable geometry fields. It does not alter a submitted answer, a
candidate image, candidate source, checklist mapping, or date-level fail-closed
rule. A regression assertion locks the uniform row schema. A separately named
post-repair output directory will be used only after the test passes.
