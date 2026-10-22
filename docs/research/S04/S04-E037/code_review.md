# Independent Code Ready — S04-E037

2026-10-22. Channel: independent read-only Codex reviewer `/root/review_gradient_probe`, inherited model (no separate model identity claim). Bound final source `a6bb52ebf30779ae22310b6af474528ed984dc8b`, protocol r1, runner `scripts/run_s04_e037_primal_dual.py`, standard U0.12 recovery0 + canonical original archive, single Taobo GPU, <=2GPUh.

Initial design correction: remove hard clip because it can block release and produce a zero parameter gradient at a wrong field solution. Final original nonsmooth map unchanged; two PHR inequalities used, field residuals remain separate from parameter stationarity. Raw old h>1 never silently clipped/restarted.

1fc9b7fe: MODIFY_AND_REREVIEW. Snapshot differentiated updated-multiplier PHR merit, not true fixed-multiplier Lagrangian; scalar example independently reproduced true gradient0 versus merit−1. Also deadline needed recheck before commit, and control replay failure could proceed to new arm.

83b9ce6a: core corrections passed. Actual extracted Lagrangian branch matches independent CPU hand calculation. New final deadline guard precedes unique history commit. Both control parameter/history identities are checked before acceptance; failures write receipt then terminate dispatcher. Gradient calls and diagnostic time tracked. Twelve algebra tests rerun passed; no NN training on Mac.

Output-only a6bb52eb: REVIEW_PASS. Invalid original h>1 marks box projected residual null and records inconsistent_bound_count. Every final snapshot stores full updated mu/rho/c with the same final network/fields, enabling independent post-run stationarity/feasibility checks.

Carried verified scope: unchanged core/config/network map/weights-only L2; fixed normalized lumped mass; dual support and post-update check; immutable step histories; trial fatigue from fixed prior state; one cached-field commit; 8x1250 update cap; original source fit call; same-point strain/raw/active/A export; failed/capped new steps never continue. Fresh resource/transfer/process checks remain mechanical launch conditions. This review is not numerical convergence, field KKT, physical truth or improvement evidence.
