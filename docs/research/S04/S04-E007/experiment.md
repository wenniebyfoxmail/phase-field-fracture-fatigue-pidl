---
storyline_id: S04
experiment_id: S04-E007
protocol_revision: 20261005-r0
status: design-pass; code-review-pending
---
# FEM hard-irreversibility KKT alignment and coverage

Purpose: determine whether c83's failed PIDL box stationarity screen persists when interpreted on the FEM nodal feasible set d_old <= d <= 1. Then screen early/middle/late states and loading phases where correctly paired native data exist. No training, no new FEM solve, no history update in this offline diagnostic.

## Five-question gate

- Mechanism: legitimate irreversible-bound reactions versus residual disequilibrium at the archived field.
- Success changes only frozen-coefficient damage-block qualification, not coupled teacher/trajectory/physical truth.
- Failure identifies a state for later targeted correction; no automatic tolerance change or solver launch.
- Cheaper first: reuse exported original MATLAB residual, accepted prior and native state; compare archived E003 AD vector; regression against Request27 c5.
- Minimal assets: bound-aware residual table, feasibility/active-set/location diagnostics, coverage/export request, decision and run receipt; register S04 storyline and inventory.

## Proposed contract (pending external design review)

Current state U approximately 0.12 c83 s4 from E003 identity-locked native capture; compare original residual and matching E003 frozen-Ftrial energy gradient. Free phase set excludes 251 prescribed precrack nodes. Verify true previous accepted damage from pre_phase_input/p_field_old and oracle copy; do not use last stagger input p_field or postcommit history.

Reuse legacy sign-filtered raw KKT L2: lower-bound r<0 is violating, upper-bound r>0 is violating, interior r is retained, exact collapsed interval d_old=1 contributes no stationarity restriction. Bound classification tolerance 1e-12. Report old implementation separately when corrected collapsed handling differs. Feasibility and fixed-value checks precede any PASS. Historical 4e-4 threshold is a explicitly migrated comparison screen, not evidence of the native runtime stopping tolerance.

Also report hard projected-map mass RMS using d-Pi_[d_old,1](d-r/(Es*m)), original whole-domain nodal mass fractions and Es=area*E*(Us/H)^2. No new normalized hard-KKT threshold. Keep old box map and 1e-3 screen as separate PIDL-objective diagnostic. No GP-hard-QP certificate claim.

Select requested coverage before reading new residuals: same U trajectory c20/c40/c60 peak as early/mid anchors, c76 as bridge only, c82/c83 late comparison; event and after-event designations require accepted event metadata. Cycle-internal loading/peak/unload substeps must be identified from the actual schedule. Missing accepted prior, native nodal/GP state or oracle => NOT_EVALUABLE for this contract, no invented predecessor. Existing c5 U0.13 is a method regression, not an early point of U0.12.

Record all failures. No broad claim from three late peaks; no field correction without a separate reviewed execution contract. Mac allowed only lightweight archived-array postprocessing and tiny tests; no full assembly/training/solve.

## Adopted design review

GPT Pro DESIGN PASS on 2026-10-05 (4m43s), existing review conversation 6ac2e1ce-9940-83ed-a562-b17182126205. Exact collapsed means d_old=d=1 only. For nonzero narrow intervals, exact d=d_old<1 takes lower precedence; exact d=1>d_old takes upper; remaining double-near nodes retain raw residual and are ambiguous, never automatic PASS. Feasibility numerical tolerance is reported explicitly at1e-12 with unrounded max/counts; inputs are never clipped. Screen name HARD_KKT_MIGRATION_SCREEN. Within-cycle normalized diagnostics keep the trajectory peak Us fixed even at zero load. The existing old c5 exported-vector replay is separate from new classifications. No automatic new solve on unavailable data. Review based on supplied design, not independent archive execution.
