# S04 FEM / PIDL fixed-state field alignment track

Purpose: improve PIDL agreement with the existing FEM numerical comparator while separating initialization, optimizer path and physical feasibility. This track continues the existing S04-E011 diagnostics; it does not replace the frozen native-Q4/T3 trajectory protocol or qualify FEM as physical truth.

Authoritative scientific protocol and dated amendments: [S04-E011 experiment](../research/S04/S04-E011/experiment.md). Earlier physical-u/v, precrack A/B/C and weight designs retain their source records; no old result is overwritten.


## Current goal anchor — user-directed method redesign (2026-10-19)

The goal remains substantive PIDL/FEM field agreement. The user explicitly redirects the primary work from minimal-switch validation to first-principles method reconstruction. The previously proposed offline hard-map minimum check is not the active research route. Completed W0/W25 and other negative results remain unchanged.

D1 reuse: current W0/W25 code/results, independently reviewed PC16 negative/nonstationary endpoint, and fresh E032/E033 attempt02 result records. D5 delivered a method-focused synthesis and4 complete source papers/reading notes. D6 now delivers the user-selected complete constrained incremental variational + FEM–neural hybrid design and independent design-review PASS, without decisive blockers. NN predicts one next-state damage initial guess; full-space FEM/damage correction, accepted-state fatigue reconstruction, fresh joint acceptance and one durable commit determine the final state. New nodal K is explicitly stronger than historical GP constraints; matched NN-off constrained FEM and classical extrapolation isolate neural value. All setup, labels, training and online correction costs are included. This is a reviewed design, not Code Ready or measured improvement. No training/FEM/data-boundary change occurred. [Full design](../research/S04/hybrid_constrained_design_20261019/design_v1.md), [independent review](../research/S04/hybrid_constrained_design_20261019/review_v1.md), [decision and implementation checklist](../research/S04/hybrid_constrained_design_20261019/decision.md).

Report: `/Users/wenxiaofang/obsidian/05 Knowledge/deep research report/Deep Research - PIDL接近FEM的第一性原理重构路线.md`. Search/source/evidence records: `local_archive/research/pidl_first_principles_20261019/`.

## Historical decision ladder (completed 2026-10-18)

| Step | Decision / minimal asset | State / advance or redirect |
|---|---|---|
| D1 | Reuse saved C initial bundle/fields, original9 failure vectors, reviewed W0/W25 runner/card, native-Q4 scorer and existing default-off bound patch | complete; continue existing route, no new FEM/trajectory/design/sweep |
| D2 | Diagnose/fix strict fullNN chain check using same-forward arithmetic controls | complete; original9 bitwise reproduced; independent joint manual/direct exact; original tolerances unchanged; actual evidence independently reviewed |
| D3 | Original W0/W25 gamma-only pair200 each, hard lower-box/symmetry off | complete; 400 updates31.8276s, active-Eh preflight passed, histories/FEM0; exact source8edc762 |
| D4 | Independently verify same FEM C/W0/W25 0/200 scores and common-scale maps; select one next test | complete; independent recomputation of6 endpoints max metric difference2.22e-16,29 hashes/9 figures verified. This authorized task is finished; proposed offline next is not executed |

## Measured result and bounded decision

W0 u/v/d at0/200 exactly repeat historical C. W25 increases J by31.157%, u/v/d by12.152/44.533/43.733%. GP negative amplitude/retreat improve but max nodal retreat increases64.581%. Keep gamma16875 under this single seen c1s1 fixed200 test. No convergence, trajectory, teacher, generalization or physical-truth conclusion.

[Full result and actual field-error table](../research/S04/S04-E011/runs/loss_weight_fixed200_result_20261018.md), [compact comparison](../research/S04/S04-E011/runs/loss_weight_fixed200_comparison_20261018.json), [actual strict-gradient evidence review](../research/S04/S04-E011/runs/weight_gradient_fix_evidence_review_20261018.json). Local exact fields/figures: `local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_fix_8edc762_20261018T210743Z/{retrieved,analysis,comparison}`; full checkpoints/GP retained remote under the same Run ID.

Historical next candidate (superseded as main route by the user on2026-10-19): offline hard-map intervention range and saturation/release-gradient audit of the saved W0 endpoint, reusing the existing full-grid algebraic feasibility check instead of repeating it. No training, no projected-field improvement claim. Only then consider a separately scoped hard-box-only200 test at unchanged gamma/weights. Displacement contributes about96.12% of J squared, so feasibility alone cannot establish the desired FEM agreement.

Current workflow: installed research-decision-core plus road-fracture/PIDL adapters; project-local skill files remain historical snapshots. This workflow refresh changes no scientific thresholds, allowed evidence, execution authority or budget. Obsidian owner note is mesh对齐.md with its one current Roadmap link.

Actual result review: [scoped independent receipt](../research/S04/S04-E011/runs/loss_weight_fixed200_evidence_review_20261018.json). Current execution succeeded; retrieval verified/partial by declared compact scope; gamma25 field claim negative; research disposition repair with one proposed offline discriminator. No active producer remains from this Run.
