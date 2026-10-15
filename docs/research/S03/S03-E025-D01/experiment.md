# S03-E025-D01 — historical-input conditional-query replay

2026-10-15; primary Storyline S03; protocol `conditional-interface-v1`.
Claim class C1/software information flow; controlled-experiment, already-viewed
development data. Base b53537128ccf34cd910ec5479d30a234152ba60d,
branch codex/crackmnist-tokenizer-mvp. User explicitly authorises implementation,
independent review and one replay of eight cases, figures and Obsidian sync.

## Question and fixed scope

Can a history-only typed predictor interface separate origin eligibility E from
post-output reference measurability R, with full coverage accounting, while
retaining the original half-depth observable and persistence/secant outputs?

Use only `../d01_conditional_query_cases_v1.json`: 8 cases, 12 transects each,
14 stages of beams4/5/6. Last two observed widths/nominal loads at k-1,k;
explicitly supplied nominal L*>L_k>L_(k-1). This is retrospective conditional
query, not proof of load knowledge at the historical origin. Origin is an
observation cutoff, not an asserted wall-clock timestamp. No final stages,
new pixels, downloads, sealed data, new registration, fitting, training or FEM.
Old E015–E024 are immutable. Fixed first-frame geometry and cached E015
five-line-median gray-profile half-depth widths, native first-frame px per beam.
Same transect ID means registered coordinates, not proven material identity.

## Information boundary and references

Read existing CSV through row-key projection, not new image measurement. A
history packet contains two selected records only, source IDs/loads, fixed
origin qualification and L*. Predictor receives a frozen typed packet, never
ledger, target row, transform, future validity or posthoc E024 classification.
E uses historic validity, finite widths, identity/unit/definition and load order;
query validity Q separately requires finite L*>L_k. No physical-plan proof gate.
Call the unchanged E015 `forecast` for persistence and secant with clip[0,120].
Save all96 input/E/Q/arm outputs or failure reasons before evaluation target
loader is called. Only then evaluate exact listed target identity and R.
No substitution, zero imputation or filtered-out difficult transects.

The underlying CSV is an already-viewed full-sequence cache. Scanning it reads
future rows as bytes/strings; projection does not constitute OS/process isolation,
new blind data or a prospective ingestion pipeline. The guaranteed boundary is
fields passed to E/predictor and the order of **evaluation** target decoding.
Earlier targets may legitimately be later cases' observed histories. Geometry
is E015-R000; E012's stage H was generated from that stage and first frame only
(`d01_stage_forecast_diagnostic.py:150–174`), not future-refitted H. Cached
measurement provenance is audited, not remeasured or physically validated here.

## Single primary criterion and descriptive comparison

Primary C1 acceptance: target mutation/removal cannot change E/Q/predictions;
evaluation target loader cannot be called before the immutable prediction file
exists; loss/coverage accounting follows the frozen contract. Synthetic tests
exercise these necessities. Replay consistency is checked against every old
two-arm per-transect output/reference/error, with max absolute deviation<=1e-12px
(floating-point/software tolerance, not a physical tolerance). A replay mismatch
stops interpretation until diagnosed; do not tune the formula to recover scores.
This is attainable because formulas, float64 values and row identities are
unchanged; no scientific improvement threshold is imposed on viewed cases.

Scientific comparison remains descriptive: common C=E&Q&R&P_persistence&P_secant;
transect MAE -> case -> beam equal weights, delta=secant-persistence (negative
better). All3 beams required for equal-beam overall value. Missing case MAE is
null, not0; a wholly unscored beam makes overall null, not reweighted2-beam MAE.
N=12/case, E, E&Q, each arm attempts/successes/failures, R on E&Q, C;
all failure reasons plus mutually-exclusive terminal categories summing to N.
Auxiliary half-secant is not rerun: not needed for this primary two-arm contract.

## Budget, repair map and minimum evidence

