---
storyline_id: S03
experiment_id: S03-E011
protocol_revision: v1
status: code_review_pending
scientific_verdict: pending
research_disposition: repair
---

# AA2024 cycle/date-indexed observation admission

Question: does the actual locked sequence provide an internally auditable
cycle progression and acquisition order suitable for designing an observation-
only cycle-to-crack-length forecasting task? Claim class C1, controlled-
experiment development evidence. No forecast or physical identification is
performed here. This is a new contract after S03-E006, not its rescued verdict.

S03-E011 was selected after checking other worktrees: S03-E007 through E010
are already used elsewhere. Prior AA2024 E005/E006 references refer specifically
to the `aa2024-value-blind-audit` worktree and its recorded exact commits;
their historical IDs are preserved rather than silently renamed.

## Task and criteria rationale

The candidate later target is crack-length change over additional loading
cycles, using only observations available at a prediction origin. That task
needs consistent cycle progression and acquisition ordering. It does not
necessarily need a globally monotonic auxiliary sensor `time` signal. E006
showed a time decrease at a pair with increasing cycles/date; its semantics
remain unknown. This motivates testing a different index, not asserting a
timer reset or smoothing/reordering the data.

This admission is structural, not complete task readiness: units, specimen
identity, sensor/label semantics, noise, reference registration, train/test
split and baselines must be addressed in a separate forecast design.

## Frozen evidence and primary admission criterion

Same immutable ZIP: 1,248,078,255 bytes, MD5
`e671b804e29401e70043bc1e17f66dd1`. All discovered paired global stages in
ascending numeric-ID order; no exclusions or silent joins. Observed 342 is not
a CLI expected-count override. Reuse reviewed E006 identity/path/member,
pairing, commented-schema, finite Decimal and per-stage stop safeguards.

One necessary conjunction: safe complete one-to-one stage pairing; complete
finite fields and exact filename/header stage identity; stable required spatial
schema; nondecreasing `cycles` and `current_stage_relative_date`; at least two
distinct cycles and crack lengths. Nondecreasing admits tied acquisitions;
repeated stages do not become independent units or imply positive cycle
horizons. No monotonic crack-growth rule is imposed. The finite `time` field
is retained for diagnostics, but monotonic `time` is not an admission clause.
No threshold tuning, sorting by measured cycles, tolerances, imputation or
interpolation. Criterion feasibility is unknown across the full sequence;
existing prefix evidence establishes parse feasibility and variation only.

Stop at first decisive primary failure; variation is assessed only after full
accepted coverage. Budget: one bounded all-stage run after exact independent
Code Ready review, at most 131,072 parser bytes per header, numeric-prefix
stopping, zero complete numerical rows and no connection-member opens.

## Progress and repair reporting

Record separate counts for parsed headers, complete fields, valid stage
identity, stable valid schema and valid cycle/date order. Completed upstream
checks may pass even if a later component fails. Incomplete checks remain
unassessed or inconclusive. Variation requires full accepted coverage.
Report `time` adjacent comparisons, decreasing-pair count and coverage; do not
infer a reset, session boundary or valid elapsed-time horizon from these counts.
These diagnostics do not vote on admission.

Pass -> structural cycle/date index may enter separate observation-forecast
design. Parser/identity failure -> qualification unestablished. Demonstrated
primary violation -> negative for this bounded contract, selecting earliest
controllable repair. Unknown sensor semantics may still prevent forecasting.
No specimen/road generalisation, fatigue-law truth, phase-field recovery,
material inversion or prediction skill follows.

Run root: `local_archive/experiments/S03-E011/runs/S03-E011-R001/`.
Minimum evidence: output, execution receipt, compact decision/coverage table,
independent evidence review and dated Storyline impact. This non-numerical C1
admission has no applicable model/comparator performance plot.
