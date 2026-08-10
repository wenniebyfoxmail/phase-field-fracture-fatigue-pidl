# External review — LTPP frame-candidate-review MVP v3, 2026-08-10

## Verdict

`REVISE`

## Accepted scope

The reviewer accepts the proposed candidate-generator-plus-frozen-human-review
workflow as a development-only engineering MVP. It neither disguises human
judgement as independent ground truth nor opens a registration claim, provided
that it cannot move candidate geometry or create a third candidate.

## Sole blocking issue

The initial checklist did not deterministically map its four answers to
`accept/reject/uncertain`, leaving a residual visual-preference degree of
freedom.

The required minimal revision is:

```text
Each item: YES / NO / UNCERTAIN.
ACCEPT iff first three items are YES and range-error item is NO.
REJECT iff any first-three item is NO or range-error item is YES.
UNCERTAIN otherwise.

Score A and B independently before comparison.
Exactly one ACCEPT => date candidate.
Zero ACCEPT => fail closed.
Two different ACCEPT candidates => fail closed as ambiguous.
Two identical accepted geometries => one candidate, retaining both provenance records.
```

No additional algorithm, generator, or historical-heuristic change is needed.
Once this mapping is frozen and the matching synthetic assertions exist, the
reviewer considers the MVP eligible for approval. Even an eight-date accepted
packet remains an engineering page-canvas result, not spatial registration or
independent control evidence.
