# Minimum next validation — frozen-model inference replay (proposal only)

2026-10-15. Human-requested proposal following accepted E021 evidence review.
NOT IMPLEMENTED / NOT EXECUTED / NO FITTING OR CONFIRMATION AUTHORITY.

## Decision and question

Prefer one no-refit replay audit before another model/feature/loss experiment.
Question:do the four frozen outer models reproduce their saved357cycle
physical-error/range records when inferred over every admitted cell, with
unchanged training-owned scales and admissible outputs?
This directly addresses the audit's unreplayed-prediction limitation. It is
an engineering/evidence-integrity check (C0/C1), not a fresh scientific gain
test, late-regime repair, uncertainty estimate or generalisation evaluation.
E021's result remains closed; this proposal does not add a new primary gate.

## Data roles and only comparison

- Read ONLY already-admitted four development prefixes and fixed85112-cell
  mapping under the same paired lock; no new exports, remapping or states.
- Read frozen R001 outer models.json, selection.json, percycle.csv, folds.csv,
  decision.json and fixed U0.115/C20 snapshot. Coefficients, h/r, normalizers
  and selected alpha are immutable inputs. No refit/re-estimation/selection.
- Reconstruct V0 and the saved outer V1 from causal PIN inputs with those
  stored quantities; FEM is scoring reference only. All357cycles/full admitted
  support, not a selected favourable subset. No inner fit or hyperparameter grid.
- Compare replay to original saved metrics; at C20 compare against its saved
  full fields. Other cycles have NO original full prediction field saved:
  replay can check full-domain bounds and aggregate reproducibility there,
  but cannot retrospectively establish pointwise equality to an unsaved field.
- U0.1175/U0.125 remain closed. No future/event-derived deployment inputs,
  NN/MOO/shared representation, process-zone qualification or coupled feedback.

## Proposed arithmetic and outcome rules (freeze before real replay)

Use float64 independent scalar prediction reconstruction from stored
coefficients/means/std and fixed final maps, not a solver or the production
fit function. Reuse the approved input/feature contract, but separately test
the reconstruction algebra with generated fixtures. Stream one cycle at a
time; do not retain the full predicted trajectory.

1. Exact checks:source/run/model/state/support identity;357orderedrows/four
   groups; finite intermediates; d∈[0,1],ab/raw>=0; V1.d/ab=V0.d/ab; frozen
   alpha/normalizers unchanged. Any failure stops as integrity/numerical failure.
2. Proposed percycle MSE comparison:
   abs(replay-saved)<=1e-10+1e-10*abs(saved), in squared raw archive units.
   Fixed C20 field comparison uses the same mixed numeric bound in raw units.
3. Aggregate R/G/Q abs difference<=1e-12, with the original exact directional
   classification unchanged. Do not relax E021 eps or turn a mismatch into V0.
4. These are proposed arithmetic-reproduction tolerances, not physical margins.
   Justification:float64 independent summation/reconstruction, prior local/
   independent saved-table differences ~1e-16, and a margin orders below the
   observed3.26% weakest gain. Before approval for real replay, generated-only
   unequal weights/constants/cancellation/projection cases must substantiate
   these values. If they do not, stop for review before real data; never tune
   a tolerance after seeing replay error to force agreement. Not bitwise equality.
5. Preserve and reconfirm the U0.11 late1.6083% increase; replay agreement does
   not erase it. A passing audit supports only frozen-model/output arithmetic
   consistency. Mismatch→diagnose implementation/storage lineage, no automatic
   refit/recovery. No claim rescue or method parameter update in either branch.

## Proposed one-attempt budget and outputs

Mac CPU4/noGPU; <=300s joint load/inference/check/report, <=2GiB attributed
sampled RSS, <=100MiB generated outputs/logs/receipts. Fresh attempt identity
and paths fixed later, one invocation only, no retry/resume/budget increase.
Caps use an explicitly reviewed monitor; sampled RSS is not a hard OS limit.
No full resource benchmark requested now; resource adequacy remains to review
for the actual inference-only implementation.

Minimum outputs:357-row comparison/range table, four-fold aggregate differences,
fixed C20 field-difference maxima, outcome/identity/terminal receipt, and one
compact decision visualization from those saved comparisons. Numerical tables
authoritative; no new FEM/PINN field export or full prediction archive.
Any missing source/evidence, nonfinite value or cap stops/freezes inconclusively;
successful process exit alone does not certify reproduction.

## Staged authority and sole owner

This turn only prepares this document. Next permitted action needs user approval
to implement a minimal no-fit runner and generated-fixture tests, then obtain
exact independent code review. Actual replay needs its own fresh identity/run
card and separate explicit execution approval. Do NOT invoke s04_raw_guard.py
for this proposal:its real entry launches fitting. Any new inference monitor
must be reviewed as such; existing fit approval cannot be reused.

Main chat sole implementation/record owner. Method chat read-only review only;
coordination chat not triggered. No actual fields decoded or predictions replayed
in proposal preparation. No source/model/evaluation code changed, and no new
execution approval artifact created. Follow-on scientific/confirmation validation
requires a separate design decision even if this engineering audit passes.
