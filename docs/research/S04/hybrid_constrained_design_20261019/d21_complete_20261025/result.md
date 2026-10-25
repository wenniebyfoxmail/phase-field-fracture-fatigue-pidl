# D21 R10 actual stop — 2026-10-25

Original owner pipeline integration is implemented at6709ad81; fixed benchmark16/16 passed. A real fresh task was dispatched, not merely prepared. Source64/64 matches the bound artifact. Native replay5/5 and plotting/runtime/capacity admission passed. All7 attributable process identities have exited.

## Actual outcome

- train_A physical step1 failed: `joint coupled block direction budget exhausted` after8 direction constructions and9 fresh working evaluations. Solver observed165.826s; complete trajectory worker169.145s; not the300s step timeout or RAM/GPU/storage failure.
- Accepted labels0/1800;train/validation completed trajectories0;fit0;test0. Initial-state snapshot/latest remain version0, identicalSHA and prescribed state ID. No final real-QP/history commit was reached. Unaccepted work points are **not labels**.
- Last fresh mechanicalL2=1.8422152e-06 = 184.22×1e-8;damageKKT=1.705712e-06 = 17.06×1e-7. Weighted objective fell33.10×; this does not establish physical convergence. Fatigue-activeGP0.
- Selected directions: one optional Newton,one active-face Krylov improvement,six certified Cauchy. Each refinement eventually stopped without certifying a further improvement; do not misreport this as zero Krylov improvements. Later Krylov line steps are first-bound truncated to roughly1e-23–1e-19 while unconstrained alpha is about2–2.6. This is an observed boundary-stagnation signature; the causal explanation remains an inference.

## Costs and remaining data

Actual new producer181.993599wall seconds;new observed child CPU222.314625s;GPU0. Do not add phase wall sums again to the producer duration. No whole-lifecycleCPU total is asserted.

Remaining conservative balance128.186352hosth and12GPUh, inside original136/12. This includes the frozen3600s staging/control/closure reserve, which is not observed compute or a new allotment. Current control-window consumption and120s final closure allowance fit within that reserve, detailed inrun_receipt.json. The reserve remains held, not released or charged twice. Resource wait/retry usage0.

Still missing: all1200 training+600validation qualified transitions,one frozen fit,all1800 heldout test states. Existing code/state0/mesh/native replay/D21 solver/label timing contract/phase supervision/freeze/fit reservation remain reusable. Failed working candidates cannot fill these gaps.

## Next technical decision — no code change or extra run authorised/executed

Current direct authority explicitly stops at a failure requiring technical code changes. Automatic admission retry cannot resolve deterministic numerical stagnation. Task remains stopped; no R11,scope expansion or automatic threshold/budget change.

Proposed next work is an original-owner repair of **active-face entry/restart under representable near-boundary steps**, beginning with the retained model andcandidate intervals. Determine whether a negligible first-bound intersection prevents an otherwise useful projected direction. Compare feasible projected-path/active-face advancement against the retained Cauchy in the same originalModel; retain exact feasibility,model-decrease protection,unchanged physical acceptance,actual-history/f_solve timing and original300s/action/update budget. Do not simply increase8directions or300s,relax tolerances,or replace labels with failure points. One task benchmark should reproduce this saved-model boundary signature and require a proven feasible improvement; only then would a fresh scientific attempt be considered under separately authorised technical repair.

Scientific impact: the configured D21 teacher producer still cannot reach the first accepted step. This blocks training readiness. It does not evaluate neural accuracy,speedup,benefit of the overall hybrid design,or road/material/mesh generalisation. Full three-arm comparison question remains unanswered.

Raw234-file inventory/146806540B remains onproducer, with per-fileSHA andcompact logs retrieved to `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/d21_complete_20261025`. [Run receipt](run_receipt.json), [prospective route](plan.md), [fixed benchmark](benchmark.json). Remote run/archive roots remain immutable evidence; no running source was hot-edited.