One Mac CPU replay on existing tables (60s wall cap expectation; no GPU).
Synthetic tests and independent read-only code review before real replay.
Fresh run `S03-E025-D01-R001` in parent local_archive/experiments/S03-E025-D01/runs/;
clean code commit, command/python/host/PID/start/end/wall/CPU, inputs and output
paths in receipt. Renderer separately operates only saved scored outputs.
Stop for source/duplicate-key/load/unit mismatch or unexpected case/stage
identity, unreviewed material changes, or comparison mismatch. Ordinary missing
historical/target data or an arm exception is accounted for, not silently removed.

Minimum evidence: all96 prediction snapshots, evaluated rows, per-case coverage
and MAE, per-beam/overall summary, old-value comparison, receipt, independent
code and evidence review; all8-case reference/prediction and error small multiples,
paired case-MAE decision plot and coverage figure, README_analysis and visible QA.
Display all cases in ledger order, every transect, no posthoc priority subset.
These are diagnostic user-facing figures, not a venue-specific submission.

If interface tests fail -> repair boundary/accounting before replay. If numeric
replay differs -> inspect mapping/serialization/formula, preserve outputs and stop.
If unchanged -> supports software replay integrity only. Descriptive secant
advantage is old development evidence, not newly independent validation.
If case-specific errors persist -> retain and locate them; no target/operator
change or new model in this Experiment. Physical metrology, new-beam/road
generalisation, confidence intervals, causal load response and autonomous
next-observation prediction remain blocked conclusions.

Registration status: prepared, pending implementation tests and independent code review.

## 2026-10-15 outcome and disposition

Execution succeeded; retrieval verified local. Primary C1 software-interface
criterion supported within fixed cached-data replay.15 synthetic tests passed
independently; code reviewed before execution at b3126c42ccbce7809e259afc55eb1ecf6cf4bd25.
Independent reviewer hand-reimplemented both formulas from E015 source rows,
without calling new forecast/replay/summarize: all192 method predictions,
references and errors agree exactly with both source calculation and old CSV.
Maximum deviation0. No new physical or C3 generalisation verdict.

R001:96 nominal opportunities,96 E,96 E&Q,96 R and96 C; each method96 attempts,
96 successes,0 failures. Every case retains12/12, no abstentions/reference loss.
This is availability of this selected archive, not guaranteed field coverage.
Case->beam->equal-beam MAE P0.9234534818541653, S0.4394862658468068px;
delta-0.48396721600735854px (relative52.4084023% lower).7/8 case MAEs favor
secant; B4/40->50 has P0.7526518832 vs S0.7551995544px. Old results unchanged.

Numerical run wall0.051591s CPU0.039184s. R002 rendering succeeded but F03
title/summary overlapped; retained, superseded for display. Renderer-only
reviewed repair516cf9b2fe103f119196c9cd844be7a9efa0afe1 produced R003, wall3.137984s,
CPU3.124891s. No second prediction run. Final4 PNG/PDF/grayscale figure sets
and guide at:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E025-D01/runs/S03-E025-D01-R003/analysis/README_analysis.md`.

Figure choice followed cached-output profiling (8 cases×22 columns, no missing
summary fields; beam groups2/4/2 are not independent case samples). Show all
points and paired case means, no significance bars/CI or smoothed spatial curve.
Programmatic layout reports empty; all colour PNGs strict300dpi checks pass.
Independent reviewer opened all4 plus grayscale; F03 repair verified. PDF
checker font WARN separately checked using pdffonts (embedded CID TrueType yes).

Minimum evidence and independent review complete; compact tables/receipts in
evidence/ and runs/. Disposition: advance interface reuse for bounded developer
queries; retain old half-depth measurement and simple baseline. No training.
Diagnostic next proposal: inspect B4 T1's30/40/50kN widths15.2524483 ->
11.5099414 ->13.8340226px (secant50kN7.7674345, error6.0665881px) against
existing same-coordinate profiles/images to separate local measurement/
correspondence effects from two-point trend reversal. This is posthoc problem
localisation, not case exclusion, altered scoring or new holdout; not executed.
E024 T7/T9 fractional-position proposal remains separate and unexecuted.
