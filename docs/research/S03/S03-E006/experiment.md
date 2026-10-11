---
storyline_id: S03
experiment_id: S03-E006
protocol_revision: v1
status: run_complete_evidence_review_pending
scientific_verdict: pending
research_disposition: repair
---

# AA2024 qualification with the observed commented-header grammar

Claim: C1 evidence-validity, controlled-experiment data. Question: can the
actual locked global-DIC sequence be admitted under a header grammar that
supports the commented schema observed in S03-E005?

S03-E004 remains inconclusive. This new experiment changes the grammar after
one header was observed; it is qualification/development work, not a holdout
test. It evaluates all discovered paired stages in the same immutable archive
(1,248,078,255 bytes, MD5 e671b804e29401e70043bc1e17f66dd1).

Reuse S03-E004 discovery, identity, field, exact Decimal comparison,
chronology, variation and normalized spatial-schema requirements. Each is
needed to admit a mechanics/time-indexed sequence. Advertised 797 counts and
mapping names are not criteria. No prediction or inverse task is evaluated.

## Header grammar and reading boundary

Comments provide scalar metadata. A semicolon-separated comment whose first
normalized token is exactly `id` is a schema candidate. Require all frozen
spatial tokens, unique normalized tokens, and exactly one candidate if this
form is used. Incomplete or multiple candidates are parser failures. Continue
through comments: a subsequent non-comment column line must match the candidate
exactly after existing normalization. A conflicting line cannot be concealed.
When the first numeric-prefix byte is reached after a complete candidate,
terminate successfully with that schema; do not consume a complete numeric row.
Without a candidate the numeric-prefix boundary still fails. Unsupported
leading bytes, decoding errors and the 131,072-byte consumption cap always
fail. EOF after a commented candidate without a column/numeric boundary fails.

Stop before opening the next member at the first decisive stage failure.
Connections are paired from directory metadata only and never opened.
Internal decompression buffering is outside the parser-consumption guarantee.

## Result interpretation

Primary criterion: all inherited admission clauses pass together. A pass
permits only design of a separately reviewed observation-only transition task.
Parser/identity failures are inconclusive; established pairing, stage,
chronology, schema or variation violations block the bounded contract.

New component statuses explicitly distinguish `passed`,
`demonstrated_violation`, `not_assessed` and `inconclusive`. Aggregate flags
remain for compatibility; false flags alone must not be read as a demonstrated
defect. Components do not rescue the primary verdict, but select a repair.
Development diagnosis on stage 7 supports feasibility of the format adaptation;
full sequence field/value consistency is unknown before execution.

Budget: one all-stage header-only qualification run after exact Code Ready
review. Output root: `local_archive/experiments/S03-E006/runs/S03-E006-R001/`.
Record output, command/identity receipt, compact component decision table,
independent evidence review and Storyline impact. No numeric rows, connection
bodies, learning, physical fit or threshold sweep. On a miss preserve the
component results and select the earliest controllable bottleneck.

Blocked claims: forecasting skill, phase-field recovery, material identification,
fatigue-law truth, independent-specimen generalisation and road transfer.

## Code review history

Commit `1a0bc9e82b962922e8a9275d2ea311553824768e` received `REVISE_CODE`:
incomplete ID parsing could label derived count/set defects as demonstrated.
The revision suppresses dependent count/set checks after ID parse failure and
preserves independently observed duplicate IDs and unsafe-member violations.
Full-audit regressions cover entirely unparsed pairs, partial parsing and an
independently observed duplicate alongside an unparseable ID. No real run has
occurred. Separate per-component coverage accounting remains a future reporting
improvement; current upstream states on later failures are conservative.

Commit `524919b877b85b243b3a18e81af6f50114d193c9` received
`PASS_CODE_READY` after the reviewer reproduced closure of that blocker.
R001 executed at 2026-10-11T22:20:17Z; identity and 342-stage pairing passed.
The commented-schema parsing repair crossed the old failure, but the new
gate stopped with `CHRONOLOGY_INVALID`. Output hash:
`3da9749f97fa889b533b650bb7e9352f2a081eadcf50f1ecb92a8560ba16908a`.
Separate bounded diagnostics locate the first decrease in the `time` signal
at stage 21 -> 22, while cycles and acquisition-relative date increase.
See `chronology_diagnostic.md`; timer-reset semantics remain a hypothesis.
Closure is pending independent evidence review. Proposed disposition: repair
by testing an explicitly justified prediction index in a new experiment.
